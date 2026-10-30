"""MinIO reuse/build decisions without compiling Go or touching Docker."""

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_minio", ROOT / "scripts/build_minio.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class BuildMinioTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.context = Path(temporary.name)
        (self.context / "Dockerfile").write_text("FROM scratch\n")
        for context in (patch.object(build, "CONTEXT", self.context),
                        patch.dict(os.environ, ORAL_BUILDER="oral-assessment-web-jenkins")):
            context.__enter__()
            self.addCleanup(context.__exit__, None, None, None)

    def test_matching_image_skips_build_but_still_checks_binary(self):
        digest = build.source_digest(self.context)
        with patch.object(build.subprocess, "run", return_value=subprocess.CompletedProcess(
                [], 0, json.dumps({build.SOURCE_LABEL: digest}))) as run:
            build.main()
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[-1], ["docker", "run", "--rm", "--network", "none", build.IMAGE, "--version"])
        self.assertTrue(run.call_args_list[-1].kwargs["check"])

    def test_missing_unlabelled_or_changed_image_is_built(self):
        for result in (subprocess.CompletedProcess([], 1, ""),
                       subprocess.CompletedProcess([], 0, "null"),
                       subprocess.CompletedProcess([], 0, json.dumps({build.SOURCE_LABEL: "old"}))):
            with self.subTest(result=result), patch.object(build.subprocess, "run", return_value=result) as run:
                build.main()
            commands = [call.args[0] for call in run.call_args_list]
            self.assertEqual(len(commands), 3)
            self.assertEqual(commands[1][:5], ["docker", "buildx", "build", "--builder", "oral-assessment-web-jenkins"])
            self.assertIn(f"{build.SOURCE_LABEL}={build.source_digest(self.context)}", commands[1])
            self.assertIn(build.IMAGE, commands[1])
            self.assertTrue(run.call_args_list[1].kwargs["check"])

    def test_failed_build_or_binary_check_is_not_ignored(self):
        for present in (False, True):
            digest = build.source_digest(self.context)
            probe = subprocess.CompletedProcess([], 0, json.dumps({build.SOURCE_LABEL: digest}) if present else "{}")
            with self.subTest(present=present), patch.object(build.subprocess, "run", side_effect=[
                    probe, subprocess.CalledProcessError(1, "docker")]) as run:
                with self.assertRaises(subprocess.CalledProcessError):
                    build.main()
                self.assertEqual(run.call_count, 2)

    def test_input_content_names_and_added_files_invalidate_reuse(self):
        digests = [build.source_digest(self.context)]
        dockerfile = self.context / "Dockerfile"
        dockerfile.write_text("FROM another-base\n")
        digests.append(build.source_digest(self.context))
        extra = self.context / "config"
        extra.write_text("setting")
        digests.append(build.source_digest(self.context))
        extra.rename(self.context / "renamed")
        digests.append(build.source_digest(self.context))
        self.assertEqual(len(set(digests)), 4)
        self.assertEqual(build.source_digest(self.context), digests[-1])

    def test_image_tag_matches_deployment(self):
        self.assertIn("image: " + build.IMAGE, (ROOT / "docker-compose.yml").read_text())


if __name__ == "__main__":
    unittest.main()
