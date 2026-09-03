import os
import subprocess

from fastapi import HTTPException

from app.schemas.requests import PullImageRequest, PushRequest
from app.utils.archive import detect_archive_type


def push_image(req: PushRequest):
    if not os.path.exists(req.source_path):
        raise HTTPException(404, f"Source file not found: {req.source_path}")
    dest = f"docker://{req.harbor_url}/{req.project}/{req.image_name}:{req.tag}"
    _detected_type = detect_archive_type(req.source_path) if req.source_path.endswith(".tar") else req.source_type
    src = f"{_detected_type}:{req.source_path}"  # tar ke andar jo actual name/tag hai wahi use hoga, custom naam sirf dest me
    cmd = ["skopeo", "copy", src, dest, f"--dest-creds={req.username}:{req.password}"]
    if not req.tls_verify:
        cmd.append("--dest-tls-verify=false")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10800)
    if result.returncode != 0:
        raise HTTPException(500, detail=result.stderr)
    return {"status": "success", "output": result.stdout, "pushed_to": dest}


def pull_image(req: PullImageRequest):
    os.makedirs(req.dest_dir, exist_ok=True)
    src = f"docker://{req.harbor_url}/{req.project}/{req.image_name}:{req.tag}"
    tar_filename = f"{req.image_name}-{req.tag}.tar"
    tar_path = os.path.join(req.dest_dir, tar_filename)
    if req.dest_type == "oci-archive":
        dest = f"oci-archive:{tar_path}:{req.tag}"
    elif req.dest_type == "docker-archive":
        dest = f"docker-archive:{tar_path}:{req.harbor_url}/{req.project}/{req.image_name}:{req.tag}"
    else:
        raise HTTPException(400, "dest_type must be 'oci-archive' or 'docker-archive'")
    cmd = ["skopeo", "copy", src, dest, f"--src-creds={req.username}:{req.password}"]
    if not req.tls_verify:
        cmd.append("--src-tls-verify=false")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10800)
    if result.returncode != 0:
        raise HTTPException(500, detail=result.stderr)
    if not os.path.exists(tar_path):
        raise HTTPException(500, "skopeo pull succeeded but .tar file not found")
    return {
        "status": "success",
        "output": result.stdout,
        "pulled_from": src,
        "tar_file": tar_path,
        "size_bytes": os.path.getsize(tar_path),
    }
