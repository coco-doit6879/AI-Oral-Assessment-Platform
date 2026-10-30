"""Reuse the local MinIO image only when its build inputs match this checkout."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

CONTEXT = Path("services/minio")
IMAGE = "oral-assessment-minio:RELEASE.2025-09-07T16-13-09Z-source"
SOURCE_LABEL = "uk.paperlens.oral.minio-source"


def source_digest(folder):
    digest = hashlib.sha256()
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            raise ValueError("MinIO build context must not contain symlinks")
        if path.is_file():
            content = path.read_bytes()
            # Include names and sizes so renames and file boundaries change the key.
            digest.update(path.relative_to(folder).as_posix().encode() + b"\0")
            digest.update(str(path.stat().st_mode & 0o777).encode() + b"\0")
            digest.update(str(len(content)).encode() + b"\0" + content)
    return digest.hexdigest()


def main():
    builder = os.environ["ORAL_BUILDER"]
    if not (CONTEXT / "Dockerfile").is_file():
        raise ValueError("MinIO Dockerfile is missing")
    digest = source_digest(CONTEXT)
    result = subprocess.run(
        ["docker", "image", "inspect", IMAGE, "--format", "{{json .Config.Labels}}"],
        text=True, capture_output=True,
    )
    labels = (json.loads(result.stdout) or {}) if result.returncode == 0 else {}
    if labels.get(SOURCE_LABEL) == digest:
        print("Reusing MinIO image: build inputs unchanged.", flush=True)
    else:
        print("Building MinIO: image missing or build inputs changed.", flush=True)
        subprocess.run([
            "docker", "buildx", "build", "--builder", builder, "--progress=plain", "--load",
            "--label", f"{SOURCE_LABEL}={digest}", "-t", IMAGE, str(CONTEXT),
        ], check=True)
    # Validate both reused and newly built images before application deployment.
    subprocess.run(["docker", "run", "--rm", "--network", "none", IMAGE, "--version"], check=True)


if __name__ == "__main__":
    main()
