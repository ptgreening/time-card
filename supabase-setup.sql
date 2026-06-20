-- ════════════════════════════════════════════════════════════
--  TIME CLOCK  —  Supabase Database Setup
--  Run this entire script in your Supabase SQL Editor
-- ════════════════════════════════════════════════════════════

-- Employee roster
create table if not exists tc_employees (
  id          text primary key,
  name        text not null,
  created_at  timestamptz default now()
);

-- Punch records (clock in / out events)
create table if not exists tc_punches (
  id            text primary key,
  employee_id   text not null,
  employee_name text not null,
  role          text not null,
  location      text not null,
  clock_in      timestamptz not null,
  clock_out     timestamptz,
  created_at    timestamptz default now()
);

-- Per-day flags: lunch deduction, NCNS, short notice
create table if not exists tc_day_flags (
  id            text primary key,        -- format: "employee_id_YYYY-MM-DD"
  employee_id   text not null,
  flag_date     date not null,
  lunch         boolean not null default false,
  ncns          boolean not null default false,
  short_notice  boolean not null default false,
  constraint unique_emp_date unique (employee_id, flag_date)
);

-- App configuration (single row — do not add more rows)
create table if not exists tc_config (
  id            integer primary key default 1,
  roles         text[] not null default array[
                  'Manager','Actor','Makeup Artist','Crowd Control','Carnival Crew'
                ],
  locations     text[] not null default array[
                  'Main Site','Storage Lot A','Storage Lot B','Office'
                ],
  manager_pin   text not null default '1234',
  admin_pin     text not null default '5678',
  constraint single_row_only check (id = 1)
);

-- Seed default config row
insert into tc_config (id) values (1) on conflict (id) do nothing;

-- ── Row Level Security ────────────────────────────────────────
--  The app itself controls access via PINs.
--  These policies allow the anon key to read/write all tables.

alter table tc_employees  enable row level security;
alter table tc_punches    enable row level security;
alter table tc_day_flags  enable row level security;
alter table tc_config     enable row level security;

create policy "public_access" on tc_employees  for all to anon using (true) with check (true);
create policy "public_access" on tc_punches    for all to anon using (true) with check (true);
create policy "public_access" on tc_day_flags  for all to anon using (true) with check (true);
create policy "public_access" on tc_config     for all to anon using (true) with check (true);

-- ── Real-time ─────────────────────────────────────────────────
--  Enables live updates when employees clock in across devices

alter publication supabase_realtime add table tc_punches;

-- ════════════════════════════════════════════════════════════
--  Done! Now grab your Project URL and anon key from
--  Project Settings → API and paste them into timeclock.html
-- ════════════════════════════════════════════════════════════
