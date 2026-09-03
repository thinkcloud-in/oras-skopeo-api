# Image Push/Pull Service

FastAPI service jo `skopeo` (container images) aur `oras` (OCI artifacts) ko wrap karke Harbor registry ke saath push/pull operations expose karta hai.

## Project Structure

```
oras_skopeo_api/
├── main.py                      # entrypoint (`uvicorn main:app`)
├── requirements.txt
└── app/
    ├── main.py                  # FastAPI app + router registration
    ├── routers/                 # endpoint declarations
    │   ├── health.py
    │   ├── image.py
    │   └── artifact.py
    ├── controllers/             # business logic (skopeo/oras subprocess calls)
    │   ├── health_controller.py
    │   ├── image_controller.py
    │   └── artifact_controller.py
    ├── schemas/
    │   └── requests.py          # Pydantic request models
    └── utils/
        └── archive.py           # tar archive type detection
```

## Prerequisites

- Python 3.10+
- `skopeo` aur `oras` CLI binaries system PATH me installed hone chahiye (in ke bina `/health` aur push/pull endpoints fail honge).

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

ya seedha:

```bash
python main.py
```

Swagger docs: http://127.0.0.1:8080/docs

## Endpoints

- `GET /health` — skopeo/oras availability check
- `POST /push/image` — skopeo se image push (tar → registry)
- `POST /pull/image` — skopeo se image pull (registry → tar)
- `POST /push/artifact` — oras se zip artifact push
- `POST /pull/artifact` — oras se artifact pull
