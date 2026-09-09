from fastapi import APIRouter

from app.controllers import guacamole_controller
from app.schemas.requests import GuacamoleLogsDeleteRequest, GuacamoleRecordingsDeleteRequest

router = APIRouter(tags=["Guacamole"])


@router.post("/guacamole/logs/delete")
def delete_logs(req: GuacamoleLogsDeleteRequest):
    return guacamole_controller.delete_connection_history_logs(req)


@router.post("/guacamole/recordings/delete")
def delete_recordings(req: GuacamoleRecordingsDeleteRequest):
    return guacamole_controller.delete_recordings(req)
