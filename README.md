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

## Getting started

Prerequisites: Python 3.12+, Node 18+, npm.

```powershell
# 1. Backend virtualenv + dependencies
python -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt

# 2. Frontend dependencies (first run)
cd frontend; npm install; cd ..

# 3. Run both servers
.\start.ps1
```

- Frontend: http://localhost:5173
- Backend API + Swagger docs: http://127.0.0.1:8000/docs

`.\start.ps1 -Backend` or `.\start.ps1 -Frontend` starts just one side.

The database (`backend/data/cinemine.db`) and the movie catalogue
(`backend/seed/tmdb_5000_movies.csv`, max 5,000 rows) are created automatically on
first start.

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
├── start.ps1                # run backend + frontend
└── test.ps1                 # run the test suite
```
