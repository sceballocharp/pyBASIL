"""Tkinter Braincodec panel for terminal use and pyBEHAVIOR integration."""

from __future__ import annotations

import base64
from collections import deque
from datetime import datetime
import json
from pathlib import Path
import random
import threading
from tkinter import filedialog, ttk
from typing import Callable, Optional
import tkinter as tk
from urllib import error as urllib_error
from urllib import request as urllib_request

try:
    import yaml
except ImportError:
    yaml = None

Callback = Callable[[], None]

MODE_SIMPLE = "simple_patterns"
MODE_BRAINCODEC = "braincodec_patterns"

MODE_LABELS = {
    MODE_SIMPLE: "Simple patterns",
    MODE_BRAINCODEC: "Braincodec patterns",
}

SIMPLE_PATTERN_KEYS = {
    "mouse_id",
    "device_id",
    "GO",
    "GO irradiance (mW/mm2)",
    "NOGO",
    "NOGO irradiance (mW/mm2)",
    "Pulse duration (ms)",
    "Pulse frequency (Hz)",
    "Number of pulses",
}

BRAINCODEC_PATTERN_KEYS = {
    "mouse_id",
    "device_id",
    "patterns_file",
    "patterns_max",
    "catch_trials",
}


class BraincodecTkPanel(ttk.Frame):
    """Reusable Tkinter frame for controlling Braincodec experiments.

    The panel is hardware-agnostic. Wire `on_start` and `on_stop` to the real
    experiment runner now, or embed this frame in the larger pyBEHAVIOR GUI
    later without changing the control surface.
    """

    def __init__(
        self,
        master,
        *,
        on_start: Optional[Callback] = None,
        on_stop: Optional[Callback] = None,
        log_lines: int = 80,
        padding: int = 10,
    ):
        super().__init__(master, padding=padding)
        self.on_start = on_start
        self.on_stop = on_stop
        self.log_lines = log_lines
        self._log_buffer = deque(maxlen=log_lines)

        self.config_file_var = tk.StringVar()
        self.trials_file_var = tk.StringVar()
        self.patterns_file_var = tk.StringVar()
        self.remote_url_var = tk.StringVar(value="http://192.168.2.99:8000")
        self.mode_var = tk.StringVar(value=MODE_SIMPLE)
        self.wait_for_trigger_var = tk.BooleanVar(value=True)
        self.ext_cables_used_var = tk.BooleanVar(value=True)
        self.generated_trial_count_var = tk.StringVar(value="800")
        self.generated_go_percent_var = tk.StringVar(value="50")
        self.generated_blank_percent_var = tk.StringVar(value="0")
        self.generated_catch_percent_var = tk.StringVar(value="0")
        self.generated_seed_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Idle")
        self.info_var = tk.StringVar(value="Waiting")
        self.progress_var = tk.IntVar(value=0)
        self.progress_max = 100
        self.indicator_color = "gray"
        self.go_pattern_canvas = None
        self.nogo_pattern_canvas = None
        self._simulation_after_id = None
        self._simulation_trials = []
        self._simulation_index = 0

        self._build_widgets()

    def _build_widgets(self) -> None:
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.rowconfigure(0, weight=1)

        left_pane = ttk.Frame(self)
        left_pane.grid(row=0, column=0, sticky="nsew")
        left_pane.columnconfigure(0, weight=1)
        left_pane.rowconfigure(4, weight=1)

        controls = ttk.LabelFrame(left_pane, text="Braincodec Control")
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(6, weight=1)

        self.start_button = ttk.Button(controls, text="Start", command=self._handle_start)
        self.start_button.grid(row=0, column=0, padx=4, pady=6, sticky="ew")

        self.stop_button = ttk.Button(controls, text="Stop", command=self._handle_stop)
        self.stop_button.grid(row=0, column=1, padx=4, pady=6, sticky="ew")

        ttk.Button(controls, text="Simulate", command=self.simulate_session).grid(
            row=0, column=2, padx=4, pady=6, sticky="ew"
        )

        ttk.Button(controls, text="Clear Log", command=self.clear_log).grid(
            row=0, column=3, padx=4, pady=6, sticky="ew"
        )

        ttk.Label(controls, text="Status").grid(row=0, column=4, padx=(16, 4), pady=6)
        ttk.Label(controls, textvariable=self.status_var, width=24).grid(
            row=0, column=5, padx=4, pady=6, sticky="w"
        )

        self.indicator = tk.Canvas(controls, width=38, height=38, highlightthickness=0)
        self.indicator.grid(row=0, column=6, padx=8, pady=6, sticky="w")
        self._indicator_item = self.indicator.create_oval(
            5, 5, 33, 33, fill=self.indicator_color, outline="black", width=2
        )

        ttk.Label(controls, text="PYNQ runner").grid(row=1, column=0, padx=4, pady=(0, 6), sticky="w")
        ttk.Entry(controls, textvariable=self.remote_url_var, width=26).grid(
            row=1, column=1, columnspan=2, padx=4, pady=(0, 6), sticky="ew"
        )
        ttk.Button(controls, text="Remote Start", command=self.start_remote_experiment).grid(
            row=1, column=3, padx=4, pady=(0, 6), sticky="ew"
        )
        ttk.Button(controls, text="Remote Stop", command=self.stop_remote_experiment).grid(
            row=1, column=4, padx=4, pady=(0, 6), sticky="ew"
        )
        ttk.Button(controls, text="Remote Status", command=self.check_remote_status).grid(
            row=1, column=5, padx=4, pady=(0, 6), sticky="ew"
        )
        ttk.Button(controls, text="Upload Files", command=self.upload_remote_files).grid(
            row=1, column=6, padx=4, pady=(0, 6), sticky="ew"
        )

        mode = ttk.LabelFrame(left_pane, text="Experiment Type")
        mode.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        mode.columnconfigure(3, weight=1)
        ttk.Radiobutton(
            mode,
            text=MODE_LABELS[MODE_SIMPLE],
            value=MODE_SIMPLE,
            variable=self.mode_var,
            command=self._on_mode_changed,
        ).grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Radiobutton(
            mode,
            text=MODE_LABELS[MODE_BRAINCODEC],
            value=MODE_BRAINCODEC,
            variable=self.mode_var,
            command=self._on_mode_changed,
        ).grid(row=0, column=1, padx=6, pady=6, sticky="w")
        ttk.Button(mode, text="Detect From Config", command=self.detect_mode_from_config).grid(
            row=0, column=2, padx=6, pady=6, sticky="ew"
        )
        ttk.Button(mode, text="Validate Config", command=self.validate_config).grid(
            row=0, column=3, padx=6, pady=6, sticky="w"
        )
        ttk.Checkbutton(
            mode,
            text="Wait for trigger",
            variable=self.wait_for_trigger_var,
        ).grid(row=1, column=0, padx=6, pady=(0, 6), sticky="w")
        ttk.Checkbutton(
            mode,
            text="Extension cables used",
            variable=self.ext_cables_used_var,
        ).grid(row=1, column=1, padx=6, pady=(0, 6), sticky="w")

        files = ttk.LabelFrame(left_pane, text="Files")
        files.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        files.columnconfigure(1, weight=1)

        self._file_row(files, 0, "Config", self.config_file_var, self._browse_config)
        self._file_row(files, 1, "Trials", self.trials_file_var, self._browse_trials)
        self.patterns_row = self._file_row(
            files, 2, "Patterns", self.patterns_file_var, self._browse_patterns
        )

        generator = ttk.LabelFrame(left_pane, text="Generate Trials .dat")
        generator.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        generator.columnconfigure(9, weight=1)
        ttk.Label(generator, text="Trials").grid(row=0, column=0, padx=(6, 4), pady=6, sticky="w")
        ttk.Entry(generator, textvariable=self.generated_trial_count_var, width=7).grid(
            row=0, column=1, padx=(0, 8), pady=6, sticky="w"
        )
        ttk.Label(generator, text="GO %").grid(row=0, column=2, padx=(6, 4), pady=6, sticky="w")
        ttk.Entry(generator, textvariable=self.generated_go_percent_var, width=6).grid(
            row=0, column=3, padx=(0, 8), pady=6, sticky="w"
        )
        self.generated_secondary_label = ttk.Label(generator, text="Blank %")
        self.generated_secondary_label.grid(row=0, column=4, padx=(6, 4), pady=6, sticky="w")
        self.generated_secondary_entry = ttk.Entry(
            generator, textvariable=self.generated_blank_percent_var, width=6
        )
        self.generated_secondary_entry.grid(
            row=0, column=5, padx=(0, 8), pady=6, sticky="w"
        )
        ttk.Label(generator, text="Seed").grid(row=0, column=6, padx=(6, 4), pady=6, sticky="w")
        ttk.Entry(generator, textvariable=self.generated_seed_var, width=8).grid(
            row=0, column=7, padx=(0, 8), pady=6, sticky="w"
        )
        ttk.Button(generator, text="Generate .dat", command=self.generate_trials_file).grid(
            row=0, column=8, padx=4, pady=6, sticky="ew"
        )
        ttk.Button(generator, text="Generate + Upload", command=self.generate_and_upload_trials).grid(
            row=0, column=9, padx=(4, 6), pady=6, sticky="ew"
        )

        preview = ttk.LabelFrame(self, text="Pattern Preview")
        preview.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        preview.columnconfigure(0, weight=1)
        self._build_pattern_preview(preview)

        runtime = ttk.LabelFrame(left_pane, text="Run")
        runtime.grid(row=4, column=0, sticky="nsew", pady=(8, 0))
        runtime.columnconfigure(0, weight=1)
        runtime.rowconfigure(3, weight=1)

        self.progress = ttk.Progressbar(
            runtime,
            variable=self.progress_var,
            maximum=self.progress_max,
            mode="determinate",
        )
        self.progress.grid(row=0, column=0, sticky="ew", padx=6, pady=(8, 4))

        ttk.Label(runtime, textvariable=self.info_var).grid(
            row=1, column=0, sticky="w", padx=6, pady=(0, 6)
        )

        self.log_text = tk.Text(runtime, height=12, wrap=tk.WORD)
        self.log_text.grid(row=3, column=0, sticky="nsew", padx=(6, 0), pady=(0, 6))
        self.log_text.configure(state="disabled")

        scrollbar = ttk.Scrollbar(runtime, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=3, column=1, sticky="ns", padx=(0, 6), pady=(0, 6))
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self._on_mode_changed()

    def _build_pattern_preview(self, parent) -> None:
        parent.columnconfigure(0, weight=1)

        go_frame = ttk.Frame(parent)
        go_frame.grid(row=0, column=0, sticky="n", padx=6, pady=(6, 3))
        nogo_frame = ttk.Frame(parent)
        nogo_frame.grid(row=1, column=0, sticky="n", padx=6, pady=(3, 6))

        ttk.Label(go_frame, text="GO").pack(anchor="center")
        self.go_pattern_canvas = tk.Canvas(go_frame, width=280, height=280, background="white")
        self.go_pattern_canvas.pack(fill=tk.BOTH, expand=True)

        ttk.Label(nogo_frame, text="NO-GO").pack(anchor="center")
        self.nogo_pattern_canvas = tk.Canvas(nogo_frame, width=280, height=280, background="white")
        self.nogo_pattern_canvas.pack(fill=tk.BOTH, expand=True)

        self._draw_empty_pattern_preview("Select a simple-pattern config")

    def _file_row(self, parent, row: int, label: str, variable: tk.StringVar, command: Callback):
        label_widget = ttk.Label(parent, text=label, width=10)
        entry = ttk.Entry(parent, textvariable=variable)
        button = ttk.Button(parent, text="Browse", command=command)
        label_widget.grid(row=row, column=0, sticky="w", padx=6, pady=4)
        entry.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        button.grid(row=row, column=2, padx=6, pady=4)
        return label_widget, entry, button

    def _browse_config(self) -> None:
        self._browse_file(self.config_file_var, [("YAML files", "*.yaml *.yml"), ("All files", "*.*")])

    def _browse_trials(self) -> None:
        self._browse_file(self.trials_file_var, [("Trial files", "*.txt *.dat *.csv"), ("All files", "*.*")])

    def _browse_patterns(self) -> None:
        self._browse_file(self.patterns_file_var, [("NumPy pattern files", "*.npy"), ("All files", "*.*")])

    def _browse_file(self, variable: tk.StringVar, filetypes) -> None:
        initialdir = self._initial_dir(variable.get())
        selected = filedialog.askopenfilename(parent=self, initialdir=initialdir, filetypes=filetypes)
        if selected:
            variable.set(selected)
            if variable is self.config_file_var:
                self.detect_mode_from_config()

    @staticmethod
    def _initial_dir(current_value: str) -> str:
        path = Path(current_value)
        if current_value and path.parent.exists():
            return str(path.parent)
        return str(Path.cwd())

    def set_start_callback(self, callback: Optional[Callback]) -> None:
        self.on_start = callback

    def set_stop_callback(self, callback: Optional[Callback]) -> None:
        self.on_stop = callback

    def set_indicator(self, color: str) -> None:
        self.indicator_color = color
        self.indicator.itemconfigure(self._indicator_item, fill=color)

    def set_progress(self, value: int, maximum: Optional[int] = None) -> None:
        if maximum is not None:
            self.progress_max = maximum
            self.progress.configure(maximum=maximum)
        self.progress_var.set(value)

    def set_status(self, text: str) -> None:
        self.status_var.set(text)

    def set_info(self, text: str) -> None:
        self.info_var.set(text)

    def get_mode(self) -> str:
        return self.mode_var.get()

    def set_mode(self, mode: str) -> None:
        if mode not in MODE_LABELS:
            raise ValueError(f"Unknown Braincodec mode: {mode}")
        self.mode_var.set(mode)
        self._on_mode_changed()

    def add_log_line(self, text: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log_buffer.append(f"[{timestamp}] {text}")
        self._refresh_log()

    def clear_log(self) -> None:
        self._log_buffer.clear()
        self._refresh_log()

    def get_selected_files(self) -> dict[str, str]:
        return {
            "mode": self.mode_var.get(),
            "config_file": self.config_file_var.get(),
            "trials_file": self.trials_file_var.get(),
            "patterns_file": self.patterns_file_var.get(),
            "wait_for_trigger": self.wait_for_trigger_var.get(),
            "ext_cables_used": self.ext_cables_used_var.get(),
        }

    def start_remote_experiment(self) -> None:
        if not self.validate_config():
            return
        payload = self._build_remote_payload()
        if payload is None:
            return
        self.set_status("Remote starting")
        self.add_log_line("Sending remote start command")
        self._run_remote_request("POST", "/start", payload)

    def stop_remote_experiment(self) -> None:
        self.set_status("Remote stopping")
        self.add_log_line("Sending remote stop command")
        self._run_remote_request("POST", "/stop", {})

    def check_remote_status(self) -> None:
        self.add_log_line("Checking remote status")
        self._run_remote_request("GET", "/status", None)

    def upload_remote_files(self) -> None:
        payload = self._build_upload_payload()
        if payload is None:
            return
        self.set_status("Uploading")
        self.add_log_line(f"Uploading {len(payload['files'])} file(s) to PYNQ")
        self._run_remote_request("POST", "/upload", payload)

    def generate_and_upload_trials(self) -> None:
        if self.generate_trials_file():
            self.upload_remote_files()

    def generate_trials_file(self) -> bool:
        try:
            trial_count = int(self.generated_trial_count_var.get().strip())
            go_percent = float(self.generated_go_percent_var.get().strip())
            secondary_percent = float(self._generated_secondary_percent_var().get().strip())
        except ValueError:
            self.add_log_line("Trial generator values must be numeric")
            self.set_status("Bad generator values")
            return False

        if trial_count <= 0:
            self.add_log_line("Trial count must be greater than zero")
            self.set_status("Bad trial count")
            return False
        if go_percent < 0 or secondary_percent < 0 or go_percent + secondary_percent > 100:
            self.add_log_line("Generated trial percentages must be >= 0 and total <= 100")
            self.set_status("Bad percentages")
            return False

        seed_text = self.generated_seed_var.get().strip()
        rng = random.Random(seed_text if seed_text else None)
        mode = self.mode_var.get()
        codes = self._generate_trial_codes(trial_count, go_percent, secondary_percent, rng, mode)
        if not codes:
            return False

        initial_dir = self._initial_dir(self.trials_file_var.get())
        path_text = filedialog.asksaveasfilename(
            title="Save generated Braincodec trials",
            initialdir=initial_dir,
            initialfile="generated_braincodec_trials.dat",
            defaultextension=".dat",
            filetypes=[("Braincodec trial files", "*.dat"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path_text:
            self.add_log_line("Trial generation cancelled")
            return False

        path = Path(path_text)
        try:
            path.write_text("\n".join(str(code) for code in codes) + "\n", encoding="utf-8")
        except OSError as exc:
            self.add_log_line(f"Could not save generated trials: {exc}")
            self.set_status("Trial save failed")
            return False

        self.trials_file_var.set(str(path))
        self.set_progress(0, maximum=len(codes))
        self.set_status("Trials generated")
        self.add_log_line(self._generated_trials_summary(codes, mode, path))
        return True

    def _generated_secondary_percent_var(self) -> tk.StringVar:
        if self.mode_var.get() == MODE_BRAINCODEC:
            return self.generated_catch_percent_var
        return self.generated_blank_percent_var

    def _generate_trial_codes(
        self,
        trial_count: int,
        go_percent: float,
        secondary_percent: float,
        rng: random.Random,
        mode: str,
    ) -> list[int]:
        go_cutoff = go_percent / 100.0
        secondary_cutoff = (go_percent + secondary_percent) / 100.0
        codes = []
        for _ in range(trial_count):
            draw = rng.random()
            if draw < go_cutoff:
                codes.append(1)
            elif draw < secondary_cutoff:
                if mode == MODE_BRAINCODEC:
                    codes.append(rng.randint(2, 15))
                else:
                    codes.append(0)
            else:
                codes.append(16 if mode == MODE_BRAINCODEC else 2)
        return codes

    def _generated_trials_summary(self, codes: list[int], mode: str, path: Path) -> str:
        go_count = sum(1 for code in codes if code == 1)
        if mode == MODE_BRAINCODEC:
            catch_count = sum(1 for code in codes if 2 <= code <= 15)
            nogo_count = len(codes) - go_count - catch_count
            return (
                f"Generated {len(codes)} trials at {path.name}: "
                f"GO={go_count}, CATCH={catch_count}, NO-GO={nogo_count} "
                "(Braincodec codes: 1=GO, 2-15=CATCH, 16=NO-GO)"
            )
        blank_count = sum(1 for code in codes if code == 0)
        nogo_count = sum(1 for code in codes if code == 2)
        return (
            f"Generated {len(codes)} trials at {path.name}: "
            f"GO={go_count}, NO-GO={nogo_count}, BLANK={blank_count} "
            "(Simple codes: 1=GO, 2=NO-GO, 0=BLANK)"
        )

    def _build_upload_payload(self) -> Optional[dict]:
        files = []
        config_file = self.config_file_var.get().strip()
        trials_file = self.trials_file_var.get().strip()

        if not config_file:
            self.add_log_line("Select a config file before upload")
            self.set_status("No config")
            return None
        if not trials_file:
            self.add_log_line("Select a trials file before upload")
            self.set_status("No trials")
            return None

        files.append(self._upload_file_entry("config", config_file))
        files.append(self._upload_file_entry("trials", trials_file))

        if self.mode_var.get() == MODE_BRAINCODEC and self.patterns_file_var.get().strip():
            files.append(self._upload_file_entry("patterns", self.patterns_file_var.get()))

        if any(file_entry is None for file_entry in files):
            return None
        return {"files": files}

    def _upload_file_entry(self, file_type: str, path_text: str) -> Optional[dict]:
        path = Path(path_text.strip())
        if not path.exists():
            self.add_log_line(f"Cannot upload missing file: {path_text}")
            self.set_status("Upload file missing")
            return None
        return {
            "type": file_type,
            "name": path.name,
            "content_b64": base64.b64encode(path.read_bytes()).decode("ascii"),
        }

    def _build_remote_payload(self) -> Optional[dict]:
        config_file = self._remote_file_value(self.config_file_var.get())
        trials_file = self._remote_file_value(self.trials_file_var.get())
        if not config_file:
            self.add_log_line("Select a config file before remote start")
            self.set_status("No config")
            return None
        if not trials_file:
            self.add_log_line("Select a trials file before remote start")
            self.set_status("No trials")
            return None

        payload = {
            "mode": self.mode_var.get(),
            "config_file": config_file,
            "trials_file": trials_file,
            "wait_for_trigger": self.wait_for_trigger_var.get(),
            "ext_cables_used": self.ext_cables_used_var.get(),
        }
        if self.mode_var.get() == MODE_BRAINCODEC and self.patterns_file_var.get().strip():
            payload["patterns_file"] = self._remote_file_value(self.patterns_file_var.get())
        return payload

    @staticmethod
    def _remote_file_value(value: str) -> str:
        value = value.strip()
        if not value:
            return ""
        path = Path(value)
        if path.is_absolute() or path.exists():
            return path.name
        return value.replace("\\", "/")

    def _run_remote_request(self, method: str, endpoint: str, payload: Optional[dict]) -> None:
        base_url = self.remote_url_var.get().strip().rstrip("/")
        if not base_url:
            self.add_log_line("Enter the PYNQ runner URL first")
            self.set_status("No runner URL")
            return

        thread = threading.Thread(
            target=self._remote_request_worker,
            args=(method, f"{base_url}{endpoint}", payload),
            daemon=True,
        )
        thread.start()

    def _remote_request_worker(self, method: str, url: str, payload: Optional[dict]) -> None:
        try:
            data = None
            headers = {}
            if payload is not None:
                data = json.dumps(payload).encode("utf-8")
                headers["Content-Type"] = "application/json"
            request = urllib_request.Request(url, data=data, headers=headers, method=method)
            with urllib_request.urlopen(request, timeout=5) as response:
                body = json.loads(response.read().decode("utf-8"))
            self.after(0, lambda body=body: self._handle_remote_response(body))
        except urllib_error.HTTPError as exc:
            try:
                body = json.loads(exc.read().decode("utf-8"))
                message = body.get("error", str(exc))
            except Exception:
                message = str(exc)
            self.after(0, lambda message=message: self._handle_remote_error(message))
        except Exception as exc:
            message = str(exc)
            self.after(0, lambda message=message: self._handle_remote_error(message))

    def _handle_remote_response(self, body: dict) -> None:
        saved = body.get("saved")
        if saved:
            saved_names = ", ".join(item.get("path", item.get("name", "")) for item in saved)
            self.set_status("Upload complete")
            self.set_info(f"Uploaded: {saved_names}")
            self.add_log_line(f"Upload complete: {saved_names}")
            return

        status = body.get("status", {})
        state = status.get("state", "unknown")
        message = status.get("last_message", "")
        current_trial = status.get("current_trial", 0)
        total_trials = status.get("total_trials", 0)

        self.set_status(f"Remote {state}")
        if total_trials:
            self.set_progress(int(current_trial), maximum=int(total_trials))
        if message:
            self.set_info(message)
        self.add_log_line(f"Remote state: {state}" + (f" | {message}" if message else ""))

    def _handle_remote_error(self, message: str) -> None:
        self.set_status("Remote error")
        self.set_indicator("red")
        self.add_log_line(f"Remote error: {message}")

    def detect_mode_from_config(self) -> Optional[str]:
        config = self._read_config()
        if config is None:
            return None

        keys = set(config)
        has_simple = SIMPLE_PATTERN_KEYS.issubset(keys)
        has_braincodec = BRAINCODEC_PATTERN_KEYS.issubset(keys)

        if has_simple and not has_braincodec:
            self.set_mode(MODE_SIMPLE)
            self.add_log_line("Detected config type: Simple patterns")
            self.update_pattern_preview(config)
            self.set_status("Config detected")
            return MODE_SIMPLE
        if has_braincodec and not has_simple:
            self.set_mode(MODE_BRAINCODEC)
            self.add_log_line("Detected config type: Braincodec patterns")
            self.clear_pattern_preview("Braincodec .npy preview not implemented yet")
            self.set_status("Config detected")
            return MODE_BRAINCODEC
        if has_simple and has_braincodec:
            self.add_log_line("Config contains keys for both modes; keeping selected mode")
            self.set_status("Config ambiguous")
            return self.mode_var.get()

        self.add_log_line("Could not detect config type from required keys")
        self.set_status("Config not recognized")
        return None

    def validate_config(self) -> bool:
        config = self._read_config()
        if config is None:
            return False

        required_keys = (
            SIMPLE_PATTERN_KEYS if self.mode_var.get() == MODE_SIMPLE else BRAINCODEC_PATTERN_KEYS
        )
        missing = sorted(required_keys - set(config))
        mode_label = MODE_LABELS[self.mode_var.get()]
        if missing:
            self.add_log_line(f"{mode_label} config is missing: {', '.join(missing)}")
            self.set_status("Config invalid")
            self.set_indicator("red")
            return False

        if self.mode_var.get() == MODE_SIMPLE:
            bad_labels = self._invalid_led_labels(config)
            if bad_labels:
                self.add_log_line(f"Invalid LED labels: {', '.join(bad_labels)}")
                self.set_status("Config invalid")
                self.set_indicator("red")
                return False
            self.update_pattern_preview(config)
        else:
            self.clear_pattern_preview("Braincodec .npy preview not implemented yet")

        self.add_log_line(f"{mode_label} config looks valid")
        self.set_status("Config valid")
        self.set_indicator("green")
        return True

    def update_pattern_preview(self, config: dict) -> None:
        if self.go_pattern_canvas is None or self.nogo_pattern_canvas is None:
            return

        go_pattern = str(config.get("GO", "")).split()
        nogo_pattern = str(config.get("NOGO", "")).split()
        go_irradiance = config.get("GO irradiance (mW/mm2)", "")
        nogo_irradiance = config.get("NOGO irradiance (mW/mm2)", "")

        self._draw_pattern_grid(
            self.go_pattern_canvas,
            go_pattern,
            f"GO ({go_irradiance} mW/mm2)",
            active_color="#2ca25f",
        )
        self._draw_pattern_grid(
            self.nogo_pattern_canvas,
            nogo_pattern,
            f"NO-GO ({nogo_irradiance} mW/mm2)",
            active_color="#de2d26",
        )

    def clear_pattern_preview(self, message: str = "") -> None:
        if self.go_pattern_canvas is None or self.nogo_pattern_canvas is None:
            return
        self._draw_empty_pattern_preview(message)

    def simulate_session(self) -> None:
        if not self.validate_config():
            return

        trials = self._read_trials()
        if not trials:
            return

        self._stop_simulation()
        self._simulation_trials = trials
        self._simulation_index = 0
        self.set_progress(0, maximum=len(trials))
        self.set_status("Simulating")
        self.add_log_line(
            "Simulation started "
            f"(wait_for_trigger={self.wait_for_trigger_var.get()}, "
            f"ext_cables_used={self.ext_cables_used_var.get()})"
        )
        self._simulation_after_id = self.after(250, self._simulate_next_trial)

    def _simulate_next_trial(self) -> None:
        if self._simulation_index >= len(self._simulation_trials):
            self._simulation_after_id = None
            self.set_status("Simulation finished")
            self.set_info("Simulation finished")
            self.set_indicator("gray")
            self.add_log_line("Simulation finished")
            return

        trial_number = self._simulation_index + 1
        trial_code = self._simulation_trials[self._simulation_index]
        trial_type, color = self._trial_type_for_code(trial_code)
        self.set_progress(trial_number, maximum=len(self._simulation_trials))
        self.set_indicator(color)
        self.set_status("Simulating")
        self.set_info(f"Trial {trial_number} of {len(self._simulation_trials)} ({trial_type})")
        self.add_log_line(f"Trial {trial_number}: {trial_type} (code {self._format_trial_code(trial_code)})")

        self._simulation_index += 1
        self._simulation_after_id = self.after(600, self._simulate_next_trial)

    def _stop_simulation(self) -> None:
        if self._simulation_after_id is not None:
            self.after_cancel(self._simulation_after_id)
            self._simulation_after_id = None

    def _read_trials(self) -> list[float]:
        trials_path = self.trials_file_var.get().strip()
        if not trials_path:
            self.add_log_line("Select a trials file first")
            self.set_status("No trials")
            return []

        path = Path(trials_path)
        if not path.exists():
            self.add_log_line(f"Trials file not found: {trials_path}")
            self.set_status("Trials missing")
            return []

        trials = []
        try:
            for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
                cleaned = raw_line.strip()
                if not cleaned or cleaned.startswith("#"):
                    continue
                for value in cleaned.replace(",", " ").split():
                    trials.append(float(value))
        except Exception as exc:
            self.add_log_line(f"Could not read trials file: {exc}")
            self.set_status("Trials error")
            return []

        if not trials:
            self.add_log_line("Trials file contains no numeric trial codes")
            self.set_status("Trials empty")
        return trials

    def _trial_type_for_code(self, trial_code: float) -> tuple[str, str]:
        mode = self.mode_var.get()
        if mode == MODE_SIMPLE:
            if trial_code == 1:
                return "GO", "green"
            if trial_code == 2:
                return "NO-GO", "red"
            if trial_code == 0:
                return "BLANK", "lightgrey"
            return "INTERMEDIATE (not implemented)", "orange"

        config = self._read_config() or {}
        catch_trials = bool(config.get("catch_trials", True))
        if not catch_trials and 2 <= trial_code <= 15:
            return "BLANK", "lightgrey"
        if trial_code == 1:
            return "GO", "green"
        if 2 <= trial_code <= 15:
            return f"CATCH {int(trial_code - 1)}", "orange"
        return "NO-GO", "red"

    @staticmethod
    def _format_trial_code(trial_code: float) -> str:
        if float(trial_code).is_integer():
            return str(int(trial_code))
        return str(trial_code)

    def _draw_empty_pattern_preview(self, message: str) -> None:
        if self.go_pattern_canvas is None or self.nogo_pattern_canvas is None:
            return
        for canvas in (self.go_pattern_canvas, self.nogo_pattern_canvas):
            canvas.delete("all")
            canvas.create_text(140, 140, text=message, width=230, fill="#555555")

    def _draw_pattern_grid(self, canvas: tk.Canvas, pattern: list[str], title: str, active_color: str) -> None:
        active_labels = set(pattern)
        canvas.delete("all")
        canvas.create_text(140, 15, text=title, font=("TkDefaultFont", 9, "bold"))

        left = 35
        top = 35
        cell = 25

        for p_number in range(1, 11):
            x = left + (p_number - 1) * cell + cell / 2
            canvas.create_text(x, top - 12, text=f"P{p_number}", font=("TkDefaultFont", 7))

        for n_number in range(1, 11):
            y = top + (n_number - 1) * cell + cell / 2
            canvas.create_text(left - 14, y, text=f"N{n_number}", font=("TkDefaultFont", 7))

        for n_number in range(1, 11):
            for p_number in range(1, 11):
                label = f"P{p_number}N{n_number}"
                is_active = label in active_labels
                color = active_color if is_active else "#f2f2f2"
                text_color = "white" if is_active else "#777777"
                x0 = left + (p_number - 1) * cell
                y0 = top + (n_number - 1) * cell
                x1 = x0 + cell
                y1 = y0 + cell
                canvas.create_rectangle(
                    x0,
                    y0,
                    x1,
                    y1,
                    fill=color,
                    outline="#9e9e9e",
                )
                canvas.create_text(
                    x0 + cell / 2,
                    y0 + cell / 2,
                    text=label,
                    font=("TkDefaultFont", 5),
                    fill=text_color,
                )

    def _refresh_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.insert(tk.END, "\n".join(self._log_buffer))
        if self._log_buffer:
            self.log_text.insert(tk.END, "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _read_config(self) -> Optional[dict]:
        config_path = self.config_file_var.get().strip()
        if not config_path:
            self.add_log_line("Select a config file first")
            self.set_status("No config")
            return None
        path = Path(config_path)
        if not path.exists():
            self.add_log_line(f"Config file not found: {config_path}")
            self.set_status("Config missing")
            return None

        try:
            config_text = path.read_text()
            config = self._load_config_text(config_text)
        except Exception as exc:
            self.add_log_line(f"Could not read config: {exc}")
            self.set_status("Config error")
            return None

        if not isinstance(config, dict):
            self.add_log_line("Config file must contain YAML key/value settings")
            self.set_status("Config error")
            return None
        return config

    def _load_config_text(self, config_text: str) -> dict:
        if yaml is not None:
            return yaml.safe_load(config_text)
        return self._load_simple_yaml(config_text)

    def _load_simple_yaml(self, config_text: str) -> dict:
        config = {}
        for line_number, raw_line in enumerate(config_text.splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                raise ValueError(f"Line {line_number} is not a key/value setting")

            key, value = line.split(":", maxsplit=1)
            key = key.strip()
            value = self._strip_inline_comment(value.strip())
            config[key] = self._parse_scalar_value(value)
        return config

    @staticmethod
    def _strip_inline_comment(value: str) -> str:
        quote = None
        for index, character in enumerate(value):
            if character in ("'", '"'):
                quote = None if quote == character else character
            elif character == "#" and quote is None:
                return value[:index].strip()
        return value

    @staticmethod
    def _parse_scalar_value(value: str):
        if not value:
            return ""
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            return value[1:-1]
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            return value

    def _invalid_led_labels(self, config: dict) -> list[str]:
        valid_labels = {f"P{p}N{n}" for p in range(1, 11) for n in range(1, 11)}
        labels = []
        for key in ("GO", "NOGO"):
            labels.extend(str(config.get(key, "")).split())
        return [label for label in labels if label not in valid_labels]

    def _on_mode_changed(self) -> None:
        mode = self.mode_var.get()
        if mode == MODE_SIMPLE:
            for widget in self.patterns_row:
                widget.grid_remove()
            self.generated_secondary_label.configure(text="Blank %")
            self.generated_secondary_entry.configure(textvariable=self.generated_blank_percent_var)
            self.set_info("Simple patterns: use a YAML config plus a trials file.")
        else:
            for widget in self.patterns_row:
                widget.grid()
            self.generated_secondary_label.configure(text="Catch %")
            self.generated_secondary_entry.configure(textvariable=self.generated_catch_percent_var)
            self.clear_pattern_preview("Braincodec .npy preview not implemented yet")
            self.set_info("Braincodec patterns: use YAML, trials, and a .npy patterns file.")

    def _handle_start(self) -> None:
        if not self.validate_config():
            return
        self.set_status("Starting")
        self.add_log_line("Start requested")
        if self.on_start is not None:
            self.on_start()

    def _handle_stop(self) -> None:
        self._stop_simulation()
        self.set_status("Stopping")
        self.add_log_line("Stop requested")
        if self.on_stop is not None:
            self.on_stop()


class BraincodecStandaloneApp(tk.Tk):
    """Small desktop wrapper so the panel can be launched from a terminal."""

    def __init__(self):
        super().__init__()
        self.title("Braincodec Control")
        self.geometry("780x520")
        self.minsize(620, 420)
        self.panel = BraincodecTkPanel(self, on_start=self._demo_start, on_stop=self._demo_stop)
        self.panel.pack(fill=tk.BOTH, expand=True)

    def _demo_start(self) -> None:
        self.panel.set_status("Ready for runner")
        self.panel.set_info("Standalone GUI is running. Connect this callback to the hardware runner.")
        self.panel.set_indicator("green")

    def _demo_stop(self) -> None:
        self.panel.set_status("Stopped")
        self.panel.set_info("Stopped")
        self.panel.set_indicator("red")


def main() -> None:
    app = BraincodecStandaloneApp()
    app.mainloop()


if __name__ == "__main__":
    main()
