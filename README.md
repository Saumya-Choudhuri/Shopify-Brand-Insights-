# Shopify-Brand-Insights-
NO OFFICIAL SHOPIFY API

## Run in GitHub Codespaces

1. Open the repo in Codespaces.
2. Terminal:
   ```bash
   python app.py
   You should then see something like: * Running on http://0.0.0.0:8000
   Once that appears:
	1.	In Codespaces, go to the PORTS tab.
	2.	Look for port 8000.
	3.	Click Open in Browser.
	4.	Add /static/index.html at the end of the URL to open the frontend.


   ## DB setup
By default, snapshots are stored in SQLite (`data.db`).  
To use MySQL, set:
DATABASE_URL=mysql+pymysql://user:pass@host:3306/dbname

## New endpoints
- POST `/api/brand-context` — same as before (now validated with Pydantic).
- POST `/api/brand-context/save` — crawls and **persists** a JSON snapshot.  
  Body: `{"website_url":"https://brand.com"}`
- GET `/api/snapshots` — lists latest saved snapshots (id, url, timestamp).
- POST `/api/competitors` — best-effort discovery of 2–3 competitor stores and returns their contexts.

before step one reffer .env.example then,
After reopening, run pip install -r requirements.txt to reinstall your dependencies.

## Deploy to Render (free tier)
1. Push the latest changes to GitHub: ensure `.gitignore`, `.env.example`, and `render.yaml` are committed.
2. Create a Render account (no card needed) and click **New + → Web Service**.
3. Connect the GitHub repo and select it. Render auto-detects `render.yaml`; keep the defaults.
4. On first deploy, Render installs dependencies with `pip install -r requirements.txt` and starts with `gunicorn -b 0.0.0.0:$PORT app:app`.
5. In the Render dashboard, confirm the `DATABASE_URL` environment variable is present (from `render.yaml`). For production data, switch to a managed database (Render PostgreSQL) instead of SQLite.
6. Once the service is live, grab the generated HTTPS URL and share it. Enable auto-deploys from `main` so each push redeploys automatically.

> SQLite on Render lives on the ephemeral container filesystem. Redeploys wipe it, so use it for demos only.

## Maintain local environment
1. Copy `.env.example` to `.env` whenever you set up a new workspace.
2. Adjust `DATABASE_URL` as needed (SQLite by default, or provide MySQL/RDS connection strings).
3. Install dependencies with:

    ```bash
    pip install -r requirements.txt
    ```