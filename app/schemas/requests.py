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
