# Time Clock — Technical Brief
**Stack:** Supabase (Postgres + Realtime) · Netlify (static hosting) · Vanilla JS SPA

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                     Clients                          │
│                                                      │
│  Employee phones        Tablet         Manager/Admin │
│  (PWA, remembered)   (shared, resets)  (desktop only)│
└────────────┬──────────────┬───────────────┬─────────┘
             │              │               │
             └──────────────┴───────────────┘
                            │  HTTPS
                    ┌───────▼────────┐
                    │    Netlify     │  Static hosting
                    │  timeclock.html│  (or S3+CloudFront)
                    └───────┬────────┘
                            │  Supabase JS client (REST + WS)
              ┌─────────────▼──────────────────┐
              │           Supabase              │
              │                                 │
              │  ┌─────────┐  ┌─────────────┐  │
              │  │ PostgREST│  │  Realtime   │  │
              │  │ (REST API│  │ (WebSocket) │  │
              │  └────┬─────┘  └──────┬──────┘  │
              │       │               │          │
              │  ┌────▼───────────────▼──────┐  │
              │  │         Postgres           │  │
              │  │   tc_employees             │  │
              │  │   tc_punches               │  │
              │  │   tc_day_flags             │  │
              │  │   tc_config                │  │
              │  └───────────────────────────┘  │
              └────────────────────────────────┘
```

The frontend is a single-file SPA with no build step. All business logic lives in the client. The backend is entirely Supabase-managed: PostgREST auto-generates a REST API from the schema, and the Realtime engine streams Postgres WAL changes over WebSocket to connected clients.

---

## 2. Data Model

### Tables

```sql
-- Employees / roster
CREATE TABLE tc_employees (
  id          TEXT PRIMARY KEY,          -- client-generated: Date.now().toString(36) + random
  name        TEXT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Punch records (clock in / clock out events)
CREATE TABLE tc_punches (
  id            TEXT PRIMARY KEY,
  employee_id   TEXT NOT NULL,           -- not FK-constrained; preserves history on roster changes
  employee_name TEXT NOT NULL,           -- denormalized for read performance (no joins needed)
  role          TEXT NOT NULL,
  location      TEXT NOT NULL,
  clock_in      TIMESTAMPTZ NOT NULL,
  clock_out     TIMESTAMPTZ,             -- NULL = currently clocked in
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Per-day manager flags (lunch deduction, NCNS, short notice)
CREATE TABLE tc_day_flags (
  id            TEXT PRIMARY KEY,        -- composite: "{employee_id}_{YYYY-MM-DD}"
  employee_id   TEXT NOT NULL,
  flag_date     DATE NOT NULL,
  lunch         BOOLEAN NOT NULL DEFAULT FALSE,
  ncns          BOOLEAN NOT NULL DEFAULT FALSE,
  short_notice  BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT unique_emp_date UNIQUE (employee_id, flag_date)
);

-- App configuration (enforced single-row)
CREATE TABLE tc_config (
  id            INTEGER PRIMARY KEY DEFAULT 1,
  roles         TEXT[] NOT NULL,
  locations     TEXT[] NOT NULL,
  manager_pin   TEXT NOT NULL DEFAULT '1234',
  admin_pin     TEXT NOT NULL DEFAULT '5678',
  CONSTRAINT single_row_only CHECK (id = 1)
);
```

### Recommended Indexes

The setup SQL only creates primary keys. Add these for production query performance:

```sql
-- Weekly timesheet queries filter and sort by clock_in date
CREATE INDEX idx_punches_clock_in     ON tc_punches (clock_in);

-- Per-employee history lookups
CREATE INDEX idx_punches_employee     ON tc_punches (employee_id, clock_in);

-- "Who is currently clocked in?" — partial index, very fast
CREATE INDEX idx_punches_active       ON tc_punches (employee_id)
  WHERE clock_out IS NULL;

-- Manager daily view filters by date
CREATE INDEX idx_day_flags_date       ON tc_day_flags (flag_date);
```

### Key Design Decisions

**employee_name denormalization on tc_punches:** Employee names are stored on each punch record rather than joined from tc_employees. This means historical records are readable even if someone is removed from the roster mid-season, and query performance is better (no join for the live view or timesheet).

**Client-generated IDs:** IDs are generated on the client using `Date.now().toString(36) + Math.random().toString(36)`. This is sufficient for this scale and avoids a round-trip to get a server-generated ID before optimistically updating the UI. For a higher-concurrency system, UUIDs (`gen_random_uuid()`) would be preferable.

**No FK constraints on tc_punches.employee_id:** Deliberate. Referential integrity would prevent removing an employee from the roster without cascading deletes on their punch history, which is undesirable for payroll records.

---

## 3. Security Model

### Current Setup

The app uses Supabase's **anon key** (public key) with **Row Level Security enabled** and a permissive policy (`USING (true)`). This means:

- Any client with the anon key can read and write all tables
- The anon key is embedded in the HTML source — anyone who opens DevTools can see it
- App-level access control is PIN-based only (Manager PIN, Admin PIN)

### Threat Assessment

For an internal seasonal production timeclock with ~100 employees, this is an **acceptable risk posture** with the following caveats:

| Threat | Likelihood | Impact | Mitigation |
|--------|-----------|--------|------------|
| Employee reads other employees' punch data via direct API | Low | Low | App UI hides this; requires knowing the Supabase URL and anon key |
| Employee manipulates their own punch records | Low | Medium | PIN protects manager/admin; no edit UI in employee view |
| External actor queries database | Very low | Low | URL not publicly indexed; anon key scoped to project only |
| PIN brute force | Low | Medium | No lockout currently; see below |

### Hardening Options (if required)

**Option A — Restrict anon key write access (recommended minimum)**

Replace the permissive policies with read-only for the anon role, and use a server-side secret (Supabase Edge Function) as a proxy for writes:

```sql
-- Read-only for anon
CREATE POLICY "anon_read" ON tc_punches FOR SELECT TO anon USING (true);

-- Writes go through an authenticated Edge Function
CREATE POLICY "service_write" ON tc_punches FOR ALL TO service_role USING (true);
```

**Option B — Supabase Edge Functions as API layer**

Write thin Edge Functions (Deno/TypeScript) that validate requests before writing to the DB. The frontend calls these instead of PostgREST directly. The `SERVICE_ROLE_KEY` never leaves the server. This is the closest equivalent to the Lambda + DynamoDB approach without leaving Supabase.

**Option C — PIN hashing**

Currently PINs are stored in plaintext in `tc_config`. At minimum, store them as bcrypt hashes and validate server-side via an Edge Function. For a 4–6 digit PIN used internally, plaintext is low risk but worth noting.

**Option D — Full auth (overkill for this use case)**

Supabase Auth supports email/password, magic links, OAuth. Would require employees to have accounts. Not recommended for a quick-in-quick-out timeclock used by seasonal workers.

---

## 4. Hosting: Netlify vs S3 + CloudFront

### Netlify (current recommendation)

| | |
|--|--|
| Setup | Drag-and-drop, ~2 min |
| SSL | Automatic (Let's Encrypt), auto-renews |
| Custom domain | Add in dashboard, CNAME or A record |
| Deploy on push | Built-in Git integration |
| CDN | Netlify Edge (global) |
| Cost | Free tier: 100GB bandwidth/month, 300 build min/month |
| Lock-in | Low — it's a static file, trivially portable |

For a single HTML file serving 100 employees, Netlify is the right call. The free tier has orders-of-magnitude more headroom than needed.

### S3 + CloudFront (if AWS is preferred)

Better choice if the team already manages AWS infrastructure or has billing consolidated there.

```
Infrastructure:
  S3 bucket          — static asset storage ($0.023/GB, ~$0.00 for one HTML file)
  CloudFront distro  — CDN + HTTPS termination (1TB free/month)
  ACM certificate    — free, auto-renews
  Route53            — DNS ($0.50/hosted zone/month)

Estimated monthly cost: ~$0.50 (just the Route53 zone)
```

**Deployment via AWS CLI:**
```bash
aws s3 cp timeclock.html s3://your-bucket-name/index.html \
  --content-type "text/html" \
  --cache-control "no-cache"

aws cloudfront create-invalidation \
  --distribution-id YOUR_DIST_ID \
  --paths "/*"
```

---

## 5. CI/CD

### Option A: Netlify Git Integration (zero-config)

1. Push `timeclock.html` to a GitHub repo
2. Connect repo to Netlify (one-time OAuth)
3. Every push to `main` triggers a deploy automatically

This is sufficient for this project. No pipeline config needed.

### Option B: GitHub Actions (explicit control)

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]
    paths: ['timeclock.html']   # only trigger on app changes

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Netlify
        uses: netlify/actions/cli@master
        with:
          args: deploy --prod --dir=. --filter=timeclock.html
        env:
          NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}
          NETLIFY_SITE_ID: ${{ secrets.NETLIFY_SITE_ID }}
```

### Option C: GitHub Actions → S3 + CloudFront

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]
    paths: ['timeclock.html']

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write   # OIDC
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC — no long-lived keys)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::ACCOUNT_ID:role/github-deploy-role
          aws-region: us-east-1

      - name: Upload to S3
        run: |
          aws s3 cp timeclock.html s3://${{ vars.S3_BUCKET }}/index.html \
            --content-type "text/html" \
            --cache-control "no-cache, no-store, must-revalidate"

      - name: Invalidate CloudFront cache
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ vars.CF_DIST_ID }} \
            --paths "/*"
```

Note: Use OIDC (`id-token: write`) rather than storing `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` as secrets. Configure the IAM role trust policy to allow the specific GitHub repo.

---

## 6. Custom Domain

### Netlify

1. **Netlify dashboard** → Site configuration → Domain management → Add custom domain
2. Add a **CNAME record** in your DNS provider:
   ```
   timeclock.yourcompany.com  CNAME  your-site.netlify.app
   ```
3. Netlify provisions an SSL cert automatically within ~1 minute

### CloudFront + Route53

```bash
# 1. Request ACM certificate (must be in us-east-1 for CloudFront)
aws acm request-certificate \
  --domain-name timeclock.yourcompany.com \
  --validation-method DNS \
  --region us-east-1

# 2. Add the CNAME validation record to Route53 (ACM console shows the values)

# 3. Attach cert to CloudFront distribution (via console or CLI)

# 4. Create Route53 alias record
# Type: A, Alias: Yes, Target: your CloudFront domain (d1234.cloudfront.net)
```

---

## 7. Backups & Recovery

### Supabase Free Tier Limitations

- **No point-in-time recovery (PITR)** on free tier
- **No automated daily backups** on free tier
- Projects inactive for 7+ days are **paused** (single click to resume; data preserved)
- Free tier storage limit: 500MB (current data: ~1MB/season at this scale)

### Manual Backup Options

**Option A: pg_dump via Supabase connection string**

```bash
# Get connection string from: Project Settings → Database → Connection string (URI)
pg_dump "postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres" \
  --table=tc_employees \
  --table=tc_punches \
  --table=tc_day_flags \
  --table=tc_config \
  --no-owner \
  --no-acl \
  -f timeclock-backup-$(date +%Y%m%d).sql
```

**Option B: CSV export via PostgREST**

```bash
# Export punches as CSV (works with anon key)
curl "https://[REF].supabase.co/rest/v1/tc_punches?select=*" \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Accept: text/csv" \
  > punches-$(date +%Y%m%d).csv
```

**Option C: Scheduled backup to S3 (lightweight automation)**

```yaml
# GitHub Actions — runs weekly
name: Backup
on:
  schedule:
    - cron: '0 6 * * 0'   # Sundays at 6 AM UTC
jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - name: Export and upload to S3
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: |
          curl "$SUPABASE_URL/rest/v1/tc_punches?select=*" \
            -H "apikey: $SUPABASE_KEY" \
            -H "Accept: text/csv" \
            > punches.csv
          aws s3 cp punches.csv s3://your-backup-bucket/timeclock/punches-$(date +%Y%m%d).csv
```

### Upgrade Path

Supabase Pro ($25/month) adds:
- 7-day PITR
- Daily automated backups
- No project pausing
- 8GB database

Not needed this season, but worth knowing the path exists.

---

## 8. Realtime Architecture

Supabase Realtime uses **Postgres logical replication** (WAL). When a row changes in `tc_punches`, the Realtime server receives the WAL event and broadcasts it over WebSocket to subscribed clients.

The app subscribes to `tc_punches` on load:

```javascript
db.channel('tc-live')
  .on('postgres_changes',
    { event: '*', schema: 'public', table: 'tc_punches' },
    payload => { /* update local state, re-render */ }
  )
  .subscribe();
```

This means when an employee clocks in on their phone, the manager's live dashboard updates within ~200ms without polling. The app also has a 30-second polling fallback for flag and config changes (which don't need realtime).

**Free tier limit:** 200 concurrent Realtime connections. At 100 employees, you'd need all of them using the app simultaneously to approach this — not realistic.

---

## 9. Free Tier Limits vs. Expected Usage

| Resource | Free Limit | Expected Usage | Headroom |
|----------|-----------|----------------|----------|
| Database size | 500 MB | ~2 MB/season | 250× |
| API requests | Unlimited | ~50K/week | ∞ |
| Realtime connections | 200 concurrent | <20 at peak | 10× |
| Bandwidth | 5 GB/month | ~100 MB/month | 50× |
| Auth users | 50,000 | N/A (PIN auth) | N/A |

No paid tier needed for this use case. The only scenario that would change this is if Supabase pauses the project due to inactivity between seasons — resume it with one click before each season starts.

---

## 10. Summary Recommendations

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| Hosting | Netlify | Zero config, free, global CDN |
| CI/CD | Netlify Git integration | Sufficient for single-file app |
| Custom domain | Netlify CNAME | 2 min setup vs 30 min for CloudFront |
| Security hardening | Add recommended indexes; optionally restrict anon write access | Good baseline for internal app |
| Backups | Weekly manual pg_dump or CSV export | Free, adequate for seasonal data |
| Realtime | Keep current WebSocket setup | Works well within free tier |
| AWS involvement | Use for S3 backup bucket if desired | Leverage existing infra without rebuilding what works |

The Supabase + Netlify stack is production-ready for this workload. The main operational task each season is un-pausing the Supabase project if it has been idle, and updating the employee roster in Admin → Settings.
