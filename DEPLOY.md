# Deploying TOP GRADE to production (Render + Netlify)

This deploys the two halves of the app separately:
- **Backend** (Flask API + database + video files) → Render
- **Frontend** (HTML/JS) → Netlify

Both have free tiers and neither needs a credit card to start.

---

## 0. Push the project to GitHub

Render and Netlify both deploy from a Git repository, so first:

1. Create a new repository on GitHub (e.g. `topgrade-app`).
2. From inside the `topgrade-app` folder:
   ```
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/topgrade-app.git
   git push -u origin main
   ```

---

## 1. Deploy the backend to Render

1. Go to [render.com](https://render.com) and sign up / log in.
2. Click **New +** → **Blueprint**.
3. Connect your GitHub account and select the `topgrade-app` repo.
4. Render will detect `render.yaml` at the repo root and pre-fill the service
   (name: `topgrade-backend`, free plan, Python).
5. Click **Apply** / **Create**. Render will:
   - `pip install -r requirements.txt`
   - `python database/seed.py` (builds a fresh database)
   - start the app with `gunicorn`
6. Once deployed, Render gives you a URL like:
   ```
   https://topgrade-backend.onrender.com
   ```
   Keep this — you'll need it in step 2.

**Test it:** open `https://topgrade-backend.onrender.com/api/courses` in your
browser. You should see the course JSON.

---

## 2. Point the frontend at your live backend

Open `frontend/config.js` and change the one line:

```js
const API_BASE = "https://topgrade-backend.onrender.com";
```

Commit and push this change:
```
git add frontend/config.js
git commit -m "Point frontend at production backend"
git push
```

---

## 3. Deploy the frontend to Netlify

**Option A — connect your GitHub repo (recommended, auto-redeploys on push):**
1. Go to [netlify.com](https://netlify.com) and sign up / log in.
2. Click **Add new site** → **Import an existing project**.
3. Choose GitHub, select `topgrade-app`.
4. Set **Base directory** to `frontend`, leave build command empty,
   publish directory as `.` (Netlify reads this from `netlify.toml` already).
5. Click **Deploy**.

**Option B — drag and drop (fastest, no auto-redeploy):**
1. Go to [app.netlify.com/drop](https://app.netlify.com/drop).
2. Drag your local `frontend` folder onto the page.

Either way, you'll get a URL like:
```
https://topgrade.netlify.app
```

---

## 4. Lock down CORS to your real frontend URL

Right now the backend accepts requests from any origin (`ALLOWED_ORIGIN=*`),
which is fine for testing but not for production.

1. In the Render dashboard, open your `topgrade-backend` service → **Environment**.
2. Set `ALLOWED_ORIGIN` to your real Netlify URL (or custom domain), e.g.:
   ```
   https://topgrade.netlify.app
   ```
3. Save — Render will redeploy automatically with the new setting.

---

## 5. Point your real domain (optional)

If you want `www.topgradeinnovation.com` to serve the app instead of the
Netlify/Render subdomains:
- In Netlify: **Domain settings** → add your custom domain, follow the DNS
  instructions (usually a CNAME record).
- In Render: **Settings** → **Custom Domain**, add something like
  `api.topgradeinnovation.com`, follow its DNS instructions.
- Update `frontend/config.js` to use `https://api.topgradeinnovation.com`
  once that's live, and update `ALLOWED_ORIGIN` on Render to match your
  new frontend domain.

Both platforms issue free HTTPS certificates automatically once DNS is set.

---

## Known limitations on the free tier (read before relying on this)

- **SQLite resets on every deploy.** The build command re-runs
  `python database/seed.py`, which wipes and rebuilds the database from
  scratch. That means any enrollments made by real users in production will
  be lost the next time you push a change. Fine for a demo; for real users,
  migrate to Render's free PostgreSQL and update `app.py`'s `get_db()` to
  connect to it instead of SQLite.
- **Video files don't persist either**, for the same reason (ephemeral
  disk). Commit small demo videos directly into `backend/media/` so they
  redeploy with the code, or — better, for real file sizes — host them on
  Cloudflare R2 or Amazon S3 and change the `video_path` values in the
  database to full URLs instead of local paths.
- **Render free web services spin down after 15 minutes of inactivity** and
  take ~30-50 seconds to wake back up on the next request. Fine for a demo;
  upgrade to a paid instance ($7/mo) to keep it always-on for real users.
- **The current login is a name-typing demo**, not real authentication.
  Don't launch this to the public without replacing it with proper
  email/password or a login provider.
