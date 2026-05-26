# ListifyAI Setup Guide

## Requirements
- Python 3.11+
- Node.js 18+
- PostgreSQL database
- ffmpeg (for video generation)

## Quick Start

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
cp .env.example .env
# Fill in .env values
alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
npm install
cp .env.example .env.local
# Fill in .env.local values
npm run dev
```

## Running the App
- Use start-backend.bat / start-backend.sh for backend
- Use start-frontend.bat / start-frontend.sh for frontend
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

## Notes
- Keep all installs local to this project.
- The Python virtual environment lives at backend/venv/.
- If migrations fail, set DATABASE_URL in backend/.env first.
- Install ffmpeg manually if `ffmpeg -version` is not available.

## Troubleshooting

ACTION REQUIRED: Please install ffmpeg manually:
  Windows: Download from https://ffmpeg.org/download.html and add to PATH
  Mac: brew install ffmpeg
  Ubuntu: sudo apt-get install ffmpeg

ACTION REQUIRED: Set DATABASE_URL in backend/.env before running migrations.
Example: DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/listifyai
