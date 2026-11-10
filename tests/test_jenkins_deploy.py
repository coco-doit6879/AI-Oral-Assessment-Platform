import copy
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "Jenkinsfile").read_text(encoding="utf-8")
source = "import datetime\n" + source.split("import datetime\n", 1)[1].split("\nORAL_DEPLOY_PY", 1)[0]
with tempfile.TemporaryDirectory() as directory:
    module_path = Path(directory) / "jenkins_deploy.py"
    module_path.write_text(source.replace("\\'", "'"), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("jenkins_deploy_test", module_path)
    deploy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(deploy)


def configuration(ollama=False, gopt=False):
    environment = {
        "JWT_SECRET": "test-only-" + "x" * 32, "BOOTSTRAP_PASSWORD": "test-password-long",
        "POSTGRES_PASSWORD": "test-database-password", "MINIO_ROOT_PASSWORD": "test-storage-password",
        "PUBLIC_ORIGIN": deploy.ORIGIN, "ALLOWED_ORIGINS": deploy.ORIGIN, "COOKIE_SECURE": "true",
        "AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key", "LLM_MODEL": "existing-cloud-model",
        "ORAL_OLLAMA_ENABLED": str(ollama).lower(), "GOPT_ENABLED": str(gopt).lower(),
        "LOCAL_REVIEW_LLM_MODEL": "qwen2.5:3b", "LOCAL_LLM_URL": "http://old-shared:11434",
    }
    volumes = {name: {} for name in ("postgres_data", "redis_data", "minio_data", "app_data")}
    services = {name: {"environment": copy.deepcopy(environment), "build": "."}
                for name in ("api", "worker", "migrate", "web", "postgres", "redis", "minio")}
    services["postgres"]["environment"].update(POSTGRES_USER="oral", POSTGRES_DB="oral")
    services["web"]["ports"] = [{"host_ip": "127.0.0.1", "published": "13000", "target": 3000}]
    services["minio"]["ports"] = [{"host_ip": "127.0.0.1", "published": "19001", "target": 9001}]
    if ollama:
        volumes["ollama_data"] = {}
        services["ollama"] = {"image": "ollama/ollama:0.40.10", "environment": {},
                              "volumes": [{"type": "volume", "source": "ollama_data", "target": "/root/.ollama"}]}
    if gopt:
        services["gopt"] = {"build": "./services/gopt", "environment": {}, "tmpfs": ["/tmp:size=512m"]}
    return {"services": services, "volumes": volumes}


class DeployTests(unittest.TestCase):
    def test_deploy_commands_report_elapsed_time_without_command_output(self):
        for returncode in (0, 1):
            output = io.StringIO()
            result = subprocess.CompletedProcess([], returncode, "private-stdout", "private-stderr")
            with self.subTest(returncode=returncode), redirect_stdout(output), \
                    patch.object(deploy.time, "monotonic", side_effect=[10, 12.5]), \
                    patch.object(deploy.subprocess, "run", return_value=result):
                if returncode:
                    with self.assertRaises(SystemExit):
                        deploy.command(["docker", "private-argument"], {}, "API health check")
                else:
                    self.assertEqual(deploy.command(["docker", "private-argument"], {}, "API health check"), "private-stdout")
            self.assertIn("API health check finished in 2.5s", output.getvalue())
            self.assertNotIn("private-", output.getvalue())

    @unittest.skipUnless(shutil.which("docker"), "Docker CLI is required for Compose validation")
    def test_real_compose_overlays_and_runtime_preserve_environment(self):
        child = {key: value for key, value in os.environ.items()
                 if key in {"PATH", "SystemRoot", "TEMP", "TMP", "USERPROFILE", "HOME", "DOCKER_CONFIG"}}
        for ollama, gopt in ((False, False), (True, False), (False, True), (True, True)):
            with self.subTest(ollama=ollama, gopt=gopt), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary)
                environment = configuration(ollama, gopt)["services"]["api"]["environment"]
                environment.update(WEB_BIND="127.0.0.1", WEB_PORT="13000", MINIO_CONSOLE_PORT="19001",
                                   POSTGRES_USER="oral", POSTGRES_DB="oral", LOCAL_REVIEW_LLM_MODEL="")
                template = (ROOT / ".env.example").read_text(encoding="utf-8")
                (folder / ".env").write_text(template + "\n" + "\n".join(
                    f"{key}={value}" for key, value in environment.items()) + "\n", encoding="utf-8")
                config = deploy.configure(deploy.compose_configuration(folder, child), "api:test", "web:test")
                if ollama:
                    service = config["services"]["ollama"]
                    self.assertFalse(service.get("ports"))
                    self.assertEqual(service["environment"]["OLLAMA_NUM_PARALLEL"], "1")
                    self.assertEqual(service["environment"]["OLLAMA_NO_CLOUD"], "1")
                    worker = config["services"]["worker"]
                    self.assertEqual(worker["environment"]["LOCAL_REVIEW_LLM_MODEL"], "qwen2.5:3b")
                    self.assertEqual(worker["environment"]["WORKER_SERIAL"], "true")
                    self.assertEqual(worker["environment"]["LOCAL_LLM_CPU_THREADS"], "0")
                    self.assertEqual(config["services"]["api"]["environment"]["LOCAL_LLM_CPU_THREADS"], "0")
                    self.assertEqual(config["volumes"]["ollama_data"]["name"], "oral-assessment-web_ollama_data")
                if ollama or gopt:
                    worker = config["services"]["worker"]
                    self.assertEqual(worker["environment"]["WORKER_SERIAL"], "true")
                    self.assertEqual(worker["environment"]["STT_CPU_THREADS"], "0")
                if gopt:
                    service = config["services"]["gopt"]
                    self.assertEqual(service["command"][-3:], ["--workers", "1", "--no-access-log"])
                self.assert_unbounded(config)
                runtime = folder / "runtime.json"
                runtime.write_text(json.dumps(deploy.escaped_config(config)), encoding="utf-8")
                (folder / "empty.env").touch()
                actual = json.loads(deploy.command([
                    "docker", "compose", "-p", deploy.PROJECT, "--env-file", str(folder / "empty.env"),
                    "-f", str(runtime), "config", "--format", "json"], child, "Runtime parse"))
                for name, service in config["services"].items():
                    self.assertEqual(actual["services"][name].get("environment", {}), service.get("environment", {}))

    @unittest.skipUnless(shutil.which("docker"), "Docker CLI is required for Compose validation")
    def test_legacy_resource_limits_cannot_reenable_caps_or_parallel_grading(self):
        child = {key: value for key, value in os.environ.items()
                 if key in {"PATH", "SystemRoot", "TEMP", "TMP", "USERPROFILE", "HOME", "DOCKER_CONFIG"}}
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            environment = configuration(True, True)["services"]["api"]["environment"]
            environment.update(WEB_BIND="127.0.0.1", WEB_PORT="13000", MINIO_CONSOLE_PORT="19001",
                               ORAL_OLLAMA_CPUS="1.0", WORKER_CPUS="1.0", GOPT_CPUS="1.0",
                               STT_CPU_THREADS="1", LOCAL_LLM_CPU_THREADS="1", GOPT_BLAS_THREADS="1",
                               WORKER_MEMORY="2g", GOPT_MEMORY="2g", ORAL_OLLAMA_MEMORY="4g",
                               WORKER_SERIAL="false", OMP_NUM_THREADS="3", OPENBLAS_NUM_THREADS="3",
                               MKL_NUM_THREADS="3", NUMEXPR_NUM_THREADS="3")
            (folder / ".env").write_text((ROOT / ".env.example").read_text() + "\n" + "\n".join(
                f"{key}={value}" for key, value in environment.items()) + "\n")
            config = deploy.configure(deploy.compose_configuration(folder, child), "api:test", "web:test")
            self.assert_unbounded(config)
            worker = config["services"]["worker"]["environment"]
            self.assertEqual(worker["STT_CPU_THREADS"], "0")
            self.assertEqual(worker["LOCAL_LLM_CPU_THREADS"], "0")
            self.assertEqual(worker["WORKER_SERIAL"], "true")

    def assert_unbounded(self, config):
        for name in ("ollama", "worker", "gopt"):
            if name not in config["services"]:
                continue
            service = config["services"][name]
            for key in ("cpus", "cpu_quota", "cpu_period", "cpuset", "mem_limit", "memswap_limit", "pids_limit"):
                self.assertNotIn(key, service, (name, key))
            self.assertFalse(service.get("deploy", {}).get("resources", {}).get("limits"))
            if name in {"worker", "gopt"} and ("gopt" in config["services"] or "ollama" in config["services"]):
                for field in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
                    command = service["command"]
                    self.assertEqual(command[0], "env")
                    self.assertEqual(command[command.index(field) - 1], "-u")

    def test_optional_services_are_project_scoped_and_do_not_change_exam_provider(self):
        for ollama, gopt in ((False, False), (True, False), (False, True), (True, True)):
            with self.subTest(ollama=ollama, gopt=gopt):
                result = deploy.configure(configuration(ollama, gopt), "api:test", "web:test")
                self.assertEqual(result["name"], "oral-assessment-web")
                for name, service in result["services"].items():
                    self.assertNotIn("build", service)
                    self.assertNotIn("container_name", service)
                    self.assertEqual(set(service["networks"]), {"default", "proxy"} if name == "web" else {"default"})
                for name, volume in result["volumes"].items():
                    self.assertEqual(volume["name"], "oral-assessment-web_" + name)
                environment = result["services"]["api"]["environment"]
                self.assertEqual(environment["AI_PROVIDER"], "gemini")
                self.assertEqual(environment["LLM_MODEL"], "existing-cloud-model")
                if ollama:
                    for name in ("api", "worker", "migrate"):
                        self.assertEqual(result["services"][name]["environment"]["LOCAL_LLM_URL"], "http://ollama:11434")
                if gopt:
                    self.assertEqual(result["services"]["gopt"]["image"], "oral-assessment-gopt:cpu")

    def test_rejects_public_ai_ports_shared_volume_and_unreviewed_services(self):
        for mutation in ("port", "volume", "bind", "extra-service"):
            with self.subTest(mutation=mutation):
                config = configuration(True, True)
                if mutation == "port":
                    config["services"]["ollama"]["ports"] = [{"published": "11434", "target": 11434}]
                elif mutation == "volume":
                    config["volumes"]["sos_models"] = {}
                elif mutation == "bind":
                    config["services"]["ollama"]["volumes"] = [{"type": "bind", "source": "/sos/models"}]
                else:
                    config["services"]["sos-ai-ollama"] = {}
                with self.assertRaises(SystemExit):
                    deploy.configure(config, "api:test", "web:test")

    def test_local_models_preserve_provider_and_reject_invalid_or_cloud_names(self):
        environment = configuration(True)["services"]["api"]["environment"]
        self.assertEqual(deploy.local_models(environment), ["qwen2.5:3b"])
        for invalid in ("", "-unsafe", "model;command", "model:cloud", "model-cloud"):
            with self.subTest(invalid=invalid), self.assertRaises(SystemExit):
                deploy.local_models(environment | {"LOCAL_REVIEW_LLM_MODEL": invalid})
        local = environment | {"AI_PROVIDER": "local", "LLM_MODEL": "qwen2.5:3b", "EMBEDDING_MODEL": "nomic-embed-text"}
        self.assertEqual(deploy.local_models(local), ["qwen2.5:3b", "nomic-embed-text"])

    def test_overlay_selection_comes_from_secret_file_not_jenkins_global_env(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled), tempfile.TemporaryDirectory() as temporary:
                calls = []

                def command(args, child, label, calls=calls, enabled=enabled):
                    calls.append(args)
                    self.assertEqual(child, {})
                    return json.dumps(configuration(enabled, enabled))

                with patch.object(deploy, "command", command), patch.object(deploy.shutil, "copyfile") as copied:
                    deploy.compose_configuration(Path(temporary), {})
                self.assertEqual(len(calls), 2 if enabled else 1)
                self.assertIn("--env-file", calls[0])
                self.assertEqual([call.args[0] for call in copied.call_args_list],
                                 ["docker-compose.yml", "docker-compose.ollama.yml", "docker-compose.gopt.yml"] if enabled else ["docker-compose.yml"])

    def test_only_missing_models_are_installed_in_oral_service(self):
        for present in (False, True):
            with self.subTest(present=present):
                commands = []
                compose = ["docker", "compose", "-p", "oral-assessment-web", "-f", "runtime.json"]
                config = deploy.configure(configuration(True, True), "api:test", "web:test")
                with patch.object(deploy, "command", lambda args, child, label, commands=commands: commands.append(args) or ""), \
                        patch.object(deploy.subprocess, "run", return_value=subprocess.CompletedProcess([], 0 if present else 1)):
                    deploy.prepare_local_ai(compose, {}, config)
                downloads = [args for args in commands if "exec" in args and "pull" in args]
                self.assertEqual(downloads, [] if present else [compose + ["exec", "-T", "ollama", "ollama", "pull", "qwen2.5:3b"]])
                self.assertTrue(any("up" in args and args[-2:] == ["ollama", "gopt"] for args in commands))
                self.assertNotIn("sos-ai-ollama", str(commands))

    def test_failed_ai_preparation_prevents_application_stop(self):
        self.assertLess(source.index("prepare_local_ai(compose, child, config)", source.index("def main()")),
                        source.index("Application stop"))
        config = deploy.configure(configuration(True, True), "api:test", "web:test")
        with patch.object(deploy, "command", side_effect=SystemExit("GOPT image missing")) as command:
            with self.assertRaises(SystemExit):
                deploy.prepare_local_ai(["docker", "compose"], {}, config)
            self.assertEqual(command.call_count, 1)


if __name__ == "__main__":
    unittest.main()
