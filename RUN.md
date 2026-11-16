# Running LunaSafe AI on a new machine

You need Python 3 and Node.js installed. Use two terminals.

## 1. Backend (terminal 1)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Check it works: open http://127.0.0.1:8000/api/health. You should see {"status":"ok", ...}.

If the page shows "Backend Error", add the page's address (for example http://localhost:5173) to CORS_ORIGINS in backend/.env, then restart the backend.

## 2. Frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Open the address that npm prints (for example http://localhost:5173).

## 3. Demo

On the Upload page click "Load known-site case study" (pre-computed demo data, labelled is_mock: true).
Real model inference through the backend (/api/infer) is not integrated yet.
