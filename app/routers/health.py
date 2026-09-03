from fastapi import APIRouter

from app.controllers import health_controller

router = APIRouter(tags=["Health"])


@router.get("/health")
def health():
    return health_controller.check_health()
