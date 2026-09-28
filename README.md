# CineMine

A Data Warehousing & Mining mini-project: upload a movie watching history (CSV or PDF),
clean and match it against a master catalogue, then explore it with analytics,
K-Means clustering, Apriori association rules, Naive Bayes genre prediction and
personalised recommendations — through a clean React dashboard.

## Stack

| Layer     | Technology |
|-----------|------------|
| Frontend  | React 19, Vite, Tailwind CSS v4, Recharts, React Router, Axios |
| Backend   | FastAPI, Pandas, scikit-learn, mlxtend, pdfplumber, SQLite, PyJWT, passlib/bcrypt |
| Testing   | pytest + FastAPI TestClient (isolated temp databases per test) |

## Features

- **Auth** — register / login with bcrypt hashing and JWT bearer tokens.
- **Upload** — CSV or PDF (table with a Movie column and optional Rating column),
  with live preview: file name, row count, detected columns, sample rows, warnings.
- **Data cleaning** — duplicate / missing / invalid detection, fuzzy title matching
  against the 4,800-movie catalogue, a review screen for ambiguous and unmatched
  records (nothing is ever auto-chosen for you), then a one-click import.
- **Analytics** — summary cards, genre donut, rating distribution,
  genre-vs-average-rating, and plain-language insight cards.
- **Mining**
  - *K-Means* — movie-level clusters with dominant genre, average rating, silhouette score.
  - *Apriori* — genre association rules (support / confidence / lift) over the catalogue.
  - *Naive Bayes* — one binary classifier per genre trained on catalogue labels, with an
    honest stratified holdout; predicts how well your profile matches each genre.
- **Recommendations** — scored candidates combining genre affinity, association patterns
  and audience quality, each with a human-readable "why this was recommended" reason.
  Watched movies are never recommended.

## Run the project (3 steps)

> One-time setup (only if `.venv` or `node_modules` is missing):
> `python -m venv .venv`, `.\.venv\Scripts\pip install -r backend\requirements.txt`,
> `cd frontend; npm install; cd ..` — `start.ps1` does the frontend install for you.

**Step 1** — open PowerShell and go to the project folder:
```powershell
cd C:\Users\visha\moviesforfuture
```

**Step 2** — start both servers with one command:
```powershell
.\start.ps1
```
Wait for two green lines:
```
[1/2] Backend  OK   http://127.0.0.1:8000  (4803 movies loaded)
[2/2] Frontend OK   http://localhost:5173
```
If a server fails, the same window prints the real error and how to fix it.

**Step 3** — open **http://localhost:5173** in your browser:
- Login: `demo@cinemine.dev` / `secret123` (already has data), or register a new account.

**Stop:** press **ENTER** in the `start.ps1` window — or, from another
PowerShell window, run `.\stop.ps1`.

`.\start.ps1 -Backend` / `.\start.ps1 -Frontend` starts only one side.

The database (`backend/data/cinemine.db`) and the movie catalogue
(`backend/seed/tmdb_5000_movies.csv`, max 5,000 rows) are created automatically on
first start. Server logs land in `logs/` and stream live into the `start.ps1` window.

### Troubleshooting

| You see | What it means | Fix |
|---|---|---|
| `ECONNREFUSED 127.0.0.1:8000` or *proxy error* in the Vite terminal | Frontend is up, **backend is not running** | Run `.\start.ps1` (keep its window open) |
| Red banner: *Backend is not running* | Same as above — the app re-checks every 10s and fixes itself once the backend is up | Run `.\start.ps1` |
| `[FAIL] Port 8000 is already in use` | An old server is still running | `.\stop.ps1` then `.\start.ps1` |
| `[FAIL] Backend did not answer within 60 seconds` | The window shows the backend's real error below the FAIL line | Read the error; common fix: `.\stop.ps1` then `.\start.ps1` |
| Blank page at `localhost:5173` | Frontend still starting | Wait 5 seconds and reload; check the `start.ps1` window for `[FAIL]` |
| *Running scripts is disabled on this system* | PowerShell policy blocked the script | `Set-ExecutionPolicy -Scope Process Bypass` then retry |
| Window flashed and closed | You double-clicked the script; errors need a readable window | Open PowerShell, `cd C:\Users\visha\moviesforfuture`, `.\start.ps1` |

### Start the two servers manually (optional)

```powershell
# Window 1 - backend
cd C:\Users\visha\moviesforfuture\backend
& "C:\Users\visha\moviesforfuture\.venv\Scripts\python.exe" -m uvicorn app.main:app --port 8000 --no-access-log

# Window 2 - frontend
cd C:\Users\visha\moviesforfuture\frontend
npm run dev
```
Stop each with `Ctrl+C`, or from a third window: `.\stop.ps1`.

## Demo data

`samples/watched_history.csv` — 28 rows covering every cleaning case: duplicates,
a missing movie name, an invalid rating (`Casablanca,eleven`), two ambiguous titles
(*Interstellar* and *Forrest Gump* exist twice in the catalogue) and one unmatched row.
`samples/watched_history.pdf` — the same idea as a PDF table.

Upload either file on the **Upload** page to see the full cleaning → matching →
import flow.

## Testing

```powershell
.\test.ps1          # full suite (~20s, 78 tests)
.\test.ps1 -All     # include tests marked "slow"
```

Every test gets its own temporary SQLite database and a 25-movie fixture catalogue,
so tests never touch your real data and always run in parallel-safe isolation.

## API overview

| Area | Endpoints |
|------|-----------|
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| Uploads | `POST /api/upload/csv`, `POST /api/upload/pdf`, `GET /api/imports/{id}`, `POST /api/imports/{id}/clean`, `POST /api/imports/{id}/confirm-matches`, `POST /api/imports/{id}/confirm` |
| Movies | `GET /api/movies`, `GET /api/movies/genres`, `GET /api/movies/{id}`, `POST /api/movies/{id}/watched` |
| Analytics | `GET /api/analytics/summary`, `GET /api/analytics/genres`, `GET /api/analytics/ratings` |
| Mining | `POST /api/mining/kmeans`, `POST /api/mining/apriori`, `POST /api/mining/naive-bayes`, `GET /api/mining/runs` |
| Recommendations | `GET /api/recommendations`, `GET /api/recommendations/{movie_id}` |

## Project structure

```
moviesforfuture/
├── backend/
│   ├── app/
│   │   ├── routes/          # FastAPI routers (auth, upload, movies, analytics, mining, recommendations)
│   │   ├── services/        # parsing, cleaning, matching, analytics, mining, recommendations
│   │   ├── database/        # schema.sql, connection, seed, repositories
│   │   ├── config.py        # paths, limits, JWT settings
│   │   └── main.py          # app factory, CORS, error handlers
│   ├── seed/tmdb_5000_movies.csv
│   ├── scripts/make_sample_pdfs.py
│   └── tests/               # 78 tests + fixtures (25-movie CSV, sample PDFs)
├── frontend/
│   └── src/
│       ├── pages/           # Login, Register, Dashboard, Upload, Cleaning, Movies, Analytics, Mining, Recommendations
│       ├── components/      # Navbar, charts, cards, ui primitives
│       └── services/api.js  # Axios instance with auth interceptor
├── samples/                 # demo upload files
├── logs/                    # server logs written by start.ps1 (git-ignored)
├── start.ps1                # ONE command: start backend + frontend, ENTER stops both
├── stop.ps1                 # ONE command: stop everything, frees ports
├── test.ps1                 # run the test suite
└── deploy.ps1               # ONE command: redeploy both to Vercel
```

## Deployment (Vercel + Turso — free, no credit card)

**Live URLs:**
- Frontend: https://frontend-zeta-ruddy-93.vercel.app
- Backend:  https://backend-delta-vert-20.vercel.app
- Demo login: `demo@cinemine.dev` / `secret123`

**Architecture:** Vercel (2 projects) + Turso (serverless SQLite)
- Backend: `backend/` root → FastAPI (Python 3.12, 354 MB bundle)
- Frontend: `frontend/` root → Vite/React (SPA rewrite)
- DB: Turso free tier (no card), seeded once with 4,803 movies + 11,927 genre rows

**Environment variables (set on Vercel projects):**

| Project | Variable | Value |
|---------|----------|-------|
| Backend | `TURSO_DATABASE_URL` | `libsql://...` (from `turso db create`) |
| Backend | `TURSO_AUTH_TOKEN` | from `turso db tokens create` |
| Backend | `CINEMINE_JWT_SECRET` | random string (auto-generated) |
| Backend | `CINEMINE_MAX_FILE_MB` | `4` (Vercel body limit is 4.5 MB) |
| Backend | `MPLCONFIGDIR` | `/tmp` (matplotlib font cache) |
| Backend | `CINEMINE_CORS_ORIGINS` | `https://frontend-zeta-ruddy-93.vercel.app` |
| Frontend | `VITE_API_URL` | `https://backend-delta-vert-20.vercel.app/api` |

**Redeploy after code changes:**
```powershell
.\deploy.ps1
```

**One-time setup (already done):**
1. `vercel login`
2. `irm get.tur.so/install.ps1 | iex` → `turso auth signup` (GitHub) → `turso db create cinemine` → `turso db tokens create cinemine`
3. Run `backend/scripts/seed_turso.py` (batched multi-row INSERTs, ~2 min)

**Limits & notes:**
- Vercel Hobby: 500 MB Python bundle limit (ours: 354 MB ✅), 4.5 MB request body limit (upload limit set to 4 MB for friendly errors)
- `MAX_FILE_SIZE_MB=10` locally → `4` on Vercel
- Cold start: ~5-8 s (pandas/sklearn imports + Turso count check). Pre-seeded DB skips movie import.
- `start.ps1` / `stop.ps1` / `test.ps1` unchanged for local dev.
