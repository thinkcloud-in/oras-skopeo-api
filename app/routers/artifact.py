from fastapi import APIRouter

from app.controllers import artifact_controller, proxmox_controller
from app.schemas.requests import OrasPullRequest, OrasPushRequest, ProxmoxPushRequest


router = APIRouter(tags=["Artifact"])


@router.post("/push/artifact")
def push_artifact(req: OrasPushRequest):
    return artifact_controller.push_artifact(req)


@router.post("/pull/artifact")
def pull_artifact(req: OrasPullRequest):
    return artifact_controller.pull_artifact(req)

@router.post("/push/artifact/proxmox")
def push_to_proxmox(req: ProxmoxPushRequest):
    return proxmox_controller.push_to_proxmox(req)