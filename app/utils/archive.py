import tarfile


def detect_archive_type(path: str) -> str:
    """Tar ke andar actual content dekh kar decide karo docker-archive hai ya oci-archive."""
    try:
        with tarfile.open(path, "r") as tf:
            names = tf.getnames()
        if "index.json" in names and "oci-layout" in names:
            return "oci-archive"
        if "manifest.json" in names:
            return "docker-archive"
    except Exception:
        pass
    return "docker-archive"  # safe fallback
