# Vision Analytics POC — People, Vehicles, Dwell Time & Attributes

Detects people & vehicle counts, how long each person stays in frame, vehicle
types, and attempts jacket/uniform/cap/shoes attribute detection — from a
recorded video first, with a clear path to plug in real CCTV/RTSP later.
Built on **Ultralytics YOLO26** (released Jan 2026) for detection + tracking,
and **YOLOE-26** (open-vocabulary) for the attributes that aren't standard
COCO classes.

```
crowd-vision-poc/
├── backend/                    FastAPI + YOLO26 (Python)
│   ├── main.py                 App entrypoint — run this
│   ├── config.py                All settings, loaded from .env
│   ├── requirements.txt
│   ├── .env.example            Copy to .env
│   ├── routes/                 API endpoints (what Swagger shows you)
│   │   ├── video_routes.py     upload / list / process / poll / results
│   │   ├── stream_routes.py    live CCTV connect
│   │   └── health_routes.py
│   ├── services/                The actual CV logic
│   │   ├── detector.py          YOLO26 detection + tracking (person/vehicle)
│   │   ├── attribute_classifier.py   YOLOE-26 open-vocab (jacket/cap/shoes)
│   │   ├── video_processor.py   orchestrates the whole pipeline per video
│   │   └── job_manager.py       tracks background jobs by job_id
│   ├── models/
│   │   └── schemas.py           request/response shapes (drives Swagger)
│   ├── utils/
│   │   ├── logger.py
│   │   └── draw_utils.py        bounding-box drawing for annotated output
│   ├── data/
│   │   ├── videos/              <- put/upload test videos here
│   │   │   └── sample_test_video.mp4   (your uploaded clip, pre-loaded)
│   │   └── weights/              YOLO26 / YOLOE-26 .pt files auto-download here
│   ├── credentials/
│   │   └── cctv_credentials.example.json   copy -> cctv_credentials.json for real RTSP creds
│   └── outputs/
│       ├── processed_videos/     annotated .mp4 output per job
│       └── reports/              JSON report per job
└── frontend/                    React (Vite) dashboard
    └── src/
        ├── api.js                all backend calls in one place
        ├── App.jsx
        └── components/
            ├── VideoSourceSelector.jsx   pick existing/upload/live
            ├── JobProgress.jsx           polls job status
            └── ResultsDashboard.jsx      counts, table, annotated video
```

## How the pieces fit together (the plan)

1. **Detection + tracking (`services/detector.py`)** — YOLO26 finds every
   person, car, truck, bus, motorcycle, bicycle in each frame. Its built-in
   BoT-SORT tracker gives each one a **persistent ID** across frames — that's
   what lets us compute "person #7 stayed 14.2 seconds" instead of just
   counting boxes per frame.

2. **Attributes (`services/attribute_classifier.py`)** — "jacket", "cap",
   "uniform", "shoes" have no fixed class in the standard COCO model YOLO26
   ships with. Two options, and this project is wired for both:
   - **Now (POC):** YOLOE-26, Ultralytics' open-vocabulary model — you just
     give it text prompts like `"cap"`, `"safety vest"`, `"boots"` at runtime,
     no training needed. Good enough to validate the idea today.
   - **Later (production accuracy):** fine-tune a small YOLO26 model on your
     own labelled site photos. You'd only change `ATTRIBUTE_MODEL` in `.env`
     — nothing else in the pipeline changes.

3. **Orchestration (`services/video_processor.py`)** — reads the video frame
   by frame with OpenCV, runs steps 1–2, keeps a running dwell-time record per
   track ID, draws boxes onto an output video, and writes a JSON report.

4. **API (`routes/`)** — wraps that pipeline as HTTP endpoints so both
   Swagger UI and the React frontend can trigger jobs and poll results.

5. **Frontend (`frontend/`)** — lets you pick a video (existing file, new
   upload, or a live camera), watch progress, then see counts, a dwell-time
   table, attribute Yes/No badges per person, and the annotated video.

## Does the video path go through frontend or backend?

**Backend controls the actual video paths.** The frontend never sends a raw
filesystem path — it just says "process `sample_test_video.mp4`" or uploads
bytes. This is deliberate:
- Videos live in `backend/data/videos/`. Drop a new file there (or hit
  **Upload** in the frontend, which saves it there for you) and it's
  immediately selectable — no code change needed to test a new clip.
- The backend resolves the filename to a real path, so the frontend/browser
  never needs filesystem access, and later swapping in RTSP is just
  supplying a different "source" the same way (see below).

## Testing the backend by itself — Swagger UI

You don't need the frontend to verify the backend works. FastAPI
auto-generates an interactive test page:

```
http://localhost:8000/docs      <- Swagger UI, click "Try it out" on any endpoint
http://localhost:8000/redoc     <- read-only alternative view
```

Suggested test order in Swagger:
1. `GET /api/health` — confirms server + config are up
2. `GET /api/videos/list` — should show `sample_test_video.mp4`
3. `POST /api/videos/process` — body `{"filename": "sample_test_video.mp4"}` → copy the returned `job_id`
4. `GET /api/videos/jobs/{job_id}` — poll until `status: completed`
5. `GET /api/videos/jobs/{job_id}/results` — full JSON report (counts, dwell times, attributes)
6. Open `http://localhost:8000/outputs/processed_videos/{job_id}.mp4` in a browser to see the annotated video

This is the fastest way to confirm the model logic is correct before
touching the frontend at all.

## Setup

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```
First request that touches a model will auto-download `yolo26m.pt` /
`yoloe-26m-seg.pt` into `data/weights/` (needs internet once). If you're on
CPU only, that's fine — `DEVICE=cpu` in `.env` already; switch to `cuda:0`
once you have a GPU box for the real CCTV workload (video is much heavier
than a single image).

### Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Open `http://localhost:5173`.

## Plugging in real CCTV tomorrow

1. `cp backend/credentials/cctv_credentials.example.json backend/credentials/cctv_credentials.json`
2. Fill in each camera's real RTSP URL (this file is git-ignored — it never
   gets committed).
3. In the frontend, switch to the **Live CCTV** tab and pick the camera — or
   call `POST /api/streams/connect` directly in Swagger.
4. Under the hood this is almost no new code: `cv2.VideoCapture()` accepts an
   `rtsp://` URL exactly like a file path, so `video_processor.py` is reused
   unchanged. Live streams should run on a machine with a GPU (`DEVICE=cuda:0`)
   for real-time performance — the CPU setting above is fine for POC clips.

## Known POC limitations (worth knowing going in)

- **Attribute accuracy**: open-vocabulary detection (YOLOE) is convenient but
  less precise than a purpose-trained model — treat jacket/cap/shoes results
  as indicative, not compliance-grade, until you fine-tune on real site
  photos (swap-in point already exists, see `.env` → `ATTRIBUTE_MODEL`).
- **Job store is in-memory** (`services/job_manager.py`) — fine for a POC,
  but jobs are lost on server restart and it won't scale across multiple
  backend processes. Swap for Redis + a task queue (Celery/RQ) when moving
  past POC; no other file needs to change.
- **Live stream duration** in `stream_routes.py` is a simple POC-bounded
  session, not a 24/7 always-on worker — that's a follow-up once the
  detection logic itself is validated.
