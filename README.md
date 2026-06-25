Link zu Lovable:
https://lovable.dev/projects/b16d71fb-65b7-4446-8043-1bec85ef0be1?magic_link=mc_6f381dd5-701e-436f-8c93-1d1387b33df4

# HackerthonITEvents

A small app to collect and display IT events. FastAPI + SQLModel + SQLite backend, React (Vite) frontend.

## How to run it

### Backend (http://localhost:8000)

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

API docs are at http://localhost:8000/docs. The SQLite database (`events.db`) is created automatically on first start.

> If `python3 -m venv` fails with an `ensurepip` error (Debian/Ubuntu), either install the venv package (`sudo apt install python3-venv`) or bootstrap pip manually:
> ```bash
> python3 -m venv --without-pip .venv
> python3 -c "import urllib.request; urllib.request.urlretrieve('https://bootstrap.pypa.io/get-pip.py', '/tmp/get-pip.py')"
> .venv/bin/python /tmp/get-pip.py
> ```

### Frontend (http://localhost:5173)

```bash
cd frontend
npm install
npm run dev
```

Run the backend and frontend in separate terminals. The frontend talks to the backend at `http://localhost:8000`; CORS is already configured for the Vite dev server.
