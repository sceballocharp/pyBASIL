"""Tkinter Braincodec panel for terminal use and pyBEHAVIOR integration."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Callable, Optional
import tkinter as tk

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
        self.mode_var = tk.StringVar(value=MODE_SIMPLE)
        self.status_var = tk.StringVar(value="Idle")
        self.info_var = tk.StringVar(value="Waiting")
        self.progress_var = tk.IntVar(value=0)
        self.progress_max = 100
        self.indicator_color = "gray"
        self.go_pattern_canvas = None
        self.nogo_pattern_canvas = None

        self._build_widgets()

    def _build_widgets(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        controls = ttk.LabelFrame(self, text="Braincodec Control")
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(5, weight=1)

        self.start_button = ttk.Button(controls, text="Start", command=self._handle_start)
        self.start_button.grid(row=0, column=0, padx=4, pady=6, sticky="ew")

        self.stop_button = ttk.Button(controls, text="Stop", command=self._handle_stop)
        self.stop_button.grid(row=0, column=1, padx=4, pady=6, sticky="ew")

        ttk.Button(controls, text="Clear Log", command=self.clear_log).grid(
            row=0, column=2, padx=4, pady=6, sticky="ew"
        )

        ttk.Label(controls, text="Status").grid(row=0, column=3, padx=(16, 4), pady=6)
        ttk.Label(controls, textvariable=self.status_var, width=24).grid(
            row=0, column=4, padx=4, pady=6, sticky="w"
        )

        self.indicator = tk.Canvas(controls, width=38, height=38, highlightthickness=0)
        self.indicator.grid(row=0, column=5, padx=8, pady=6, sticky="w")
        self._indicator_item = self.indicator.create_oval(
            5, 5, 33, 33, fill=self.indicator_color, outline="black", width=2
        )

        mode = ttk.LabelFrame(self, text="Experiment Type")
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

        files = ttk.LabelFrame(self, text="Files")
        files.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        files.columnconfigure(1, weight=1)

        self._file_row(files, 0, "Config", self.config_file_var, self._browse_config)
        self._file_row(files, 1, "Trials", self.trials_file_var, self._browse_trials)
        self.patterns_row = self._file_row(
            files, 2, "Patterns", self.patterns_file_var, self._browse_patterns
        )

        preview = ttk.LabelFrame(self, text="Pattern Preview")
        preview.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        preview.columnconfigure(0, weight=1)
        self._build_pattern_preview(preview)

        runtime = ttk.LabelFrame(self, text="Run")
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
        parent.columnconfigure(1, weight=1)

        go_frame = ttk.Frame(parent)
        go_frame.grid(row=0, column=0, sticky="nsew", padx=(6, 3), pady=6)
        nogo_frame = ttk.Frame(parent)
        nogo_frame.grid(row=0, column=1, sticky="nsew", padx=(3, 6), pady=6)

        ttk.Label(go_frame, text="GO").pack(anchor="center")
        self.go_pattern_canvas = tk.Canvas(go_frame, width=310, height=310, background="white")
        self.go_pattern_canvas.pack(fill=tk.BOTH, expand=True)

        ttk.Label(nogo_frame, text="NO-GO").pack(anchor="center")
        self.nogo_pattern_canvas = tk.Canvas(nogo_frame, width=310, height=310, background="white")
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
        }

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

    def _draw_empty_pattern_preview(self, message: str) -> None:
        if self.go_pattern_canvas is None or self.nogo_pattern_canvas is None:
            return
        for canvas in (self.go_pattern_canvas, self.nogo_pattern_canvas):
            canvas.delete("all")
            canvas.create_text(155, 155, text=message, width=260, fill="#555555")

    def _draw_pattern_grid(self, canvas: tk.Canvas, pattern: list[str], title: str, active_color: str) -> None:
        active_labels = set(pattern)
        canvas.delete("all")
        canvas.create_text(155, 15, text=title, font=("TkDefaultFont", 9, "bold"))

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
            self.set_info("Simple patterns: use a YAML config plus a trials file.")
        else:
            for widget in self.patterns_row:
                widget.grid()
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
