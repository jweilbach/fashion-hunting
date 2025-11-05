# ABMC Phase 1 Automation — Media Tracker & Reporting

This starter kit gets you live with:
1) **Daily Media Tracker** → Google Sheets + recap email text (printed to stdout or optional Gmail API).
2) **Monthly Slides Deck** → Google Slides API (blank deck + example batch requests).

---

## Quick Start

### 0) Create a Google Cloud Service Account (Sheets + Slides)
- Create a GCP project → enable **Google Sheets API** and **Google Slides API**.
- Create a **Service Account**, then create a **JSON key** and download it.
- Save it as `gcp_service_account.json` in the project root (same folder as this README).
- Share your Google Sheet with the service account email (it looks like `xyz@xyz.iam.gserviceaccount.com`).

### 1) Install Python deps
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure feeds and settings
- Edit `config/feeds.yaml` (your brands, competitors, and RSS/Google Alerts)
- Copy `config/settings.example.yaml` to `config/settings.yaml` and fill values.
- Copy `.env.example` to `.env` and fill secrets (OpenAI API key, etc.).

### 3) Create your Google Sheet
- Create a spreadsheet named exactly as `sheet_name` in `config/settings.yaml`.
- The script will create a worksheet `Clips` with headers if it doesn't exist.

### 4) Run daily tracker
```bash
source .venv/bin/activate
python src/fetch_and_report.py
```
It will append rows to Google Sheets and print an email-ready daily recap body.

### 5) Create a monthly Slides deck
```bash
python src/create_slides.py
```
It prints a URL to your new deck. You can expand the `requests_batch` to add slides.

---

## Cron (example)
Run daily at 8:15 AM:
```cron
15 8 * * * cd /opt/abmc_phase1 && . .venv/bin/activate && python src/fetch_and_report.py >> logs/daily.log 2>&1
```

## Docker (optional)
Build and run:
```bash
docker build -t abmc-phase1 .
docker run --rm -v $(pwd)/gcp_service_account.json:/app/gcp_service_account.json:ro --env-file .env abmc-phase1
```

## Notes
- **No client keys** are bundled. You must provide your own `gcp_service_account.json` and `.env`.
- The recap email content is printed to stdout; you can copy/paste into Gmail or wire a mail API later.
- Safe to run locally or on a small VM.
