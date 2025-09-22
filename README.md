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