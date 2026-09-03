from fastapi import APIRouter

from app.controllers import image_controller
from app.schemas.requests import PullImageRequest, PushRequest

router = APIRouter(tags=["Image"])


@router.post("/push/image")
def push_image(req: PushRequest):
    return image_controller.push_image(req)


@router.post("/pull/image")
def pull_image(req: PullImageRequest):
    return image_controller.pull_image(req)
