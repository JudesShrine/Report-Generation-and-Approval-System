# Report Generation and Approval System

FastAPI-based web application for creating, managing, sharing and approving reports.

## Run locally

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload
```

Open the local URL shown by Uvicorn.

## Deploy on Render

This repository contains `render.yaml`, so Render can use:

- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Important database note

This starter deployment keeps the application's existing database approach. Render web-service filesystems are not intended as permanent database storage. For a real public deployment, connect the application to Render PostgreSQL (or another persistent database) and store uploaded files in persistent/object storage.

## GitHub

Do not commit passwords, API keys, `.env` files, database files, or private uploaded documents.
