import json
import os
import subprocess
import time

import requests

from fastapi import HTTPException

from app.schemas.requests import ProxmoxPushRequest


def _proxmox_api_base(req: ProxmoxPushRequest) -> str:
    return f"https://{req.node_host}:8006/api2/json"


def _poll_upid(req: ProxmoxPushRequest, upid: str) -> dict:
    """
    Polls Proxmox's task-status endpoint until the import task finishes.
    Uploading the file is only step one -- Proxmox still has to write and
    verify it on the target storage afterward, which this waits out.
    """
    url = f"{_proxmox_api_base(req)}/nodes/{req.node_name}/tasks/{upid}/status"
    headers = {"Authorization": f"PVEAPIToken={req.proxmox_token}"}
    deadline = time.time() + req.poll_timeout

    while time.time() < deadline:
        resp = requests.get(url, headers=headers, verify=req.tls_verify, timeout=15)
        if resp.status_code >= 400:
            raise HTTPException(500, f"Failed to poll task {upid}: {resp.text}")
        status = resp.json().get("data", {})
        if status.get("status") == "stopped":
            if status.get("exitstatus") != "OK":
                raise HTTPException(500, f"Proxmox import task {upid} failed: {status.get('exitstatus')}")
            return status
        time.sleep(5)

    raise HTTPException(504, f"Timed out waiting for Proxmox task {upid} to finish")


def push_to_proxmox(req: ProxmoxPushRequest) -> dict:
    if not os.path.exists(req.file_path):
        raise HTTPException(404, f"File not found: {req.file_path}")

    url = f"{_proxmox_api_base(req)}/nodes/{req.node_name}/storage/{req.storage}/upload"

    cmd = [
        "curl", "-s", "-S",
        "-H", f"Authorization: PVEAPIToken={req.proxmox_token}",
        "-F", "content=import",
        "-F", f"filename=@{req.file_path};filename={req.filename};type=application/octet-stream",
        url,
    ]
    if not req.tls_verify:
        cmd.insert(1, "-k")

    result = subprocess.run(cmd, capture_output=True, timeout=7200)
    if result.returncode != 0:
        raise HTTPException(
            500,
            f"curl upload failed (exit {result.returncode}): {result.stderr.decode(errors='replace')}",
        )

    try:
        upload_data = json.loads(result.stdout.decode())
    except json.JSONDecodeError:
        raise HTTPException(500, f"Proxmox returned non-JSON response: {result.stdout[:500]!r}")

    upid = upload_data.get("data")
    if not upid:
        raise HTTPException(500, f"Proxmox upload response had no task UPID: {upload_data}")

    task_result = _poll_upid(req, upid)

    return {
        "status": "success",
        "upid": upid,
        "task": task_result,
        "storage": req.storage,
        "node": req.node_name,
        "filename": req.filename,
    }
