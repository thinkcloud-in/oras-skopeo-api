import json
import logging
import os
import shutil
import subprocess
import time

import requests

from fastapi import HTTPException

from app.schemas.requests import ProxmoxPushRequest

logger = logging.getLogger(__name__)


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


def _run_curl_upload(req: ProxmoxPushRequest) -> dict:
    """A single upload attempt. Raises RuntimeError on any failure -- caller retries."""
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
        raise RuntimeError(f"curl upload failed (exit {result.returncode}): {result.stderr.decode(errors='replace')}")

    try:
        upload_data = json.loads(result.stdout.decode())
    except json.JSONDecodeError:
        raise RuntimeError(f"Proxmox returned non-JSON response: {result.stdout[:500]!r}")

    upid = upload_data.get("data")
    if not upid:
        raise RuntimeError(f"Proxmox upload response had no task UPID: {upload_data}")

    return upload_data


def _cleanup_staged_file(req: ProxmoxPushRequest):
    """
    Removes the pulled artifact from this pod's PV once Proxmox confirms
    it has the file -- nothing downstream ever needs it again (VM creation
    uses Proxmox's own import_volid reference, not this file). Only ever
    called after success; a failed push leaves the file in place so a
    retry doesn't have to re-pull from Harbor.
    """
    try:
        staged_dir = os.path.dirname(req.file_path)
        if staged_dir and os.path.isdir(staged_dir):
            shutil.rmtree(staged_dir, ignore_errors=True)
            logger.info(f"Cleaned up staged artifact directory: {staged_dir}")
        elif os.path.exists(req.file_path):
            os.remove(req.file_path)
            logger.info(f"Cleaned up staged artifact file: {req.file_path}")
    except Exception as e:
        # Non-fatal: the push itself already succeeded, a leftover file on
        # the PV is disk-space hygiene, not a reason to fail the request.
        logger.warning(f"Could not clean up staged file {req.file_path} (non-fatal): {e}")


def push_to_proxmox(req: ProxmoxPushRequest) -> dict:
    if not os.path.exists(req.file_path):
        raise HTTPException(404, f"File not found: {req.file_path}")

    last_error = None
    upload_data = None
    for attempt in range(1, req.max_retries + 1):
        try:
            upload_data = _run_curl_upload(req)
            break
        except RuntimeError as e:
            last_error = e
            logger.warning(f"Upload attempt {attempt}/{req.max_retries} failed: {e}")
            if attempt < req.max_retries:
                time.sleep(req.retry_delay_seconds)

    if upload_data is None:
        raise HTTPException(
            500,
            f"Upload to {req.node_name}:{req.storage} failed after {req.max_retries} attempts: {last_error}",
        )

    upid = upload_data.get("data")
    task_result = _poll_upid(req, upid)

    _cleanup_staged_file(req)

    return {
        "status": "success",
        "upid": upid,
        "task": task_result,
        "storage": req.storage,
        "node": req.node_name,
        "filename": req.filename,
    }
