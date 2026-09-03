from fastapi import FastAPI

from app.routers import artifact, health, image

app = FastAPI(title="Image Push/Pull Service")

app.include_router(health.router)
app.include_router(image.router)
app.include_router(artifact.router)