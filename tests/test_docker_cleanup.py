"""Exercise retention and ownership without touching a Docker daemon."""

import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "docker_cleanup", Path(__file__).resolve().parents[1] / "scripts/docker_cleanup.py"
)
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


def image(key, tags, created="2026-10-10T00:00:00Z", owned=True):
    return {
        "id": key,
        "tags": tags,
        "created": created,
        "labels": {cleanup.LABEL: cleanup.PROJECT} if owned else {},
    }


def container(
    key,
    image_id,
    reference,
    service=None,
    state="running",
    project=None,
    name=None,
    owned=False,
):
    labels = {cleanup.LABEL: cleanup.PROJECT} if owned else {}
    if service:
        labels.update(
            {
                "com.docker.compose.project": project or cleanup.PROJECT,
                "com.docker.compose.service": service,
            }
        )
    return {
        "id": key,
        "image": image_id,
        "reference": reference,
        "name": name or "/" + key,
        "state": state,
        "health": "healthy",
        "labels": labels,
    }


class FakeDocker:
    def __init__(self):
        self.images = []
        for component, repository in cleanup.REPOSITORIES.items():
            self.images += [
                image(component + "-current", [repository + ":build-10"]),
                image(
                    component + "-previous",
                    [repository + ":build-8"],
                    "2026-10-08T00:00:00Z",
                ),
                image(
                    component + "-failed",
                    [repository + ":build-9"],
                    "2026-10-09T00:00:00Z",
                ),
                image(
                    component + "-old",
                    [repository + ":build-7"],
                    "2026-10-07T00:00:00Z",
                    owned=False,
                ),
            ]
        self.images += [
            image("check", [cleanup.CHECK_REPOSITORY + ":build-10"]),
            image("dangling", []),
            image("foreign", ["unrelated-app:release"], owned=False),
        ]
        self.rows = [
            container("api", "api-current", "oral-assessment-api:build-10", "api"),
            container(
                "worker", "api-current", "oral-assessment-api:build-10", "worker"
            ),
            container("web", "web-current", "oral-assessment-web:build-10", "web"),
            container("postgres", "postgres", "pgvector/pgvector:pg16", "postgres"),
            container(
                "old-worker",
                "api-old",
                "oral-assessment-api:build-7",
                "worker",
                state="exited",
            ),
            container(
                "test",
                "api-current",
                "oral-assessment-api:build-10",
                state="exited",
                owned=True,
            ),
            container(
                "legacy-test",
                "api-failed",
                "oral-assessment-api:build-9",
                state="exited",
                name="/build-9-tests",
            ),
            container(
                "foreign",
                "foreign",
                "unrelated-app:release",
                "app",
                state="exited",
                project="other",
            ),
        ]
        self.mutations = []

    def __call__(self, *args):
        if args == ("buildx", "prune", "--help"):
            return "--max-used-space bytes"
        if args[:2] == ("container", "ls"):
            return "\n".join(row["id"] for row in self.rows)
        if args[:2] == ("container", "inspect"):
            return json.dumps(next(row for row in self.rows if row["id"] == args[-1]))
        if args[:2] == ("image", "inspect"):
            return json.dumps(
                next(
                    row
                    for row in self.images
                    if args[-1] == row["id"] or args[-1] in row["tags"]
                )
            )
        if args[:2] == ("image", "ls"):
            if "--filter" in args:
                rows = [
                    r
                    for r in self.images
                    if r["labels"].get(cleanup.LABEL) == cleanup.PROJECT
                ]
            else:
                rows = [
                    r
                    for r in self.images
                    if any(t.startswith(args[-1] + ":") for t in r["tags"])
                ]
            return "\n".join(r["id"] for r in rows)
        if args[:2] == ("container", "rm"):
            row = next(r for r in self.rows if r["id"] == args[-1])
            assert row["state"] in {"exited", "created", "dead"}
            assert "-f" not in args and "--volumes" not in args
            self.rows.remove(row)
        elif args[:2] == ("image", "rm"):
            assert "-f" not in args
            row = next(
                r for r in self.images if args[-1] == r["id"] or args[-1] in r["tags"]
            )
            assert not any(c["image"] == row["id"] for c in self.rows)
            if args[-1] in row["tags"]:
                row["tags"].remove(args[-1])
            if not row["tags"]:
                self.images.remove(row)
        elif args[:2] == ("buildx", "prune"):
            assert args in (
                ("buildx", "prune", "--builder", cleanup.BUILDER, "--filter", "until=168h", "--force"),
                ("buildx", "prune", "--builder", cleanup.BUILDER, "--max-used-space", "10GB", "--force"),
            )
        elif args == ("system", "df"):
            return "disk report"
        else:
            raise AssertionError(f"Unexpected Docker command: {args}")
        self.mutations.append(args)
        return ""


class DockerCleanupTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.engine = FakeDocker()
        for context in [
            patch.object(cleanup, "SNAPSHOT", Path(folder.name) / "previous.json"),
            patch.object(cleanup, "docker", self.engine),
            patch.dict(
                os.environ,
                {
                    "ORAL_TAG": "build-10",
                    "ORAL_API_IMAGE": "oral-assessment-api:build-10",
                    "ORAL_WEB_IMAGE": "oral-assessment-web:build-10",
                },
            ),
            redirect_stdout(io.StringIO()),
        ]:
            context.__enter__()
            self.addCleanup(context.__exit__, None, None, None)
        cleanup.SNAPSHOT.write_text(
            json.dumps(
                {
                    "build": "build-10",
                    "images": {
                        key: {"id": key + "-previous", "reference": repo + ":build-8"}
                        for key, repo in cleanup.REPOSITORIES.items()
                    },
                }
            )
        )

    def test_retains_deployed_pair_removes_failed_and_older_releases(self):
        cleanup.clean()
        self.assertEqual(
            {r["id"] for r in self.engine.images},
            {
                "api-current",
                "api-previous",
                "web-current",
                "web-previous",
                "foreign",
            },
        )
        self.assertEqual(
            {r["id"] for r in self.engine.rows},
            {"api", "worker", "web", "postgres", "foreign"},
        )
        self.assertEqual(
            [args for args in self.engine.mutations if args[:2] == ("buildx", "prune")],
            [("buildx", "prune", "--builder", cleanup.BUILDER, "--filter", "until=168h", "--force"),
             ("buildx", "prune", "--builder", cleanup.BUILDER, "--max-used-space", "10GB", "--force")],
        )

    def test_old_buildx_uses_bounded_storage_flag(self):
        with patch.object(cleanup, "docker", return_value="--keep-storage bytes") as docker:
            cleanup.prune_cache()
        commands = [call.args for call in docker.call_args_list]
        self.assertEqual(commands[-1], (
            "buildx", "prune", "--builder", cleanup.BUILDER, "--keep-storage", "10GB", "--force"))
        self.assertNotIn("--filter", commands[-1])  # Size limit also applies to recent cache.
        self.assertNotIn("--all", str(commands))

    def test_unknown_buildx_never_falls_back_to_unbounded_prune(self):
        with patch.object(cleanup, "docker", return_value="--force") as docker:
            with self.assertRaisesRegex(RuntimeError, "cache left intact"):
                cleanup.prune_cache()
        docker.assert_called_once_with("buildx", "prune", "--help")

    def test_preserves_images_held_by_foreign_stopped_or_restarting_containers(self):
        self.engine.rows += [
            container(
                "other",
                "api-old",
                "oral-assessment-api:build-7",
                "app",
                state="exited",
                project="other",
            ),
            container(
                "restart",
                "web-old",
                "oral-assessment-web:build-7",
                "job",
                state="restarting",
            ),
        ]
        cleanup.clean()
        self.assertTrue({"api-old", "web-old"} <= {r["id"] for r in self.engine.images})
        self.assertTrue({"other", "restart"} <= {r["id"] for r in self.engine.rows})

    def test_unhealthy_or_mismatched_deployment_never_deletes(self):
        for field, value in (
            ("health", "unhealthy"),
            ("image", "web-previous"),
            ("state", "exited"),
        ):
            with self.subTest(field=field):
                web = next(r for r in self.engine.rows if r["id"] == "web")
                old = web[field]
                web[field] = value
                with self.assertRaises(RuntimeError):
                    cleanup.clean()
                self.assertEqual(self.engine.mutations, [])
                web[field] = old

    def test_stale_snapshot_never_deletes(self):
        saved = json.loads(cleanup.SNAPSHOT.read_text())
        saved["build"] = "other-build"
        cleanup.SNAPSHOT.write_text(json.dumps(saved))
        with self.assertRaisesRegex(RuntimeError, "another build"):
            cleanup.clean()
        self.assertEqual(self.engine.mutations, [])

    def test_snapshot_captures_only_running_project_images_and_rejects_mixed_api(self):
        cleanup.snapshot()
        saved = json.loads(cleanup.SNAPSHOT.read_text())
        self.assertEqual(saved["images"]["api"]["id"], "api-current")
        self.assertEqual(saved["images"]["web"]["id"], "web-current")
        next(r for r in self.engine.rows if r["id"] == "worker")["image"] = (
            "api-previous"
        )
        with self.assertRaisesRegex(RuntimeError, "Inconsistent"):
            cleanup.snapshot()

    def test_first_adoption_and_identical_current_image_keep_two_distinct_versions(
        self,
    ):
        images = self.engine.images
        current = {
            key: {"id": key + "-current", "reference": repo + ":build-10"}
            for key, repo in cleanup.REPOSITORIES.items()
        }
        for previous in ({}, current):
            ids, tags = cleanup.retention(images, current, previous)
            self.assertEqual(
                ids, {"api-current", "web-current", "api-failed", "web-failed"}
            )
            self.assertEqual(len(tags), 4)

    def test_foreign_alias_is_not_removed_with_owned_tag(self):
        old = next(r for r in self.engine.images if r["id"] == "api-old")
        old["tags"].append("other-backup:keep")
        cleanup.clean()
        self.assertEqual(old["tags"], ["other-backup:keep"])
        self.assertIn(old, self.engine.images)

    def test_foreign_compose_project_wins_over_legacy_test_name(self):
        row = container(
            "foreign-test",
            "api-old",
            "oral-assessment-api:build-7",
            "test",
            project="other",
            state="exited",
            name="/build-7-tests",
            owned=True,
        )
        self.assertFalse(cleanup.owned_container(row))

    def test_missing_previous_image_falls_back_and_duplicate_tags_count_as_one_image(
        self,
    ):
        current = {
            key: {"id": key + "-current", "reference": repo + ":build-10"}
            for key, repo in cleanup.REPOSITORIES.items()
        }
        previous = {
            key: {"id": "missing", "reference": repo + ":missing"}
            for key, repo in cleanup.REPOSITORIES.items()
        }
        next(r for r in self.engine.images if r["id"] == "api-current")["tags"].append(
            "oral-assessment-api:alias"
        )
        ids, tags = cleanup.retention(self.engine.images, current, previous)
        self.assertEqual(
            ids, {"api-current", "api-failed", "web-current", "web-failed"}
        )
        self.assertEqual(len(tags), 4)

    def test_container_delete_race_aborts_without_force_or_prune(self):
        original = self.engine.__call__

        def raced(*args):
            if args[:2] == ("container", "rm"):
                raise RuntimeError("Container became active")
            return original(*args)

        with patch.object(cleanup, "docker", raced), self.assertRaises(RuntimeError):
            cleanup.clean()
        self.assertEqual(self.engine.mutations, [])


if __name__ == "__main__":
    unittest.main()
