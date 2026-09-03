import subprocess


def check_health():
    skopeo_ok = subprocess.run(["skopeo", "--version"], capture_output=True).returncode == 0
    oras_ok = subprocess.run(["oras", "version"], capture_output=True).returncode == 0
    return {"skopeo": skopeo_ok, "oras": oras_ok}
