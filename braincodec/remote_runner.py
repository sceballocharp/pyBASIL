"""Small HTTP runner for controlling Braincodec experiments on a PYNQ device.

Run this file on the PYNQ/Braincodec machine. The Windows pyBEHAVIOR GUI can
then send start/stop/status commands over HTTP while the hardware-specific
PYNQ and Microblaze code stays on the device.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import threading
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse


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

            self.status.update(
                {
                    "state": "starting",
                    "mode": payload.get("mode"),
                    "current_trial": 0,
                    "total_trials": 0,
                    "last_message": "Starting experiment",
                    "started_at": datetime.now().isoformat(timespec="seconds"),
                    "finished_at": None,
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
            running = self.thread is not None and self.thread.is_alive()

        if experiment is not None:
            try:
                experiment.stop_()
            except Exception as exc:
                self.update(state="error", error=str(exc), last_message="Stop failed")
                return 500, {"ok": False, "error": str(exc)}

        self.update(state="stopping" if running else "idle", last_message="Stop requested")
        return 202, {"ok": True, "status": self.snapshot()}

    def _run_experiment(self, payload: dict[str, Any]) -> None:
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
            asyncio.run(exp.run())

            final_state = "stopped" if self.snapshot()["state"] == "stopping" else "finished"
            self.update(
                state=final_state,
                last_message="Experiment finished",
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

    def _get_overlay(self):
        if self.overlay is None:
            from pynq import Overlay

            self.overlay = Overlay("base.bit")
        return self.overlay

    def _create_experiment(self, overlay, payload: dict[str, Any]):
        ExpSimplePatterns, ExpBraincodecPatterns = _import_driver_classes()
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
        path = urlparse(self.path).path
        if path == "/status":
            self._send_json(200, {"ok": True, "status": self.runner_state.snapshot()})
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
