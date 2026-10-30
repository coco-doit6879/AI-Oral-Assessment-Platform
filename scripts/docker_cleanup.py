"""Retain two OralAI releases and clean only this deployment's Docker resources."""

import argparse
import json
import os
import subprocess
from pathlib import Path

PROJECT = "oral-assessment-web"
LABEL = "uk.paperlens.oral.project"
BUILDER = "oral-assessment-web-jenkins"
REPOSITORIES = {"api": "oral-assessment-api", "web": "oral-assessment-web"}
CHECK_REPOSITORY = "oral-assessment-web-check"
SNAPSHOT = Path(".data/jenkins/previous-images.json")
CACHE_MAX_AGE = "168h"
CACHE_MAX_SIZE = "10GB"
CONTAINER_FORMAT = (
    '{"id":{{json .Id}},"image":{{json .Image}},'
    '"reference":{{json .Config.Image}},"name":{{json .Name}},'
    '"state":{{json .State.Status}},"labels":{{json (index .Config "Labels")}},'
    '"health":{{with index .State "Health"}}{{json .Status}}{{else}}null{{end}}}'
)
IMAGE_FORMAT = (
    '{"id":{{json .Id}},"created":{{json .Created}},'
    '"tags":{{json .RepoTags}},"labels":{{json (index .Config "Labels")}}}'
)


def docker(*args):
    result = subprocess.run(
        ["docker", *args], text=True, capture_output=True, check=False
    )
    if result.returncode:
        # Never print inspect output or arbitrary Docker errors containing credentials.
        raise RuntimeError(f"Docker {args[0]} {args[1]} failed; cleanup stopped.")
    return result.stdout


def containers():
    ids = docker("container", "ls", "-aq", "--no-trunc").split()
    return [
        json.loads(docker("container", "inspect", "--format", CONTAINER_FORMAT, cid))
        for cid in ids
    ]


def image(reference):
    return json.loads(docker("image", "inspect", "--format", IMAGE_FORMAT, reference))


def service(container):
    labels = container.get("labels") or {}
    if labels.get("com.docker.compose.project") == PROJECT:
        return labels.get("com.docker.compose.service")
    return None


def snapshot():
    previous = {}
    rows = containers()
    for component, services in (("api", {"api", "worker"}), ("web", {"web"})):
        active = [c for c in rows if service(c) in services and c["state"] == "running"]
        if len({c["image"] for c in active}) > 1:
            raise RuntimeError(
                f"Inconsistent running {component} images; review deployment before continuing."
            )
        if active:
            previous[component] = {
                "id": active[0]["image"],
                "reference": active[0]["reference"],
            }
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    # Bind the snapshot to this build so an interrupted job cannot reuse old workspace data.
    SNAPSHOT.write_text(
        json.dumps({"build": os.environ["ORAL_TAG"], "images": previous})
    )
    print("Saved image references for the currently running OralAI release.")


def inventory():
    ids = set()
    for repository in (*REPOSITORIES.values(), CHECK_REPOSITORY):
        ids.update(docker("image", "ls", "-q", "--no-trunc", repository).split())
    # Labels identify untagged output from builds made by this pipeline.
    ids.update(
        docker(
            "image", "ls", "-q", "--no-trunc", "--filter", f"label={LABEL}={PROJECT}"
        ).split()
    )
    return [image(key) for key in sorted(ids)]


def owned_container(container):
    labels = container.get("labels") or {}
    compose_project = labels.get("com.docker.compose.project")
    if compose_project:
        return compose_project == PROJECT
    if labels.get(LABEL) == PROJECT:
        return True
    # Existing Jenkins test containers predate ownership labels.
    reference = container["reference"]
    prefix = REPOSITORIES["api"] + ":"
    return (
        reference.startswith(prefix)
        and container["name"].lstrip("/") == reference[len(prefix) :] + "-tests"
    )


def retention(images, current, previous):
    """Keep distinct current/previous image IDs, plus a fallback for first adoption."""
    keep_ids, keep_tags = set(), set()
    for component, repository in REPOSITORIES.items():
        candidates = sorted(
            [
                row
                for row in images
                if any(t.startswith(repository + ":") for t in row.get("tags") or [])
            ],
            key=lambda row: (row["created"], row["id"]),
            reverse=True,
        )
        selected = {current[component]["id"]}
        keep_tags.add(current[component]["reference"])
        old = previous.get(component)
        if (
            old
            and old["id"] != current[component]["id"]
            and any(row["id"] == old["id"] for row in images)
        ):
            selected.add(old["id"])
            keep_tags.add(old["reference"])
        for row in candidates:
            if len(selected) == 2:
                break
            if row["id"] not in selected:
                selected.add(row["id"])
        for row in candidates:
            tags = [t for t in row.get("tags") or [] if t.startswith(repository + ":")]
            if row["id"] in selected and not keep_tags.intersection(tags):
                keep_tags.add(max(tags))
        keep_ids.update(selected)
    return keep_ids, keep_tags


def verify_deployment(rows, current):
    for name, component in (("api", "api"), ("worker", "api"), ("web", "web")):
        active = [
            row for row in rows if service(row) == name and row["state"] == "running"
        ]
        if not active or any(
            row["image"] != current[component]["id"] for row in active
        ):
            raise RuntimeError(
                f"Current {name} container does not match this build; nothing cleaned."
            )
        if name != "worker" and any(row["health"] != "healthy" for row in active):
            raise RuntimeError(f"Current {name} is not healthy; nothing cleaned.")


def prune_cache():
    # Keep warm dependency layers. Age and size are separate passes: an age
    # filter on the size pass would prevent eviction of recent, oversized cache.
    help_text = docker("buildx", "prune", "--help")
    if "--max-used-space" in help_text:
        size_flag = "--max-used-space"
    elif "--keep-storage" in help_text:
        size_flag = "--keep-storage"
    else:
        raise RuntimeError("Buildx lacks bounded cache pruning; cache left intact. Upgrade Buildx.")
    docker("buildx", "prune", "--builder", BUILDER, "--filter", f"until={CACHE_MAX_AGE}", "--force")
    docker("buildx", "prune", "--builder", BUILDER, size_flag, CACHE_MAX_SIZE, "--force")
    print(f"OralAI cache: removed unused records older than {CACHE_MAX_AGE}; size target {CACHE_MAX_SIZE}.")


def clean():
    saved = json.loads(SNAPSHOT.read_text())
    if saved.get("build") != os.environ["ORAL_TAG"]:
        raise RuntimeError(
            "Deployment image snapshot belongs to another build; nothing cleaned."
        )
    current = {}
    for component, repository in REPOSITORIES.items():
        reference = os.environ[f"ORAL_{component.upper()}_IMAGE"]
        if not reference.startswith(repository + ":"):
            raise RuntimeError(
                "Unexpected application image repository; nothing cleaned."
            )
        current[component] = {"id": image(reference)["id"], "reference": reference}
    rows = containers()
    verify_deployment(rows, current)
    images = inventory()
    keep_ids, keep_tags = retention(images, current, saved["images"])
    print("Keeping current and previous OralAI API/web images.")
    for row in rows:
        if row["state"] in {"created", "exited", "dead"} and owned_container(row):
            docker("container", "rm", row["id"])
            print("Removed stopped OralAI container:", row["name"])
    # Re-read after removing stopped containers. Protect every remaining user's images.
    remaining = containers()
    protected_ids = {row["image"] for row in remaining}
    protected_tags = {row["reference"] for row in remaining}
    for row in images:
        tags = row.get("tags") or []
        owned_tags = [
            tag
            for tag in tags
            if tag.split(":", 1)[0] in {*REPOSITORIES.values(), CHECK_REPOSITORY}
        ]
        if row["id"] in protected_ids:
            # Preserve all aliases for images held by another container, even if this exceeds two releases.
            continue
        for tag in owned_tags:
            if tag not in keep_tags and tag not in protected_tags:
                docker("image", "rm", tag)
                print("Removed image tag:", tag)
        if (
            not tags
            and row["id"] not in keep_ids
            and (row.get("labels") or {}).get(LABEL) == PROJECT
        ):
            docker("image", "rm", row["id"])
            print("Removed untagged OralAI image:", row["id"])
    # Cache is isolated in this builder; never prune the shared/default daemon cache.
    prune_cache()
    print("Docker disk usage:")
    print(docker("system", "df"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("snapshot", "clean"))
    args = parser.parse_args()
    try:
        snapshot() if args.action == "snapshot" else clean()
    except (RuntimeError, OSError, ValueError, KeyError) as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
