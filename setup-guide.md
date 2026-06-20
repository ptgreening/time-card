# Time Clock — Setup Guide

Everything you need to get this running for your season.
Total time: about 20 minutes.

---

## What you'll need
- A computer (Mac or Windows)
- The two files from this download: `timeclock.html` and `supabase-setup.sql`

---

## Step 1 — Create your database (Supabase)

Supabase is a free database service. Your punch data lives here and syncs across all devices in real time.

1. Go to **[supabase.com](https://supabase.com)** and click **Start your project**
2. Sign up with GitHub or email (free)
3. Click **New project**
4. Name it `time-clock`, pick a region close to you (US East or US West), set a password, click **Create new project**
5. Wait about 60–90 seconds for it to finish setting up

### Create the tables

6. In your project, click **SQL Editor** in the left sidebar
7. Click **+ New query**
8. Open `supabase-setup.sql` in Notepad (Windows) or TextEdit (Mac)
9. Select all the text, copy it, paste it into the SQL Editor
10. Click the green **Run** button
11. You should see "Success. No rows returned" — that means it worked

### Get your API credentials

12. Click the **gear icon (⚙)** at the bottom of the left sidebar → **API**
13. Copy the **Project URL** (looks like: `https://abcdefgh.supabase.co`)
14. Copy the **anon public** key (a long string starting with `eyJ...`)
15. Keep these handy — you'll need them in the next step

---

## Step 2 — Configure the app

1. Open `timeclock.html` in a text editor
   - **Windows:** Right-click the file → Open with → Notepad
   - **Mac:** Right-click → Open With → TextEdit (then Format → Make Plain Text)

2. Near the top, find these two lines:
   ```
   const SUPABASE_URL = 'YOUR_SUPABASE_URL';
   const SUPABASE_KEY = 'YOUR_SUPABASE_ANON_KEY';
   ```

3. Replace `YOUR_SUPABASE_URL` with your Project URL (keep the quotes)
4. Replace `YOUR_SUPABASE_ANON_KEY` with your anon key (keep the quotes)

   It should look like this when done:
   ```
   const SUPABASE_URL = 'https://abcdefgh.supabase.co';
   const SUPABASE_KEY = 'eyJhbGci...your long key here...';
   ```

5. Save the file

---

## Step 3 — Put it on the web (Netlify)

Netlify hosts your file so everyone can access it from any device.

1. Go to **[netlify.com](https://netlify.com)** and sign up (free)
2. Once logged in, click **Add new site** → **Deploy manually**
3. Drag and drop your `timeclock.html` file onto the upload area
4. Wait about 10 seconds — your site is live!
5. You'll see a URL like `coral-widget-abc123.netlify.app` — this is your app

### Customize the URL (optional but recommended)
6. Click **Site configuration** → **Change site name**
7. Enter something like `yourcompany-timeclock` → **Save**
8. Your URL is now `yourcompany-timeclock.netlify.app`

---

## Step 4 — Add your employees

1. On a **desktop/laptop**, open your app URL
2. Click **Staff login** (top right — only visible on desktop)
3. Enter the Admin PIN: **5678**
4. Go to the **Settings** tab
5. Paste your employee list into the roster box (one name per line)
6. Update your actual roles and locations if needed
7. **Change your Manager and Admin PINs** before going live!
8. Click **Save settings**

---

## Step 5 — Share with your team

### For employees on personal phones
- Text or email them the URL
- **iPhone:** Open in Safari → tap the Share button → "Add to Home Screen" → it appears as an app icon
- **Android:** Open in Chrome → tap ⋮ menu → "Add to Home Screen"
- First time they clock in, they'll be asked "Is this your personal phone?" — if they tap Yes, the app remembers them and goes straight to their screen next time

### For the management tablet
- Open the URL in the tablet's browser
- Bookmark it or add it to the home screen
- The app will auto-reset to the search screen after each clock-in or clock-out (4-second countdown)

### For manager / admin access
- Use any desktop or laptop browser — open the same URL
- The **Staff login** button only appears on screens wider than 900px (won't show on phones or tablets)
- Manager PIN: whatever you set in Settings (default: 1234)
- Admin PIN: whatever you set in Settings (default: 5678)

---

## Generating a QR code for the tablet

Go to **[qr.io](https://qr.io)** or **[qrcode-monkey.com](https://www.qrcode-monkey.com/)**, enter your URL, and download the QR code image. Print it and post it near the management table so employees who don't have the URL yet can scan it.

---

## Troubleshooting

**"Connection Error" on launch**
- Double-check you copied the full URL and anon key into the HTML (no missing characters, quotes still there)
- Make sure you ran the SQL setup script — go back to Supabase SQL Editor and run it again if unsure (it's safe to run twice)

**Employee name not found**
- Names in the roster must match exactly (including capitalization and spaces)
- Go to Admin → Settings and check the roster

**"Save failed" toast message**
- Usually a brief internet hiccup — try again
- If it keeps happening, check your Supabase project is still active (free projects don't expire, but can be paused after inactivity — unpause from the Supabase dashboard)

**Updating the app later**
- Edit `timeclock.html`, then drag it back to Netlify (same "Deploy manually" flow) — it replaces the old version automatically

---

## Summary of PINs and access

| Who | Device | Access |
|-----|--------|--------|
| Employees | Their phone or the tablet | Clock in/out only |
| Manager | Desktop/laptop | Daily view, edit times, flags |
| Admin | Desktop/laptop | Everything + settings + CSV export |

