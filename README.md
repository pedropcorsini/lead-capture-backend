# Lead Capture Backend

REST API for an event lead capture system. Registers leads, stores photos and generated cards in AWS S3, creates QR codes for card downloads, and exposes an API-key protected admin panel.

**Frontend:** [lead-capture-frontend](https://github.com/pedropcorsini/lead-capture-frontend)
**Live API:** https://lead-capture-backend-production.up.railway.app

## Tech Stack

- **Python 3** + **FastAPI**
- **SQLAlchemy** (ORM)
- **PostgreSQL** (hosted on Railway)
- **AWS S3** (photo and card storage)
- **Pillow** (final card image generation)
- **qrcode** (QR code generation)

## Features

- Two-step, token-based lead registration flow
- Accepts a photo already composed with the event frame, sent by the frontend
- Generates the final card (photo + lead data + QR code) and stores it in S3
- Serves downloads through temporary signed S3 URLs, no public bucket exposure
- Admin panel authenticated via an API key header, with search by name or document number and paginated results

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/leads` | Creates a lead, returns an access token |
| POST | `/leads/{token}/foto` | Uploads the composed photo |
| POST | `/leads/{token}/gerar-card` | Builds the final card and stores it in S3 |
| GET | `/leads/{token}/qrcode` | Generates the QR code for download |
| GET | `/leads/{token}/download-card` | Redirects to a temporary signed S3 URL |
| GET | `/admin/leads` | Lists/searches leads, paginated |
| GET | `/admin/leads/{lead_id}` | Returns a single lead's details |
| GET | `/admin/leads/{lead_id}/download-card` | Downloads a specific lead's card |

Admin routes require an `X-Admin-Api-Key` header.

## Project Structure

```
main.py            # API routes
models.py          # Lead model (SQLAlchemy)
database.py        # Database connection
storage.py         # S3 upload/download and signed URLs
validations.py      # CPF, phone, and postal code validation
card_generator.py    # Final card image generation (Pillow)
qr_code.py          # QR code generation
assets/molduras/      # PNG files for the 4 available frames
assets/fonts/        # Embedded font used on the card
```

## Getting Started

```bash
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\activate         # Windows

pip install -r requirements.txt
cp .env.example .env           # fill in your own values
uvicorn main:app --reload
```

The API runs at `http://localhost:8000`. Tables are created automatically on first run.

## Deploy

Deployed on Railway, with automatic deploys from the `main` branch.
