import logging
import os
import shutil
import time
import paramiko
from fastapi import HTTPException
from app.schemas.requests import VmPushRequest

logger = logging.getLogger(__name__)
#test-cmnt

def _mkdir_p_remote(client, remote_dir: str):
    """mkdir -p over exec_command, waiting for and checking the actual exit status
    -- a fire-and-forget exec_command here silently masked permission/path
    failures before, only surfacing as a confusing 'No such file' from sftp.put."""
    if not remote_dir:
        return
    _, stdout, stderr = client.exec_command(f"mkdir -p {remote_dir}")
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        raise RuntimeError(f"mkdir -p {remote_dir} failed: {stderr.read().decode(errors='replace')}")


def _run_sftp_put(req: VmPushRequest):
    """
    A single transfer attempt. Raises RuntimeError on any failure -- caller
    retries. Handles both a single file (dest_path is the full remote file
    path) and a whole directory (dest_path is the remote directory the local
    directory's contents get mirrored into) -- a full HF-format model is a
    folder of files (config.json, tokenizer files, safetensors shards), not
    a single file like the template qcow2/GGUF cases.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            req.vm_host, username=req.vm_ssh_user, password=req.vm_ssh_pass,
            timeout=30, look_for_keys=False,
        )
        sftp = client.open_sftp()
        try:
            if os.path.isdir(req.file_path):
                _mkdir_p_remote(client, req.dest_path)
                for root, dirs, files in os.walk(req.file_path):
                    rel = os.path.relpath(root, req.file_path)
                    remote_root = req.dest_path if rel == "." else f"{req.dest_path}/{rel.replace(os.sep, '/')}"
                    _mkdir_p_remote(client, remote_root)
                    for fname in files:
                        sftp.put(os.path.join(root, fname), f"{remote_root}/{fname}")
            else:
                _mkdir_p_remote(client, os.path.dirname(req.dest_path))
                sftp.put(req.file_path, req.dest_path)
        finally:
            sftp.close()
    except Exception as e:
        raise RuntimeError(f"SFTP transfer to {req.vm_host}:{req.dest_path} failed: {e}")
    finally:
        client.close()


def _cleanup_staged_file(req: VmPushRequest):
    """
    Removes the pulled artifact from this pod's PV once the VM has it --
    same rationale as the Proxmox push's cleanup. Only ever called after
    success; a failed transfer leaves the file in place so a retry doesn't
    have to re-pull from Harbor.
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
        logger.warning(f"Could not clean up staged file {req.file_path} (non-fatal): {e}")


def push_to_vm(req: VmPushRequest) -> dict:
    if not os.path.exists(req.file_path):
        raise HTTPException(404, f"File not found: {req.file_path}")

    last_error = None
    for attempt in range(1, req.max_retries + 1):
        try:
            _run_sftp_put(req)
            break
        except RuntimeError as e:
            last_error = e
            logger.warning(f"VM transfer attempt {attempt}/{req.max_retries} failed: {e}")
            if attempt < req.max_retries:
                time.sleep(req.retry_delay_seconds)
    else:
        raise HTTPException(
            500,
            f"Transfer to {req.vm_host}:{req.dest_path} failed after {req.max_retries} attempts: {last_error}",
        )

    _cleanup_staged_file(req)

    return {
        "status": "success",
        "vm_host": req.vm_host,
        "dest_path": req.dest_path,
    }
