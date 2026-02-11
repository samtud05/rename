# CM360 Creative Renamer

Rename creative files to CM360 names using fuzzy matching against a T-sheet (Excel/CSV).

## Local development

### Backend (Python)

```bash
cd backend
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — Vite proxies `/api` to the backend on port 8000.

## Deploy to Render (free)

1. Sign up at [dashboard.render.com](https://dashboard.render.com/register) (GitHub or email).
2. **New → Web Service**, connect your GitHub repo.
3. Set:
   - **Root Directory:** (leave blank)
   - **Build Command:**
     ```bash
     cd frontend && npm install && npm run build && mkdir -p ../backend/static && cp -r dist/* ../backend/static/ && cd .. && pip install -r backend/requirements.txt
     ```
   - **Start Command:**
     ```bash
     uvicorn backend.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Environment:** Python 3 (Render will detect it; you can set Python version in Environment if needed).
4. Deploy. Your app will be at `https://<your-service>.onrender.com`.

No login required for app users; the link is private unless you share it.

## Usage

1. Upload a **ZIP** of creatives (any structure; filenames are used for matching).
2. Upload the **T-sheet** (Excel `.xlsx` or CSV) with a column containing CM360 creative names (auto-detected or use a column header like "creative name").
3. Set the **confidence threshold** (e.g. 70%). Matches below this are flagged in the preview.
4. Click **Preview mapping** to see old name → new name and score.
5. Click **Download renamed ZIP** to get the ZIP with CM360 names (extension preserved).
6. Click **Download CSV log** to get a log of Old Name, New Name, Match %.

## Tech

- **Backend:** FastAPI, pandas, openpyxl, RapidFuzz
- **Frontend:** React, Vite
- **Hosting:** Render (Web Service, free tier)
