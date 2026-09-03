from fastapi import APIRouter

from app.controllers import artifact_controller
from app.schemas.requests import OrasPullRequest, OrasPushRequest

router = APIRouter(tags=["Artifact"])


@router.post("/push/artifact")
def push_artifact(req: OrasPushRequest):
    return artifact_controller.push_artifact(req)


@router.post("/pull/artifact")
def pull_artifact(req: OrasPullRequest):
    return artifact_controller.pull_artifact(req)
