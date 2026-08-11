"""Small HTTP runner for controlling Braincodec experiments on a PYNQ device.

Run this file on the PYNQ/Braincodec machine. The Windows pyBEHAVIOR GUI can
then send start/stop/status commands over HTTP while the hardware-specific
PYNQ and Microblaze code stays on the device.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import re
import threading
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse


MODE_SIMPLE = "simple_patterns"
MODE_BRAINCODEC = "braincodec_patterns"


class BraincodecRunnerState:
    def __init__(self):
        self.lock = threading.Lock()
        self.overlay = None
        self.experiment = None
        self.thread = None
        self.status = {
            "state": "idle",
            "mode": None,
            "current_trial": 0,
            "total_trials": 0,
            "last_message": "Idle",
            "started_at": None,
            "finished_at": None,
            "log_file": None,
            "error": None,
        }

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return dict(self.status)

    def update(self, **values: Any) -> None:
        with self.lock:
            self.status.update(values)

    def start(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        with self.lock:
            if self.thread is not None and self.thread.is_alive():
                return 409, {"ok": False, "error": "An experiment is already running"}

            payload = dict(payload)
            payload["log_file"] = _build_session_log_file(payload)
            self.status.update(
                {
                    "state": "starting",
                    "mode": payload.get("mode"),
                    "current_trial": 0,
                    "total_trials": 0,
                    "last_message": "Starting experiment",
                    "started_at": datetime.now().isoformat(timespec="seconds"),
                    "finished_at": None,
                    "log_file": payload["log_file"],
                    "error": None,
                }
            )

            self.thread = threading.Thread(
                target=self._run_experiment,
                args=(payload,),
                name="braincodec-experiment",
                daemon=True,
            )
            self.thread.start()

        return 202, {"ok": True, "status": self.snapshot()}

    def stop(self) -> tuple[int, dict[str, Any]]:
        with self.lock:
            experiment = self.experiment
            thread = self.thread
            running = thread is not None and thread.is_alive()

        if experiment is not None:
            stop_errors = self._request_experiment_stop(experiment)
            if stop_errors:
                self.update(
                    state="error",
                    error="; ".join(stop_errors),
                    last_message="Stop failed",
                )
                return 500, {"ok": False, "error": "; ".join(stop_errors)}

        if running and thread is not None:
            thread.join(timeout=2.0)
            running = thread.is_alive()

        if running:
            self.update(state="stopping", last_message="Stop requested; waiting for experiment thread")
        else:
            self.update(
                state="stopped" if experiment is not None else "idle",
                last_message="Experiment stopped" if experiment is not None else "No experiment running",
                finished_at=datetime.now().isoformat(timespec="seconds") if experiment is not None else None,
            )
        return 202, {"ok": True, "status": self.snapshot()}

    def _request_experiment_stop(self, experiment) -> list[str]:
        errors = []
        try:
            experiment._stop_requested = True
        except Exception as exc:
            errors.append(f"Could not set _stop_requested: {exc}")

        on_stop_clicked = getattr(experiment, "on_stop_clicked", None)
        if callable(on_stop_clicked):
            try:
                on_stop_clicked(None)
            except Exception as exc:
                errors.append(f"on_stop_clicked failed: {exc}")

        stop_method = getattr(experiment, "stop_", None)
        if callable(stop_method):
            try:
                stop_method()
            except Exception as exc:
                errors.append(f"stop_ failed: {exc}")
        return errors

    def upload(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        files = payload.get("files", [])
        if not isinstance(files, list) or not files:
            return 400, {"ok": False, "error": "Upload payload must contain a non-empty files list"}

        saved = []
        for file_info in files:
            try:
                saved.append(_save_uploaded_file(file_info))
            except Exception as exc:
                return 400, {"ok": False, "error": str(exc), "saved": saved}

        self.update(last_message=f"Uploaded {len(saved)} file(s)")
        return 200, {"ok": True, "saved": saved, "status": self.snapshot()}

    def _run_experiment(self, payload: dict[str, Any]) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            self.update(state="loading", last_message="Loading hardware and driver")
            total_trials = _count_trials_if_available(payload.get("trials_file", ""))
            if total_trials:
                self.update(total_trials=total_trials)
            overlay = self._get_overlay()
            exp = self._create_experiment(overlay, payload)

            with self.lock:
                self.experiment = exp

            self._attach_status_hooks(exp)
            self.update(state="running", last_message="Running experiment")
            loop.run_until_complete(exp.run())

            final_state = "stopped" if self.snapshot()["state"] in {"stopping", "stopped"} else "finished"
            self.update(
                state=final_state,
                last_message="Experiment stopped" if final_state == "stopped" else "Experiment finished",
                finished_at=datetime.now().isoformat(timespec="seconds"),
            )
        except Exception as exc:
            self.update(
                state="error",
                error=f"{type(exc).__name__}: {exc}",
                last_message="Experiment failed",
                finished_at=datetime.now().isoformat(timespec="seconds"),
                traceback=traceback.format_exc(),
            )
        finally:
            with self.lock:
                self.experiment = None
            asyncio.set_event_loop(None)
            loop.close()

    def _get_overlay(self):
        if self.overlay is None:
            from pynq import Overlay

            self.overlay = Overlay("base.bit")
        return self.overlay

    def _create_experiment(self, overlay, payload: dict[str, Any]):
        ExpSimplePatterns, ExpBraincodecPatterns = _import_driver_classes()
        _patch_driver_log_file((ExpSimplePatterns, ExpBraincodecPatterns), payload.get("log_file"))
        mode = payload.get("mode", MODE_SIMPLE)
        config_file = _required(payload, "config_file")
        trials_file = _required(payload, "trials_file")
        wait_for_trigger = bool(payload.get("wait_for_trigger", True))
        ext_cables_used = bool(payload.get("ext_cables_used", True))

        if mode == MODE_SIMPLE:
            return ExpSimplePatterns(
                overlay,
                config_file,
                trials_file,
                wait_for_trigger=wait_for_trigger,
                ext_cables_used=ext_cables_used,
            )
        if mode == MODE_BRAINCODEC:
            return ExpBraincodecPatterns(
                overlay,
                config_file,
                trials_file,
                wait_for_trigger=wait_for_trigger,
                ext_cables_used=ext_cables_used,
            )
        raise ValueError(f"Unknown experiment mode: {mode}")

    def _attach_status_hooks(self, exp) -> None:
        panel = getattr(exp, "control_panel", None)
        if panel is None:
            return

        original_set_status = getattr(panel, "set_status", None)
        original_set_info = getattr(panel, "set_info", None)
        original_set_progress = getattr(panel, "set_progress", None)

        def set_status(text):
            self.update(last_message=str(text))
            if callable(original_set_status):
                original_set_status(text)

        def set_info(text):
            self.update(last_message=str(text))
            if callable(original_set_info):
                original_set_info(text)

        def set_progress(value):
            self.update(current_trial=int(value))
            if callable(original_set_progress):
                original_set_progress(value)

        panel.set_status = set_status
        panel.set_info = set_info
        panel.set_progress = set_progress


class BraincodecRequestHandler(BaseHTTPRequestHandler):
    runner_state: BraincodecRunnerState = None

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/status":
            self._send_json(200, {"ok": True, "status": self.runner_state.snapshot()})
            return
        if path == "/download":
            query = parse_qs(parsed.query)
            requested_path = query.get("path", [""])[0]
            self._send_download(requested_path)
            return
        self._send_json(404, {"ok": False, "error": "Unknown endpoint"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/start":
            payload = self._read_json()
            status, body = self.runner_state.start(payload)
            self._send_json(status, body)
            return
        if path == "/stop":
            status, body = self.runner_state.stop()
            self._send_json(status, body)
            return
        if path == "/upload":
            payload = self._read_json()
            status, body = self.runner_state.upload(payload)
            self._send_json(status, body)
            return
        self._send_json(404, {"ok": False, "error": "Unknown endpoint"})

    def log_message(self, format: str, *args: Any) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {self.address_string()} {format % args}")

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length == 0:
            return {}
        data = self.rfile.read(content_length).decode("utf-8")
        return json.loads(data)

    def _send_json(self, status: int, body: dict[str, Any]) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_download(self, requested_path: str) -> None:
        try:
            path = _safe_download_path(requested_path)
            with open(path, "rb") as handle:
                data = handle.read()
        except Exception as exc:
            self._send_json(404, {"ok": False, "error": str(exc)})
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{os.path.basename(path)}"')
        self.end_headers()
        self.wfile.write(data)


def _import_driver_classes():
    try:
        from led_driver.driver import ExpBraincodecPatterns, ExpSimplePatterns
    except ImportError:
        try:
            from driver import ExpBraincodecPatterns, ExpSimplePatterns
        except ImportError:
            from .driver import ExpBraincodecPatterns, ExpSimplePatterns
    return ExpSimplePatterns, ExpBraincodecPatterns


def _required(payload: dict[str, Any], key: str) -> Any:
    value = payload.get(key)
    if value in (None, ""):
        raise ValueError(f"Missing required field: {key}")
    return value


def _count_trials_if_available(trials_file: str) -> int:
    if not trials_file or not os.path.exists(trials_file):
        return 0
    count = 0
    with open(trials_file, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            count += len(line.replace(",", " ").split())
    return count


def _build_session_log_file(payload: dict[str, Any]) -> str:
    metadata = payload.get("session_metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    mouse = _mouse_filename_component(str(metadata.get("mouse", "mouse")))
    project = _safe_component(str(metadata.get("project", "project")))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("logs", exist_ok=True)
    return os.path.join("logs", f"{mouse}_{project}_{timestamp}.csv")


def _patch_driver_log_file(classes, log_file: str | None) -> None:
    if not log_file:
        return
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)

    def create_named_log_file(folder="logs"):
        del folder
        return log_file

    for cls in classes:
        run_method = getattr(cls, "run", None)
        globals_dict = getattr(run_method, "__globals__", None)
        if isinstance(globals_dict, dict) and "create_log_file" in globals_dict:
            globals_dict["create_log_file"] = create_named_log_file


def _mouse_filename_component(value: str) -> str:
    cleaned = _safe_component(value)
    if cleaned and cleaned[:1].lower() != "m":
        return f"M{cleaned}"
    return cleaned or "mouse"


def _safe_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value).strip())
    cleaned = cleaned.strip("._-")
    return cleaned or "unknown"


def _save_uploaded_file(file_info: dict[str, Any]) -> dict[str, str]:
    if not isinstance(file_info, dict):
        raise ValueError("Each uploaded file must be an object")

    file_type = file_info.get("type")
    name = _safe_filename(str(file_info.get("name", "")))
    content_b64 = file_info.get("content_b64")
    if not name:
        raise ValueError("Uploaded file is missing a name")
    if not isinstance(content_b64, str):
        raise ValueError(f"Uploaded file {name} is missing content_b64")

    if file_type == "config":
        folder = "Configurations"
    elif file_type == "trials":
        folder = "trials_files"
    elif file_type == "patterns":
        folder = "Patterns"
    else:
        raise ValueError(f"Unknown upload file type: {file_type}")

    os.makedirs(folder, exist_ok=True)
    destination = os.path.abspath(os.path.join(folder, name))
    folder_abs = os.path.abspath(folder)
    if not destination.startswith(folder_abs):
        raise ValueError(f"Unsafe upload destination: {name}")

    with open(destination, "wb") as handle:
        handle.write(base64.b64decode(content_b64.encode("ascii")))

    return {"type": str(file_type), "name": name, "path": os.path.relpath(destination)}


def _safe_filename(name: str) -> str:
    basename = os.path.basename(name.replace("\\", "/"))
    if basename in ("", ".", ".."):
        raise ValueError(f"Unsafe file name: {name}")
    return basename


def _safe_download_path(path_text: str) -> str:
    normalized = str(path_text or "").replace("\\", "/").strip()
    if not normalized:
        raise ValueError("Download path is required")
    logs_root = os.path.abspath("logs")
    candidate = os.path.abspath(normalized)
    if not candidate.startswith(logs_root + os.sep):
        raise ValueError(f"Unsafe download path: {path_text}")
    if not os.path.isfile(candidate):
        raise FileNotFoundError(path_text)
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Braincodec PYNQ HTTP server.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument(
        "--workdir",
        default=None,
        help="Working directory containing Configurations/, trials, calibration files, and driver assets.",
    )
    args = parser.parse_args()

    if args.workdir:
        os.chdir(args.workdir)

    state = BraincodecRunnerState()
    BraincodecRequestHandler.runner_state = state
    server = ThreadingHTTPServer((args.host, args.port), BraincodecRequestHandler)
    print(f"Braincodec runner listening on http://{args.host}:{args.port}")
    print(f"Working directory: {os.getcwd()}")
    server.serve_forever()


if __name__ == "__main__":
    main()
