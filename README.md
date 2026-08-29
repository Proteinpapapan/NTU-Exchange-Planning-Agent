# NTU Exchange Planner

Local agentic planner for **GEM Explorer** and **SUSEP**. It joins Coursefinder
approved mappings with a chat UI, and only asks for two things if you leave them
out: your **degree programme** and which of the **four exchange terms** you want.

## Run locally (Windows)

You need Python 3.11+ and Node.js 20+.

```powershell
cd "C:\Users\black\Desktop\NTU Exchange Planner"
.\start.ps1
```

Then open [http://localhost:3000](http://localhost:3000).

The Groq key lives in `backend/.env` (gitignored). Copy `backend/.env.example`
if you need to replace it.

Manual start:

```powershell
# backend
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn api.chat:app --app-dir src --reload --port 8000

# frontend (another terminal)
cd frontend
npm install
npm run dev
```

## What it does

- Lists partner universities that have **at least one Approved** mapping for your
  degree. Empty catalogues and rejected-only universities are omitted.
- **Show more** loads more mappings from SQL, including the expanded Coursefinder
  fields (syllabus, contact hours, assessment, host credits).
- **Know more about this university** runs a short research briefing.
- AU conversion (e.g. 2 ECTS ≈ 1 AU) and FX to SGD if your budget is not in SGD.

## Agents

Intake → gate (degree + term) → decomposition → mapping / AU / currency /
research → reflection → structured cards.
