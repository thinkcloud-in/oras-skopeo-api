import os
import shutil
import subprocess
import tempfile
import zipfile

from fastapi import HTTPException

from app.schemas.requests import OrasPullRequest, OrasPushRequest

EXCLUDED_ARTIFACT_FILES = {"version_metadata.json"}


def push_artifact(req: OrasPushRequest):
    if not os.path.exists(req.file_path):
        raise HTTPException(404, f"File not found: {req.file_path}")
    dest = f"{req.harbor_url}/{req.project}/{req.artifact_name}:{req.tag}"

    extract_dir = tempfile.mkdtemp(prefix="oras-push-")
    try:
        try:
            with zipfile.ZipFile(req.file_path, "r") as zf:
                zf.extractall(extract_dir)
        except zipfile.BadZipFile:
            raise HTTPException(400, f"Not a valid zip file: {req.file_path}")

        push_files = []
        for root, _, files in os.walk(extract_dir):
            for fname in files:
                if fname in EXCLUDED_ARTIFACT_FILES:
                    continue
                push_files.append(os.path.relpath(os.path.join(root, fname), extract_dir))

        if not push_files:
            raise HTTPException(400, "Zip contained no files to push after excluding version_metadata.json")

        cmd = ["oras", "push", dest, *push_files, "-u", req.username, "-p", req.password, "--disable-path-validation"]
        if req.plain_http:
            cmd.append("--plain-http")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10800, cwd=extract_dir)
        if result.returncode != 0:
            raise HTTPException(500, detail=result.stderr)

        os.remove(req.file_path)

        return {"status": "success", "output": result.stdout, "pushed_to": dest, "files_pushed": push_files}
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)


def pull_artifact(req: OrasPullRequest):
    os.makedirs(req.dest_dir, exist_ok=True)
    src = f"{req.harbor_url}/{req.project}/{req.artifact_name}:{req.tag}"
    cmd = ["oras", "pull", src, "-u", req.username, "-p", req.password,
           "-o", req.dest_dir, "--allow-path-traversal"]
    if req.plain_http:
        cmd.append("--plain-http")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10800)
    if result.returncode != 0:
        raise HTTPException(500, detail=result.stderr)

    pulled_files = os.listdir(req.dest_dir)
    if not pulled_files:
        raise HTTPException(500, "oras pull succeeded but no files were returned")

    # Safety net: push is supposed to extract zips before pushing, but if a raw
    # zip slipped through (old data, or push-side extraction failed), unzip it
    # here so the caller always gets real files back, never a zip.
    for fname in pulled_files:
        fpath = os.path.join(req.dest_dir, fname)
        if os.path.isfile(fpath) and fname.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(fpath, "r") as zf:
                    zf.extractall(req.dest_dir)
            except zipfile.BadZipFile:
                continue
            os.remove(fpath)

    for root, _, files in os.walk(req.dest_dir):
        for fname in files:
            if fname in EXCLUDED_ARTIFACT_FILES:
                os.remove(os.path.join(root, fname))

    pulled_files = os.listdir(req.dest_dir)
    if not pulled_files:
        raise HTTPException(500, "pull succeeded but no files remained after unzip/cleanup")

    return {
        "status": "success",
        "output": result.stdout,
        "pulled_from": src,
        "files": pulled_files,
        "dest_dir": req.dest_dir,
    }
