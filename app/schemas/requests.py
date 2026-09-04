from pydantic import BaseModel


class PushRequest(BaseModel):
    harbor_url: str
    username: str
    password: str
    project: str
    image_name: str
    tag: str
    source_path: str
    source_type: str = "oci-archive"
    tls_verify: bool = False


class PullImageRequest(BaseModel):
    harbor_url: str
    username: str
    password: str
    project: str
    image_name: str
    tag: str
    dest_dir: str = "/library/harbor/pull_images"
    dest_type: str = "oci-archive"
    tls_verify: bool = False


class OrasPushRequest(BaseModel):
    harbor_url: str
    username: str
    password: str
    project: str
    artifact_name: str
    tag: str
    file_path: str
    plain_http: bool = True


class OrasPullRequest(BaseModel):
    harbor_url: str
    username: str
    password: str
    project: str
    artifact_name: str
    tag: str
    dest_dir: str = "/library/harbor/pull_artifacts"
    plain_http: bool = True


class ProxmoxPushRequest(BaseModel):
    file_path: str
    node_host: str
    node_name: str
    filename: str
    proxmox_token: str
    storage: str = "local"
    tls_verify: bool = False
    # How long to wait for the Proxmox import task to finish after the
    # upload completes -- separate from the upload's own timeout, since
    # Proxmox still has to write/verify the file after receiving it.
    poll_timeout: int = 3600
    # Retries the curl upload itself on failure (network blip, momentary
    # Proxmox unavailability) -- deliberately NOT re-pulling from Harbor,
    # since the file is already staged here; only the upload is retried.
    max_retries: int = 3
    retry_delay_seconds: int = 15


class VmPushRequest(BaseModel):
    file_path: str
    vm_host: str
    vm_ssh_user: str
    vm_ssh_pass: str
    dest_path: str
    # Retries the SFTP transfer itself on failure -- deliberately NOT
    # re-pulling from Harbor, since the file is already staged here; only
    # the transfer to the VM is retried.
    max_retries: int = 3
    retry_delay_seconds: int = 15
