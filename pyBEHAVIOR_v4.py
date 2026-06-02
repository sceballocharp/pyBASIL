import os
import queue
import random
import re
import struct
import threading
import time
import tkinter as tk
import csv
import math
import statistics
from datetime import datetime, timezone
from tkinter import filedialog, messagebox, ttk

try:
    import numpy as np
except Exception:
    np = None

try:
    from scipy.io import loadmat
except Exception:
    loadmat = None

try:
    import nidaqmx
    from nidaqmx.constants import AcquisitionType, LineGrouping, TerminalConfiguration
except Exception:
    nidaqmx = None
    AcquisitionType = None
    LineGrouping = None
    TerminalConfiguration = None

try:
    import sounddevice as sd
except Exception:
    sd = None

try:
    import h5py
except Exception:
    h5py = None

try:
    from pynwb import NWBFile, NWBHDF5IO, TimeSeries
except Exception:
    NWBFile = None
    NWBHDF5IO = None
    TimeSeries = None


APP_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SAVE_ROOT = r"\\helix.pasteur.fr\projects\Bathellierlab\User_folders"
DEFAULT_NI_SCRIPT = os.path.join(APP_DIR, "setup_valves_IRFork.m")
DEFAULT_SOUND_FILE = (
    r"\\helix.pasteur.fr\projects\Bathellierlab\User_folders\Sebastian"
    r"\Sounds\FM_GoNoGo\12-Jan-2026\AllSounds_Corrected.mat"
)


class BehaviorAcquisitionApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("pyBEHAVIOR_v4")
        screen_height = self.winfo_screenheight()
        self.geometry(f"1120x{int(screen_height * 0.90)}+0+0")

        self.acq_thread = None
        self.running = False
        self.plot_queue = queue.Queue()
        self.time_buffer = []
        self.data_buffer = []
        self.soundcopy_buffer = []
        self.full_soundcopy_buffer = []
        self.trigger_pulses = []
        self.sound_outputs = []
        self.trial_state_intervals = []
        self.full_trigger_pulses = []
        self.full_sound_outputs = []
        self.irfork_file = None
        self.soundcopy_file = None
        self.exp_folder = ""
        self.irfork_was_high = False
        self.last_trigger_time = -1e12
        self.next_trial_allowed_time_s = -1e12
        self.current_ir_baseline = 0.0
        self.sound_data = None
        self.sound_loaded = False
        self.sound_sequence = []
        self.sound_sequence_index = 0
        self.trial_index = 0
        self.acq_start_perf = None
        self.acq_sample_index = 0
        self.trial_log_path = ""
        self.parameters_log_path = ""
        self.trial_rows = []
        self.parameter_rows = []
        self.current_parameter_signature = None
        self.parameter_block_index = 0
        self.active_trial_index = None
        self.active_trial_start_s = None
        self.active_trial_end_s = None
        self.active_high_start_s = None
        self.active_crossing_total_s = 0.0
        self.active_lick_count = 0
        self.active_reward_decided = False
        self.active_trial_base_iti_s = 0.0
        self.active_trial_extra_timeout_s = 0.0
        self.active_lever_sound_id = 1
        self.active_lever_next_sound_time_s = None
        self.active_lever_low_start_s = None
        self.lever_sound_gap_s = 0.5
        self.active_dmts_sample_sound_id = 1
        self.active_dmts_test_sound_id = 2
        self.active_dmts_test_sound_time_s = None
        self.active_dmts_response_start_s = None
        self.active_dmts_response_end_s = None
        self.active_dmts_reward_start_s = None
        self.active_dmts_response_evaluated = False
        self.active_dmts_response_met = False
        self.active_dmts_test_sound_played = False
        self.active_dmts_response_started = False
        self.active_dmts_scored = False
        self.sim_next_pulse_start_s = 0.0
        self.sim_pulse_end_s = -1.0
        self.results_window = None
        self.results_canvas = None
        self.nwb_saving = False

        self.ai_task = None
        self.reward_task = None

        self._build_ui()
        self.generate_sequence(log=False)
        self.after(50, self._drain_plot_queue)
        self.log("pyBEHAVIOR_v4 ready.")
        if nidaqmx is None:
            self.log("nidaqmx not available: hardware acquisition/output will use simulation or be disabled.")
        if loadmat is None:
            self.log("scipy not available: MATLAB .mat sound loading is disabled.")
        if NWBFile is None:
            self.log("pynwb not available: NWB export is disabled until pynwb is installed.")

    def _build_ui(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(4, weight=3)
        root.rowconfigure(5, weight=1)

        run_setup = ttk.LabelFrame(root, text="Control And Files")
        run_setup.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        run_setup.columnconfigure(0, weight=1)
        run_setup.columnconfigure(1, weight=1)
        run_setup_left = ttk.Frame(run_setup)
        run_setup_left.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        run_setup_left.columnconfigure(1, weight=1)
        for col in range(3):
            run_setup_left.columnconfigure(col, weight=1, uniform="main_buttons")
        run_setup_right = ttk.Frame(run_setup)
        run_setup_right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.ni_script = tk.StringVar(value=DEFAULT_NI_SCRIPT)
        self.sound_file = tk.StringVar(value=DEFAULT_SOUND_FILE)
        self.simulation_mode = tk.BooleanVar(value=False)
        self.big_button_style = "Big.TButton"
        ttk.Style().configure(self.big_button_style, font=("Segoe UI", 12, "bold"), padding=(12, 8))
        ttk.Button(run_setup_left, text="Start Live", command=self.start_live, style=self.big_button_style).grid(row=0, column=0, padx=4, pady=6, sticky="ew")
        ttk.Button(run_setup_left, text="Stop", command=self.stop_live, style=self.big_button_style).grid(row=0, column=1, padx=4, pady=6, sticky="ew")
        ttk.Button(run_setup_left, text="Clear", command=self.clear_plot, style=self.big_button_style).grid(row=0, column=2, padx=4, pady=6, sticky="ew")
        ttk.Label(run_setup_left, text="Status").grid(row=0, column=3, padx=(20, 4))
        self.status_canvas = tk.Canvas(run_setup_left, width=18, height=18, highlightthickness=0)
        self.status_canvas.grid(row=0, column=4)
        self.status_dot = self.status_canvas.create_oval(2, 2, 16, 16, fill="gray", outline="")
        ttk.Button(run_setup_left, text="Import parameters", command=self.import_parameters_file).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ttk.Button(run_setup_left, text="Save NWB", command=self.save_nwb_placeholder).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        ttk.Button(run_setup_left, text="Open .bin", command=self.open_bin).grid(row=1, column=2, padx=4, pady=4, sticky="ew")
        ttk.Button(run_setup_left, text="Results Figure", command=self.open_results_window).grid(row=1, column=3, padx=4, pady=4, sticky="ew")
        ttk.Checkbutton(run_setup_left, text="Simulation", variable=self.simulation_mode).grid(row=1, column=4, padx=4, pady=4, sticky="w")
        self._file_row(run_setup_left, 2, "NI script", self.ni_script, self.choose_ni_script)
        self._file_row(run_setup_left, 3, "Sound .mat", self.sound_file, self.choose_sound_file)

        session = ttk.LabelFrame(root, text="Session")
        session.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        self.user_name = tk.StringVar(value="username")
        self.mouse_id = tk.StringVar(value="1")
        self.project_name = tk.StringVar(value="ProjectName")
        self.output_format = tk.StringVar(value="NWB")
        self.save_root = tk.StringVar(value=DEFAULT_SAVE_ROOT)
        self._entry(session, 0, "User", self.user_name, width=14)
        self._entry(session, 2, "Mouse", self.mouse_id, width=8)
        self._entry(session, 4, "Project", self.project_name, width=18)
        ttk.Label(session, text="Output").grid(row=0, column=6, padx=(14, 4))
        ttk.Combobox(session, textvariable=self.output_format, values=("NWB", "BIDS", "No standard"), width=12).grid(row=0, column=7)
        self._entry(session, 8, "Save root", self.save_root, width=32)

        acq = ttk.LabelFrame(root, text="Acquisition")
        acq.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        self.device = tk.StringVar(value="Dev1")
        self.channels = tk.StringVar(value="ai6,ai5,ai1")
        self.rate_hz = tk.StringVar(value="1000")
        self.window_s = tk.StringVar(value="10")
        self.callback_s = tk.StringVar(value="0.1")
        self.auto_scale = tk.BooleanVar(value=False)
        self.ai_terminal_config = tk.StringVar(value="RSE")
        self.subtract_baseline = tk.BooleanVar(value=False)
        self.left_y_min = tk.StringVar(value="-1")
        self.left_y_max = tk.StringVar(value="5")
        self.right_y_min = tk.StringVar(value="-1")
        self.right_y_max = tk.StringVar(value="5")
        self._entry(acq, 0, "Device", self.device, width=9)
        self._entry(acq, 2, "Channels", self.channels, width=16)
        self._entry(acq, 4, "Rate Hz", self.rate_hz, width=9)
        self._entry(acq, 6, "Window s", self.window_s, width=8)
        self._entry(acq, 8, "Callback s", self.callback_s, width=8)
        ttk.Label(acq, text="AI terminal").grid(row=0, column=10, padx=(10, 4))
        ttk.Combobox(
            acq,
            textvariable=self.ai_terminal_config,
            values=("RSE", "NRSE", "DIFF", "DEFAULT"),
            state="readonly",
            width=8,
        ).grid(row=0, column=11)
        ttk.Checkbutton(acq, text="Auto scale", variable=self.auto_scale).grid(row=0, column=12, padx=10)
        ttk.Checkbutton(acq, text="Subtract baseline", variable=self.subtract_baseline).grid(row=0, column=13, padx=10)
        self._entry(acq, 0, "Left ymin", self.left_y_min, width=7, row=1)
        self._entry(acq, 2, "Left ymax", self.left_y_max, width=7, row=1)
        self._entry(acq, 4, "Right ymin", self.right_y_min, width=7, row=1)
        self._entry(acq, 6, "Right ymax", self.right_y_max, width=7, row=1)

        trig = ttk.LabelFrame(root, text="Trigger And Sound")
        trig.grid(row=3, column=0, sticky="ew", pady=(0, 6))
        self.trigger_type = tk.StringVar(value="IRFork")
        self.write_irfork_bin = tk.BooleanVar(value=True)
        self.trigger_output_on_crossing = tk.BooleanVar(value=True)
        self.play_sound_on_crossing = tk.BooleanVar(value=True)
        self.threshold_v = tk.StringVar(value="1")
        self.pulse_ms = tk.StringVar(value="50")
        self.sound_id = tk.StringVar(value="1")
        self.sound_level = tk.StringVar(value="1")
        ttk.Label(trig, text="Trigger").grid(row=0, column=0, padx=(4, 4))
        ttk.Combobox(trig, textvariable=self.trigger_type, values=("IRFork", "Lick", "None"), width=9).grid(row=0, column=1)
        ttk.Checkbutton(trig, text="Write IRFork.bin", variable=self.write_irfork_bin).grid(row=0, column=2, padx=8)
        ttk.Checkbutton(trig, text="Trigger output", variable=self.trigger_output_on_crossing).grid(row=0, column=3, padx=8)
        ttk.Button(trig, text="Trigger Output", command=self.send_output_pulse).grid(row=0, column=4, padx=8)
        ttk.Checkbutton(trig, text="Play sound", variable=self.play_sound_on_crossing).grid(row=0, column=5, padx=8)
        self._entry(trig, 6, "Threshold V", self.threshold_v, width=6)
        self._entry(trig, 8, "Pulse ms", self.pulse_ms, width=6)
        self._entry(trig, 0, "Sound id", self.sound_id, width=6, row=1)
        self._entry(trig, 2, "Level", self.sound_level, width=6, row=1)
        ttk.Button(trig, text="Test Sound", command=lambda: self.play_loaded_sound(use_sequence=False)).grid(row=1, column=4, padx=8, pady=4)

        body = ttk.Frame(root)
        body.grid(row=4, column=0, sticky="nsew")
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        plot_frame = ttk.LabelFrame(body, text="Live Acquisition")
        plot_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 8))
        self.plot_canvas = tk.Canvas(plot_frame, height=190, bg="white")
        self.plot_canvas.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        seq = ttk.LabelFrame(body, text="Closed Loop Sequence")
        seq.grid(row=0, column=1, sticky="nsew", pady=(0, 6))
        self.sequence_length = tk.StringVar(value="300")
        self.sequence_values = tk.StringVar(value="1 10")
        self.sequence_weights = tk.StringVar(value="0.5 0.5")
        self.sequence_index_var = tk.StringVar(value="0")
        self.sequence_next_var = tk.StringVar(value="1")
        self.last_trial_sound_var = tk.StringVar(value="")
        self.last_trial_type_var = tk.StringVar(value="")
        self.random_seed = tk.StringVar(value="")
        self.max_trials = tk.StringVar(value="0")
        self._entry(seq, 0, "Length", self.sequence_length, width=6)
        self._entry(seq, 2, "Values", self.sequence_values, width=10)
        self._entry(seq, 4, "Weights", self.sequence_weights, width=10)
        self._entry(seq, 6, "Seed", self.random_seed, width=6)
        self._entry(seq, 0, "Max trials", self.max_trials, width=6, row=1)
        ttk.Button(seq, text="ReGenerate Sequence", command=self.generate_sequence).grid(row=1, column=2, columnspan=6, sticky="ew", padx=6, pady=6)
        self._entry(seq, 0, "Index", self.sequence_index_var, width=6, row=2, state="readonly")
        self._entry(seq, 2, "Next", self.sequence_next_var, width=6, row=2, state="readonly")
        self._entry(seq, 4, "Last sound", self.last_trial_sound_var, width=7, row=2, state="readonly")
        self._entry(seq, 6, "Last type", self.last_trial_type_var, width=7, row=2, state="readonly")

        trial = ttk.LabelFrame(body, text="Trial Structure")
        trial.grid(row=1, column=1, sticky="nsew")
        self.task_type = tk.StringVar(value="")
        self.iti_s = tk.StringVar(value="1")
        self.iti_rand_min_s = tk.StringVar(value="")
        self.iti_rand_max_s = tk.StringVar(value="")
        self.sound_delay_s = tk.StringVar(value="0")
        self.delay_s = tk.StringVar(value="0")
        self.sound_duration_s = tk.StringVar(value="0")
        self.trial_duration_s = tk.StringVar(value="2")
        self.response_window_s = tk.StringVar(value="2")
        self.reward_delay_s = tk.StringVar(value="0")
        self.hit_threshold_s = tk.StringVar(value="50")
        self.punish_interval = tk.StringVar(value="")
        self.reward_go = tk.StringVar(value="")
        self.punish_no_go_fa = tk.StringVar(value="")
        self.min_lick_count = tk.StringVar(value="")
        self.lick_threshold = tk.StringVar(value="")
        self.lever_hold_time_s = tk.StringVar(value="1")
        self.sample_sound_id = tk.StringVar(value="1")
        self.test_sound_id = tk.StringVar(value="2")
        self.current_trial_var = tk.StringVar(value="0")
        for col in (1, 3, 5, 7):
            trial.columnconfigure(col, weight=1)
        self._entry(trial, 0, "Task type", self.task_type, width=6, row=0)
        self._entry(trial, 2, "Current trial", self.current_trial_var, width=6, row=0, state="readonly")
        self._entry(trial, 4, "RewardGo", self.reward_go, width=6, row=0)
        self._entry(trial, 0, "ITI s", self.iti_s, width=6, row=1)
        self._entry(trial, 2, "ITI min", self.iti_rand_min_s, width=6, row=1)
        self._entry(trial, 4, "ITI max", self.iti_rand_max_s, width=6, row=1)
        self._entry(trial, 0, "Trial s", self.trial_duration_s, width=6, row=2, state="readonly")
        self._entry(trial, 2, "Response s", self.response_window_s, width=6, row=2)
        self._entry(trial, 4, "Reward delay s", self.reward_delay_s, width=6, row=2)
        self.sound_delay_widgets = self._entry(trial, 6, "Sound delay s", self.sound_delay_s, width=6, row=2)
        self.delay_widgets = self._entry(trial, 6, "Delay s", self.delay_s, width=6, row=2)
        self._entry(trial, 4, "Punish FA", self.punish_no_go_fa, width=6, row=3)
        self.min_lick_count_widgets = self._entry(trial, 6, "Min licks", self.min_lick_count, width=6, row=3)
        self.lick_threshold_widgets = self._entry(trial, 2, "Lick thresh", self.lick_threshold, width=6, row=3)
        self.hit_threshold_widgets = self._entry(trial, 2, "Resp. hold %", self.hit_threshold_s, width=6, row=3)
        self.lever_hold_widgets = self._entry(trial, 0, "Lever hold s", self.lever_hold_time_s, width=6, row=3)
        self.sample_sound_widgets = self._entry(trial, 0, "Sample ID", self.sample_sound_id, width=6, row=4)
        self.test_sound_widgets = self._entry(trial, 2, "Test ID", self.test_sound_id, width=6, row=4)
        for var in (self.sound_delay_s, self.delay_s, self.sound_duration_s, self.response_window_s, self.reward_delay_s):
            var.trace_add("write", lambda *_: self.update_trial_duration())
        self.task_type.trace_add("write", lambda *_: (self.update_task_parameter_visibility(), self.update_trial_duration()))
        self.trigger_type.trace_add("write", lambda *_: self.update_task_parameter_visibility())
        self.update_trial_duration()
        self.update_task_parameter_visibility()

        log_frame = ttk.LabelFrame(root, text="Output")
        log_frame.grid(row=5, column=0, sticky="nsew", pady=(8, 0))
        root.rowconfigure(5, weight=1)
        self.log_text = tk.Text(log_frame, height=7, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _file_row(self, parent, row, label, var, command):
        line = ttk.Frame(parent)
        line.grid(row=row, column=0, columnspan=3, sticky="ew", padx=4, pady=3)
        line.columnconfigure(1, weight=1)
        ttk.Label(line, text=label, width=11).grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Entry(line, textvariable=var).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        ttk.Button(line, text="Browse", command=command).grid(row=0, column=2)

    def _entry(self, parent, col, label, var, width=10, row=0, state="normal"):
        label_widget = ttk.Label(parent, text=label)
        entry_widget = ttk.Entry(parent, textvariable=var, width=width, state=state)
        label_widget.grid(row=row, column=col, padx=(6, 4), pady=4, sticky="w")
        entry_widget.grid(row=row, column=col + 1, padx=(0, 6), pady=4, sticky="w")
        return label_widget, entry_widget

    def update_task_parameter_visibility(self):
        if not hasattr(self, "lever_hold_widgets"):
            return
        is_lever = self.is_lever_task()
        is_dmts = self.is_dmts_task()
        is_lick = self.is_lick_trigger()
        self.set_widget_pair_visible(self.sound_delay_widgets, not is_lever and not is_dmts, row=2, col=6)
        self.set_widget_pair_visible(self.delay_widgets, is_dmts, row=2, col=6)
        self.set_widget_pair_visible(self.min_lick_count_widgets, not is_lever, row=3, col=6)
        self.set_widget_pair_visible(self.lick_threshold_widgets, not is_lever and is_lick, row=3, col=2)
        self.set_widget_pair_visible(self.hit_threshold_widgets, not is_lever and not is_lick, row=3, col=2)
        self.set_widget_pair_visible(self.lever_hold_widgets, is_lever, row=3, col=0)
        self.set_widget_pair_visible(self.sample_sound_widgets, is_dmts, row=4, col=0)
        self.set_widget_pair_visible(self.test_sound_widgets, is_dmts, row=4, col=2)

    def set_widget_pair_visible(self, widgets, visible, row, col):
        label_widget, entry_widget = widgets
        if visible:
            label_widget.grid(row=row, column=col, padx=(6, 4), pady=4, sticky="w")
            entry_widget.grid(row=row, column=col + 1, padx=(0, 6), pady=4, sticky="w")
        else:
            label_widget.grid_remove()
            entry_widget.grid_remove()

    def update_trial_duration(self):
        sound_duration_s = self.parse_float(self.sound_duration_s, 0)
        if self.is_dmts_task():
            total = (
                sound_duration_s
                + self.parse_float(self.delay_s, 0)
                + sound_duration_s
                + self.parse_float(self.response_window_s, 0)
                + self.parse_float(self.reward_delay_s, 0)
            )
        else:
            total = (
                self.parse_float(self.sound_delay_s, 0)
                + sound_duration_s
                + self.parse_float(self.response_window_s, 0)
                + self.parse_float(self.reward_delay_s, 0)
            )
        self.trial_duration_s.set(f"{total:g}")

    def log(self, message):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("1.0", f"{stamp}  {message}\n")

    def set_status(self, color):
        self.status_canvas.itemconfig(self.status_dot, fill=color)

    def choose_ni_script(self):
        path = filedialog.askopenfilename(initialdir=APP_DIR, filetypes=[("MATLAB files", "*.m"), ("All files", "*.*")])
        if path:
            self.ni_script.set(path)

    def choose_sound_file(self):
        path = filedialog.askopenfilename(initialdir=APP_DIR, filetypes=[("MAT files", "*.mat"), ("All files", "*.*")])
        if path:
            self.sound_file.set(path)
            self.sound_loaded = False

    def import_parameters_file(self):
        path = filedialog.askopenfilename(
            initialdir=os.path.join(APP_DIR, "protocols") if os.path.isdir(os.path.join(APP_DIR, "protocols")) else self.save_root.get(),
            filetypes=[("DAT files", "*.dat"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            params = self.read_parameters_file(path)
            applied = self.apply_imported_parameters(params)
            self.log(f"Imported {applied} parameters from {os.path.basename(path)}.")
        except Exception as exc:
            messagebox.showerror("Import parameters", f"Could not import parameters:\n{exc}")

    def read_parameters_file(self, path):
        params = {}
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("%"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                elif "\t" in line:
                    key, value = line.split("\t", 1)
                else:
                    parts = line.split(None, 1)
                    if len(parts) != 2:
                        continue
                    key, value = parts
                params[key.strip()] = value.strip()
        return params

    def apply_imported_parameters(self, params):
        mapping = {
            "UserName": self.user_name,
            "MouseId": self.mouse_id,
            "ProjectName": self.project_name,
            "NICard_filename": self.ni_script,
            "Sound_filename": self.sound_file,
            "frec": self.rate_hz,
            "bin": self.callback_s,
            "TriggerTypeDropDown": self.trigger_type,
            "OuputformatDropDown": self.output_format,
            "OutputformatDropDown": self.output_format,
            "TaskType": self.task_type,
            "MaxTrials": self.max_trials,
            "SoundLevel": self.sound_level,
            "RandomSeed": self.random_seed,
            "ITI_s": self.iti_s,
            "ITIrandMin_s": self.iti_rand_min_s,
            "ITIrandMax_s": self.iti_rand_max_s,
            "Sounddelay_s": self.sound_delay_s,
            "SoundDuration_s": self.sound_duration_s,
            "Delay_s": self.delay_s,
            "TrialDuration_s": self.trial_duration_s,
            "ResponseWindow_s": self.response_window_s,
            "RewardDelay_s": self.reward_delay_s,
            "Rewardduration_ms": self.pulse_ms,
            "RewardProb": self.reward_go,
            "HIT": self.hit_threshold_s,
            "HITThreshold_percent": self.hit_threshold_s,
            "HITThreshold_s": self.hit_threshold_s,
            "HIT_s": self.hit_threshold_s,
            "PunishInterval": self.punish_interval,
            "RewardGo": self.reward_go,
            "RewardGoProb": self.reward_go,
            "PunishNoGoFA": self.punish_no_go_fa,
            "Minlickcount": self.min_lick_count,
            "Lickthreshold": self.lick_threshold,
            "LeverThreshold": self.threshold_v,
            "LeverHoldTime_s": self.lever_hold_time_s,
            "SampleSoundId": self.sample_sound_id,
            "TestSoundId": self.test_sound_id,
        }
        applied = 0
        for key, var in mapping.items():
            if key in params:
                var.set(params[key])
                applied += 1
        if "Sound_filename" in params:
            self.sound_loaded = False
        if self.is_lever_task() and not self.lever_hold_time_s.get().strip():
            self.lever_hold_time_s.set("1")
        self.update_task_parameter_visibility()

        sequence_changed = False
        if "GoSoundId" in params or "NoGoSoundId" in params:
            go_id = params.get("GoSoundId", self.sequence_values.get().split()[0] if self.sequence_values.get().split() else "1")
            no_go_id = params.get("NoGoSoundId", "10")
            self.sequence_values.set(f"{go_id} {no_go_id}")
            self.sound_id.set(go_id)
            applied += int("GoSoundId" in params) + int("NoGoSoundId" in params)
            sequence_changed = True
        if "GoWeight" in params or "NoGoWeight" in params:
            go_weight = params.get("GoWeight", self.sequence_weights.get().split()[0] if self.sequence_weights.get().split() else "0.5")
            no_go_weight = params.get("NoGoWeight", "0.5")
            self.sequence_weights.set(f"{go_weight} {no_go_weight}")
            applied += int("GoWeight" in params) + int("NoGoWeight" in params)
            sequence_changed = True
        if sequence_changed:
            self.generate_sequence(log=False)
            self.log("Closed-loop sequence updated from imported Go/NoGo parameters.")
        if self.is_dmts_task():
            self.sound_id.set(self.sample_sound_id.get())
            self.sequence_values.set(f"{self.sample_sound_id.get()} {self.test_sound_id.get()}")
            self.update_trial_duration()
        return applied

    def parse_float(self, var, default):
        return self.parse_float_value(var.get(), default)

    def parse_float_value(self, value, default):
        try:
            return float(value)
        except Exception:
            return default

    def parse_int(self, var, default):
        try:
            return int(float(var.get()))
        except Exception:
            return default

    def parse_channels(self):
        text = self.channels.get().replace(" ", "")
        if ":" in text:
            start, end = text.split(":", 1)
            prefix = "".join(ch for ch in start if not ch.isdigit())
            first = int("".join(ch for ch in start if ch.isdigit()))
            last = int("".join(ch for ch in end if ch.isdigit()))
            return [f"{prefix}{i}" for i in range(first, last + 1)]
        return [item for item in text.replace(";", ",").split(",") if item]

    def setup_tasks(self):
        self.close_tasks()
        if nidaqmx is None:
            return False

        device = self.device.get().strip() or "Dev1"
        rate = self.parse_float(self.rate_hz, 1000)
        channels = self.parse_channels()

        self.ai_task = nidaqmx.Task()
        terminal_config = self.get_ai_terminal_configuration()
        for channel in channels:
            physical_channel = f"{device}/{channel}"
            if terminal_config is None:
                self.ai_task.ai_channels.add_ai_voltage_chan(physical_channel)
            else:
                self.ai_task.ai_channels.add_ai_voltage_chan(physical_channel, terminal_config=terminal_config)
        self.ai_task.timing.cfg_samp_clk_timing(rate, sample_mode=AcquisitionType.CONTINUOUS)

        self.reward_task = nidaqmx.Task()
        self.reward_task.do_channels.add_do_chan(f"{device}/port2/line6", line_grouping=LineGrouping.CHAN_PER_LINE)
        self.reward_task.write(False)

        self.log("NI tasks initialized.")
        return True

    def get_ai_terminal_configuration(self):
        if TerminalConfiguration is None:
            return None
        config = self.ai_terminal_config.get()
        if config == "RSE":
            return TerminalConfiguration.RSE
        if config == "NRSE":
            return TerminalConfiguration.NRSE
        if config == "DIFF":
            return TerminalConfiguration.DIFFERENTIAL
        return None

    def close_tasks(self):
        for attr in ("ai_task", "reward_task"):
            task = getattr(self, attr, None)
            if task is not None:
                try:
                    task.close()
                except Exception:
                    pass
                setattr(self, attr, None)

    def start_live(self):
        if self.running:
            return
        self.clear_buffers()
        self.running = True
        self.irfork_was_high = False
        self.last_trigger_time = -1e12
        self.next_trial_allowed_time_s = -1e12
        self.trial_index = 0
        self.acq_start_perf = None
        self.acq_sample_index = 0
        self.trial_log_path = ""
        self.parameters_log_path = ""
        self.trial_rows = []
        self.parameter_rows = []
        self.current_parameter_signature = None
        self.parameter_block_index = 0
        self.active_trial_index = None
        self.active_trial_start_s = None
        self.active_trial_end_s = None
        self.active_high_start_s = None
        self.active_crossing_total_s = 0.0
        self.active_lick_count = 0
        self.active_reward_decided = False
        self.active_trial_base_iti_s = 0.0
        self.active_trial_extra_timeout_s = 0.0
        self.active_lever_sound_id = 1
        self.active_lever_next_sound_time_s = None
        self.active_lever_low_start_s = None
        self.lever_sound_gap_s = 0.5
        self.active_dmts_sample_sound_id = 1
        self.active_dmts_test_sound_id = 2
        self.active_dmts_test_sound_time_s = None
        self.active_dmts_response_start_s = None
        self.active_dmts_response_end_s = None
        self.active_dmts_reward_start_s = None
        self.active_dmts_response_evaluated = False
        self.active_dmts_response_met = False
        self.active_dmts_test_sound_played = False
        self.active_dmts_response_started = False
        self.active_dmts_scored = False
        self.sim_next_pulse_start_s = 0.0
        self.sim_pulse_end_s = -1.0
        self.current_trial_var.set("0")
        self.last_trial_sound_var.set("")
        self.last_trial_type_var.set("")
        self.open_results_window()
        self.set_status("green")
        self.prepare_session_folder()
        self.open_irfork_file()
        if self.simulation_mode.get():
            self.close_tasks()
            self.log("Simulation mode enabled: generated IR crossings will be used.")
        else:
            self.setup_tasks()
        if self.play_sound_on_crossing.get():
            self.load_sound_file()
        self.acq_thread = threading.Thread(target=self.acquisition_loop, daemon=True)
        self.acq_thread.start()
        self.log("Live acquisition started.")

    def stop_live(self):
        self.running = False
        if self.active_trial_index is not None and self.time_buffer:
            trial_end_s = min(self.time_buffer[-1], self.active_trial_end_s or self.time_buffer[-1])
            if self.is_lever_task():
                self.finish_active_lever_trial(trial_end_s, success=False)
            else:
                self.finish_active_trial(trial_end_s)
        self.close_irfork_file()
        self.close_tasks()
        if self.output_format.get() == "NWB":
            self.save_nwb(silent=True)
        self.set_status("gray")
        self.log("Live acquisition stopped.")

    def clear_buffers(self):
        self.time_buffer.clear()
        self.data_buffer.clear()
        self.soundcopy_buffer.clear()
        self.full_soundcopy_buffer.clear()
        self.trigger_pulses.clear()
        self.sound_outputs.clear()
        self.trial_state_intervals.clear()
        self.full_trigger_pulses.clear()
        self.full_sound_outputs.clear()
        self.current_ir_baseline = 0.0

    def clear_plot(self):
        self.clear_buffers()
        self.plot_canvas.delete("all")
        self.log_text.delete("1.0", tk.END)

    def acquisition_loop(self):
        rate = self.parse_float(self.rate_hz, 1000)
        callback_s = self.parse_float(self.callback_s, 0.1)
        count = max(1, int(rate * callback_s))
        start_time = time.perf_counter()
        self.acq_start_perf = start_time

        use_simulation = self.simulation_mode.get()
        if self.ai_task is not None and not use_simulation:
            self.ai_task.start()

        while self.running:
            try:
                if self.ai_task is not None and not use_simulation:
                    raw = self.ai_task.read(number_of_samples_per_channel=count, timeout=2.0)
                    data = self.normalize_read(raw, count)
                    chunk_start_sample = self.acq_sample_index
                    times = [(chunk_start_sample + i) / rate for i in range(len(data))]
                    self.acq_sample_index += len(data)
                else:
                    data, times = self.simulate_data(count, rate)
                    time.sleep(callback_s)
                self.handle_data(times, data)
            except Exception as exc:
                self.plot_queue.put(("log", f"Acquisition error: {exc}"))
                self.plot_queue.put(("status", "red"))
                self.running = False
                break

    def normalize_read(self, raw, count):
        if not raw:
            return []
        if isinstance(raw[0], list):
            channels = raw
            return [list(row) for row in zip(*channels)]
        return [[x] for x in raw[:count]]

    def simulate_data(self, count, rate):
        values = []
        times = []
        for i in range(count):
            sample_index = self.acq_sample_index + i
            t = sample_index / rate
            times.append(t)
            # Simulated beam crossings every 3 seconds, with randomized crossing duration.
            while t >= self.sim_next_pulse_start_s:
                self.sim_pulse_end_s = self.sim_next_pulse_start_s + random.uniform(0.1, 2.0)
                self.sim_next_pulse_start_s += 3.0
            ir = 1.4 if t < self.sim_pulse_end_s else 0.1
            values.append([ir, 0.0, 0.0])
        self.acq_sample_index += count
        return values, times

    def handle_data(self, times, rows):
        if not rows:
            return
        ir_col = 0
        raw_ir_values = [row[ir_col] for row in rows]
        soundcopy_col = self.get_soundcopy_column(rows)
        raw_soundcopy_values = [row[soundcopy_col] for row in rows] if soundcopy_col is not None else [0.0] * len(rows)
        self.time_buffer.extend(times)
        self.data_buffer.extend(raw_ir_values)
        self.soundcopy_buffer.extend(raw_soundcopy_values)
        self.full_soundcopy_buffer.extend(raw_soundcopy_values)

        if self.irfork_file is not None:
            self.irfork_file.write(struct.pack(f"{len(rows)}d", *raw_ir_values))
        if self.soundcopy_file is not None and soundcopy_col is not None:
            self.soundcopy_file.write(struct.pack(f"{len(rows)}d", *raw_soundcopy_values))

        window = self.parse_float(self.window_s, 10)
        min_time = self.time_buffer[-1] - window
        while self.time_buffer and self.time_buffer[0] < min_time:
            self.time_buffer.pop(0)
            self.data_buffer.pop(0)
            if self.soundcopy_buffer:
                self.soundcopy_buffer.pop(0)
        self.current_ir_baseline = statistics.median(self.data_buffer) if self.subtract_baseline.get() and self.data_buffer else 0.0
        corrected_ir_values = [value - self.current_ir_baseline for value in raw_ir_values]
        self.check_trigger(times, corrected_ir_values)
        self.plot_queue.put(("plot", (list(self.time_buffer), list(self.data_buffer))))

    def get_soundcopy_column(self, rows):
        if not rows or len(rows[0]) < 2:
            return None
        return 1

    def check_trigger(self, times, ir_values):
        threshold = self.get_current_trigger_threshold()

        for sample_time_s, value in zip(times, ir_values):
            if self.is_lever_task():
                self.check_lever_trigger_sample(sample_time_s, value, threshold)
                continue

            if self.active_trial_index is not None and self.active_trial_end_s is not None and sample_time_s >= self.active_trial_end_s:
                if self.is_dmts_task():
                    self.finish_active_dmts_timeline(self.active_trial_end_s)
                else:
                    self.finish_active_trial(self.active_trial_end_s)

            is_high = value >= threshold
            crossed_up = is_high and not self.irfork_was_high
            crossed_down = not is_high and self.irfork_was_high
            self.irfork_was_high = is_high

            if self.active_trial_index is not None:
                if self.is_dmts_task():
                    self.update_active_dmts_trial(sample_time_s, is_high, crossed_up, crossed_down)
                elif self.is_lick_trigger():
                    if crossed_up:
                        self.add_active_lick()
                elif crossed_up:
                    self.active_high_start_s = sample_time_s
                elif crossed_down:
                    self.add_active_high_interval(sample_time_s)
                if not self.is_dmts_task():
                    self.evaluate_active_trial(sample_time_s)
                continue

            if not crossed_up:
                continue

            if sample_time_s < self.next_trial_allowed_time_s:
                continue

            max_trials = max(0, self.parse_int(self.max_trials, 0))
            if max_trials and self.trial_index >= max_trials:
                self.plot_queue.put(("log", f"Accepted crossing ignored: max trials {max_trials} reached."))
                continue

            sound_id = self.parse_int(self.sample_sound_id, 1) if self.is_dmts_task() else (
                self.consume_next_sound_id() if self.play_sound_on_crossing.get() else self.parse_int(self.sound_id, 1)
            )
            iti = self.draw_trial_iti_s()
            self.create_trial(sound_id, sample_time_s, threshold, iti)
            if self.is_dmts_task():
                self.start_active_dmts_trial(sample_time_s, iti)
            else:
                self.start_active_trial(sample_time_s, iti)
            if self.is_lick_trigger() and not self.is_dmts_task():
                self.add_active_lick()
            if self.play_sound_on_crossing.get() and not self.is_dmts_task():
                self.play_loaded_sound(sound_id=sound_id, from_worker=True, start_s=sample_time_s)
            self.last_trigger_time = sample_time_s
            trial_type_id, trial_type = self.classify_trial_sound(sound_id)
            trigger_name = self.trigger_type.get().strip() or "Trigger"
            self.plot_queue.put(("log", f"{trigger_name} crossed {threshold:g} V. Trial {self.trial_index} is type {trial_type_id} {trial_type}, sound id {sound_id}."))
            if not self.is_dmts_task():
                self.evaluate_active_trial(sample_time_s)

    def prepare_session_folder(self):
        date_folder = datetime.now().strftime("%Y%m%d")
        time_folder = datetime.now().strftime("%H%M%S") + "_Data"
        user_folder = os.path.join(self.save_root.get(), self.user_name.get())
        behavior_folder = os.path.join(user_folder, "behavior_data")
        mouse_folder = os.path.join(behavior_folder, "M" + self.mouse_id.get())
        self.exp_folder = os.path.join(
            mouse_folder,
            date_folder,
            time_folder,
        )
        os.makedirs(behavior_folder, exist_ok=True)
        os.makedirs(self.exp_folder, exist_ok=True)
        self.log(f"Session folder: {self.exp_folder}")
        self.write_parameters_dat()
        self.trial_log_path = os.path.join(self.exp_folder, "TrialLog.csv")
        self.parameters_log_path = os.path.join(self.exp_folder, "Parameters.csv")

    def open_irfork_file(self):
        self.close_irfork_file()
        if not self.write_irfork_bin.get():
            return
        if not self.exp_folder:
            self.prepare_session_folder()
        self.irfork_file = open(os.path.join(self.exp_folder, "IRFork.bin"), "wb")
        self.soundcopy_file = open(os.path.join(self.exp_folder, "SoundCopy.bin"), "wb")
        self.log(f"Writing IRFork.bin and SoundCopy.bin: {self.exp_folder}")

    def close_irfork_file(self):
        if self.irfork_file is not None:
            self.irfork_file.close()
            self.irfork_file = None
            self.log("Closed IRFork.bin.")
        if self.soundcopy_file is not None:
            self.soundcopy_file.close()
            self.soundcopy_file = None
            self.log("Closed SoundCopy.bin.")

    def get_current_parameters(self):
        sequence_values = self.sequence_values.get().split()
        sequence_weights = self.sequence_weights.get().split()
        return {
            "UserName": self.user_name.get(),
            "MouseId": self.mouse_id.get(),
            "ProjectName": self.project_name.get(),
            "NICard_filename": self.ni_script.get().replace(os.sep, "/"),
            "Sound_filename": self.sound_file.get().replace(os.sep, "/"),
            "IRForkColumn": 1,
            "SoundCopyColumn": 2,
            "SimulationMode": int(self.simulation_mode.get()),
            "frec": self.rate_hz.get(),
            "bin": self.callback_s.get(),
            "TriggerTypeDropDown": self.trigger_type.get(),
            "OuputformatDropDown": self.output_format.get(),
            "TaskType": self.task_type.get(),
            "GoWeight": sequence_weights[0] if len(sequence_weights) > 0 else "",
            "NoGoWeight": sequence_weights[1] if len(sequence_weights) > 1 else "",
            "GoSoundId": sequence_values[0] if len(sequence_values) > 0 else "",
            "NoGoSoundId": sequence_values[1] if len(sequence_values) > 1 else "",
            "SoundLevel": self.sound_level.get(),
            "RandomSeed": self.random_seed.get(),
            "ITI_s": self.iti_s.get(),
            "ITIrandMin_s": self.iti_rand_min_s.get(),
            "ITIrandMax_s": self.iti_rand_max_s.get(),
            "Sounddelay_s": self.sound_delay_s.get(),
            "Delay_s": self.delay_s.get(),
            "SoundDuration_s": self.sound_duration_s.get(),
            "TrialDuration_s": self.trial_duration_s.get(),
            "ResponseWindow_s": self.response_window_s.get(),
            "RewardDelay_s": self.reward_delay_s.get(),
            "Rewardduration_ms": self.pulse_ms.get(),
            "HIT": self.hit_threshold_s.get(),
            "HITThreshold_percent": self.hit_threshold_s.get(),
            "PunishInterval": self.punish_interval.get(),
            "RewardGo": self.reward_go.get(),
            "RewardProb": self.reward_go.get(),
            "PunishNoGoFA": self.punish_no_go_fa.get(),
            "Minlickcount": self.min_lick_count.get(),
            "Lickthreshold": self.lick_threshold.get(),
            "LeverThreshold": self.threshold_v.get(),
            "LeverHoldTime_s": self.lever_hold_time_s.get(),
            "MaxTrials": self.max_trials.get(),
            "SampleSoundId": self.sample_sound_id.get(),
            "TestSoundId": self.test_sound_id.get(),
            "PlaySound": int(self.play_sound_on_crossing.get()),
            "TriggerOutput": int(self.trigger_output_on_crossing.get()),
        }

    def write_parameters_dat(self):
        keys = (
            "UserName",
            "MouseId",
            "ProjectName",
            "NICard_filename",
            "Sound_filename",
            "IRForkColumn",
            "SoundCopyColumn",
            "SimulationMode",
            "frec",
            "bin",
            "TriggerTypeDropDown",
            "OuputformatDropDown",
            "TaskType",
            "GoWeight",
            "NoGoWeight",
            "GoSoundId",
            "NoGoSoundId",
            "SampleSoundId",
            "TestSoundId",
            "SoundLevel",
            "RandomSeed",
            "ITI_s",
            "ITIrandMin_s",
            "ITIrandMax_s",
            "Sounddelay_s",
            "Delay_s",
            "SoundDuration_s",
            "TrialDuration_s",
            "ResponseWindow_s",
            "RewardDelay_s",
            "Rewardduration_ms",
            "HIT",
            "HITThreshold_percent",
            "PunishInterval",
            "RewardGo",
            "RewardProb",
            "PunishNoGoFA",
            "Minlickcount",
            "Lickthreshold",
            "LeverThreshold",
            "LeverHoldTime_s",
            "MaxTrials",
        )
        params = self.get_current_parameters()
        path = os.path.join(self.exp_folder, "parameters.dat")
        with open(path, "w", encoding="utf-8") as f:
            for key in keys:
                f.write(f"{key}={params[key]}\n")

    def create_trial(self, sound_id, trigger_time_s, threshold, iti):
        self.trial_index += 1
        trial_type_id, trial_type = self.classify_trial_sound(sound_id)
        timestamp = datetime.now().isoformat(timespec="milliseconds")
        rate = self.parse_float(self.rate_hz, 1000)
        trigger_sample = int(round(trigger_time_s * rate))
        trial_row = {
            "trial": self.trial_index,
            "timestamp": timestamp,
            "trigger_time_s": f"{trigger_time_s:.6f}",
            "trigger_sample": trigger_sample,
            "crossing_duration_s": "",
            "TrialType": f"{trial_type_id} {trial_type}",
            "HIT": "",
            "MISS": "",
            "CR": "",
            "FA": "",
            "ResultType": "",
            "sound_id": sound_id,
            "lick_count": "",
        }
        params = self.get_current_parameters()
        parameter_row = {
            "trial": self.trial_index,
            "timestamp": timestamp,
            "sound_id": sound_id,
            "trigger_time_s": f"{trigger_time_s:.6f}",
            "trigger_sample": trigger_sample,
            "task_type": params["TaskType"],
            "sample_sound_id": params["SampleSoundId"],
            "test_sound_id": params["TestSoundId"],
            "hit_threshold_percent": self.parse_float_value(params["HIT"], 50),
            "hit_threshold_s": self.get_hit_threshold_s(),
            "threshold_v": threshold,
            "lever_hold_time_s": self.parse_float_value(params["LeverHoldTime_s"], 1),
            "iti_s": iti,
            "iti_rand_min_s": params["ITIrandMin_s"],
            "iti_rand_max_s": params["ITIrandMax_s"],
            "sound_delay_s": self.parse_float_value(params["Sounddelay_s"], 0),
            "delay_s": self.parse_float_value(params["Delay_s"], 0),
            "sound_duration_s": params["SoundDuration_s"],
            "trial_duration_s": self.parse_float_value(params["TrialDuration_s"], 3),
            "response_window_s": self.parse_float_value(params["ResponseWindow_s"], 2),
            "reward_delay_s": self.parse_float_value(params["RewardDelay_s"], 0),
            "reward_duration_ms": self.parse_float_value(params["Rewardduration_ms"], 50),
            "punish_interval": params["PunishInterval"],
            "reward_go": params["RewardGo"],
            "reward_prob": params["RewardProb"],
            "punish_no_go_fa": params["PunishNoGoFA"],
            "min_lick_count": params["Minlickcount"],
            "lick_threshold": params["Lickthreshold"],
            "play_sound": params["PlaySound"],
            "trigger_output": params["TriggerOutput"],
            "Block": "",
        }
        parameter_row["Block"] = self.get_parameter_block_label(parameter_row)
        self.trial_rows.append(trial_row)
        self.parameter_rows.append(parameter_row)
        self.write_trial_log()
        self.write_parameters_csv()
        self.after(0, self.update_trial_display, sound_id, trial_type_id, trial_type)

    def draw_trial_iti_s(self):
        base_iti_s = max(0.0, self.parse_float(self.iti_s, 1))
        rand_min_s = max(0.0, self.parse_float(self.iti_rand_min_s, 0))
        rand_max_s = max(0.0, self.parse_float(self.iti_rand_max_s, 0))
        if rand_max_s < rand_min_s:
            rand_min_s, rand_max_s = rand_max_s, rand_min_s
        return base_iti_s + random.uniform(rand_min_s, rand_max_s)

    def start_active_trial(self, trigger_time_s, iti_s):
        response_window_s = max(0.0, self.parse_float(self.response_window_s, 2))
        self.active_trial_index = self.trial_index
        self.active_trial_start_s = trigger_time_s
        self.active_trial_end_s = trigger_time_s + response_window_s
        self.active_high_start_s = trigger_time_s
        self.active_crossing_total_s = 0.0
        self.active_lick_count = 0
        self.active_reward_decided = False
        self.active_trial_base_iti_s = iti_s
        self.active_trial_extra_timeout_s = 0.0
        self.next_trial_allowed_time_s = trigger_time_s + iti_s
        self.start_trial_state_interval(trigger_time_s)

    def start_active_dmts_trial(self, trigger_time_s, iti_s):
        sound_duration_s = max(0.0, self.parse_float(self.sound_duration_s, 0))
        delay_s = max(0.0, self.parse_float(self.delay_s, 0))
        response_window_s = max(0.0, self.parse_float(self.response_window_s, 2))
        reward_delay_s = max(0.0, self.parse_float(self.reward_delay_s, 0))
        reward_duration_s = max(0.0, self.parse_float(self.pulse_ms, 50) / 1000.0)
        self.active_trial_index = self.trial_index
        self.active_trial_start_s = trigger_time_s
        self.active_dmts_response_start_s = trigger_time_s + sound_duration_s + delay_s + sound_duration_s
        self.active_dmts_response_end_s = self.active_dmts_response_start_s + response_window_s
        self.active_dmts_reward_start_s = self.active_dmts_response_end_s + reward_delay_s
        self.active_trial_end_s = self.active_dmts_reward_start_s + reward_duration_s
        self.active_high_start_s = None
        self.active_crossing_total_s = 0.0
        self.active_lick_count = 0
        self.active_reward_decided = False
        self.active_trial_base_iti_s = iti_s
        self.active_trial_extra_timeout_s = 0.0
        self.active_dmts_sample_sound_id = max(1, self.parse_int(self.sample_sound_id, 1))
        self.active_dmts_test_sound_id = max(1, self.parse_int(self.test_sound_id, 2))
        self.active_dmts_test_sound_time_s = trigger_time_s + sound_duration_s + delay_s
        self.active_dmts_response_evaluated = False
        self.active_dmts_response_met = False
        self.active_dmts_test_sound_played = False
        self.active_dmts_response_started = False
        self.active_dmts_scored = False
        self.next_trial_allowed_time_s = trigger_time_s + iti_s
        self.start_trial_state_interval(trigger_time_s)
        if self.play_sound_on_crossing.get():
            self.play_loaded_sound(sound_id=self.active_dmts_sample_sound_id, from_worker=True, start_s=trigger_time_s)

    def is_lever_task(self):
        return self.task_type.get().strip().lower() == "lever"

    def is_dmts_task(self):
        return self.task_type.get().strip().lower() == "dmts"

    def is_lick_trigger(self):
        return self.trigger_type.get().strip().lower() == "lick"

    def get_current_trigger_threshold(self):
        if self.is_lick_trigger():
            return self.parse_float(self.lick_threshold, self.parse_float(self.threshold_v, 1))
        return self.parse_float(self.threshold_v, 1)

    def get_min_lick_count(self):
        return max(1, self.parse_int(self.min_lick_count, 1))

    def check_lever_trigger_sample(self, sample_time_s, value, threshold):
        is_high = value >= threshold
        crossed_up = is_high and not self.irfork_was_high
        crossed_down = not is_high and self.irfork_was_high
        self.irfork_was_high = is_high

        if self.active_trial_index is not None:
            if is_high:
                self.active_lever_low_start_s = None
                self.evaluate_active_lever_trial(sample_time_s)
            elif crossed_down:
                self.active_lever_low_start_s = sample_time_s
            elif self.active_lever_low_start_s is not None:
                low_duration_s = sample_time_s - self.active_lever_low_start_s
                if low_duration_s >= self.get_lever_release_debounce_s():
                    self.finish_active_lever_trial(self.active_lever_low_start_s, success=False)
            return

        if not crossed_up:
            return

        if sample_time_s < self.next_trial_allowed_time_s:
            return

        max_trials = max(0, self.parse_int(self.max_trials, 0))
        if max_trials and self.trial_index >= max_trials:
            self.plot_queue.put(("log", f"Accepted lever press ignored: max trials {max_trials} reached."))
            return

        sound_id = self.parse_int(self.sound_id, 1)
        iti = self.draw_trial_iti_s()
        self.create_trial(sound_id, sample_time_s, threshold, iti)
        self.start_active_lever_trial(sample_time_s, iti)
        self.play_next_lever_sound(sample_time_s)
        self.last_trigger_time = sample_time_s
        self.plot_queue.put(("log", f"Lever crossed {threshold:g} V. Trial {self.trial_index} started; hold for {self.get_lever_hold_time_s():g} s."))
        self.evaluate_active_lever_trial(sample_time_s)

    def update_active_dmts_trial(self, sample_time_s, is_high, crossed_up, crossed_down):
        if crossed_down and not self.is_lick_trigger() and not self.active_dmts_scored:
            self.finish_active_dmts_miss(sample_time_s, "fork event ended")
            return

        if self.active_dmts_test_sound_time_s is not None and not self.active_dmts_test_sound_played:
            if sample_time_s >= self.active_dmts_test_sound_time_s:
                if self.play_sound_on_crossing.get():
                    self.play_loaded_sound(
                        sound_id=self.active_dmts_test_sound_id,
                        from_worker=True,
                        start_s=self.active_dmts_test_sound_time_s,
                    )
                self.active_dmts_test_sound_played = True

        response_start_s = self.active_dmts_response_start_s
        if response_start_s is None or sample_time_s < response_start_s:
            return

        response_end_s = self.active_dmts_response_end_s
        if response_end_s is not None and sample_time_s >= response_end_s:
            self.finish_active_dmts_response(response_end_s)
            reward_start_s = self.active_dmts_reward_start_s
            if reward_start_s is not None and sample_time_s >= reward_start_s:
                self.finish_active_dmts_reward_period(reward_start_s)
            return

        if not self.active_dmts_response_started:
            self.active_dmts_response_started = True
            if is_high and not self.is_lick_trigger():
                self.active_high_start_s = response_start_s

        if self.is_lick_trigger():
            if crossed_up:
                self.add_active_lick()
        elif crossed_up:
            self.active_high_start_s = sample_time_s
        elif crossed_down:
            self.add_active_high_interval(sample_time_s)

    def finish_active_dmts_response(self, response_end_s):
        if self.active_dmts_response_evaluated:
            return
        row = self.get_active_trial_row()
        if row is None:
            self.active_dmts_response_evaluated = True
            return
        self.active_dmts_response_evaluated = True
        if self.is_lick_trigger():
            lick_count = self.active_lick_count
            row["lick_count"] = lick_count
            response_met = lick_count >= self.get_min_lick_count()
            measure = float(lick_count)
            log_measure = f"{lick_count} licks"
        else:
            if self.active_high_start_s is not None:
                self.add_active_high_interval(response_end_s)
            measure = self.active_crossing_total_s
            row["crossing_duration_s"] = f"{measure:.6f}"
            response_met = measure >= self.get_hit_threshold_s()
            log_measure = f"{measure:.3f} s total IR crossing"
        self.active_dmts_response_met = response_met
        self.write_trial_log()
        self.plot_queue.put(("log", f"DMTS trial {row['trial']} response window ended with {log_measure}. Criterion met={int(response_met)}."))

    def finish_active_dmts_reward_period(self, reward_start_s):
        if self.active_dmts_scored:
            return
        row = self.get_active_trial_row()
        if row is None:
            self.clear_active_trial()
            return
        if not self.active_dmts_response_evaluated:
            self.finish_active_dmts_response(self.active_dmts_response_end_s or reward_start_s)
        self.active_dmts_scored = True
        same_sound = self.active_dmts_sample_sound_id == self.active_dmts_test_sound_id
        hit = bool(same_sound and self.active_dmts_response_met)
        row["HIT"] = int(hit)
        row["MISS"] = int(not hit)
        row["CR"] = 0
        row["FA"] = 0
        row["ResultType"] = "HIT" if hit else "MISS"
        if hit:
            measure = float(row.get("lick_count") or self.active_crossing_total_s)
            self.maybe_send_go_reward(row, measure, start_s=reward_start_s)
        self.write_trial_log()
        self.plot_queue.put(("results", None))
        self.plot_queue.put(("log", f"DMTS trial {row['trial']} reached reward period. Same sound={int(same_sound)}. Result={row['ResultType']}."))

    def finish_active_dmts_miss(self, trial_end_s, reason):
        row = self.get_active_trial_row()
        if row is None:
            self.clear_active_trial()
            return
        self.active_dmts_scored = True
        if self.active_high_start_s is not None:
            self.add_active_high_interval(trial_end_s)
        row["crossing_duration_s"] = f"{self.active_crossing_total_s:.6f}"
        row["HIT"] = 0
        row["MISS"] = 1
        row["CR"] = 0
        row["FA"] = 0
        row["ResultType"] = "MISS"
        self.write_trial_log()
        self.plot_queue.put(("results", None))
        self.plot_queue.put(("log", f"DMTS trial {row['trial']} stopped: {reason}. Result=MISS."))
        self.end_trial_state_interval(trial_end_s)
        self.clear_active_trial()

    def finish_active_dmts_timeline(self, trial_end_s):
        if not self.active_dmts_scored:
            reward_start_s = self.active_dmts_reward_start_s or trial_end_s
            self.finish_active_dmts_reward_period(reward_start_s)
        self.write_trial_log()
        self.plot_queue.put(("results", None))
        self.end_trial_state_interval(trial_end_s)
        self.clear_active_trial()

    def start_active_lever_trial(self, trigger_time_s, iti_s):
        self.active_trial_index = self.trial_index
        self.active_trial_start_s = trigger_time_s
        self.active_trial_end_s = None
        self.active_high_start_s = trigger_time_s
        self.active_crossing_total_s = 0.0
        self.active_lick_count = 0
        self.active_reward_decided = False
        self.active_trial_base_iti_s = iti_s
        self.active_trial_extra_timeout_s = 0.0
        self.active_lever_sound_id = self.parse_int(self.sound_id, 1)
        self.active_lever_next_sound_time_s = trigger_time_s
        self.active_lever_low_start_s = None
        self.next_trial_allowed_time_s = trigger_time_s + iti_s
        self.start_trial_state_interval(trigger_time_s)

    def start_trial_state_interval(self, start_s):
        self.trial_state_intervals.append([start_s, None])
        window = max(1, self.parse_float(self.window_s, 10))
        oldest = start_s - window * 2
        while self.trial_state_intervals and self.trial_state_intervals[0][1] is not None and self.trial_state_intervals[0][1] < oldest:
            self.trial_state_intervals.pop(0)

    def end_trial_state_interval(self, end_s):
        for interval in reversed(self.trial_state_intervals):
            if interval[1] is None:
                interval[1] = end_s
                break

    def get_lever_hold_time_s(self):
        return max(0.0, self.parse_float(self.lever_hold_time_s, 1))

    def get_lever_release_debounce_s(self):
        return 0.05

    def play_next_lever_sound(self, sample_time_s):
        if not self.play_sound_on_crossing.get():
            return
        if self.active_lever_next_sound_time_s is None:
            return
        if sample_time_s < self.active_lever_next_sound_time_s:
            return
        sound_id = max(1, self.active_lever_sound_id)
        duration_s = self.play_loaded_sound(sound_id=sound_id, from_worker=True, start_s=sample_time_s)
        if duration_s is None:
            self.active_lever_next_sound_time_s = None
            return
        self.active_lever_sound_id = sound_id + 1
        self.active_lever_next_sound_time_s = sample_time_s + max(0.0, duration_s) + self.lever_sound_gap_s

    def evaluate_active_lever_trial(self, sample_time_s):
        row = self.get_active_trial_row()
        if row is None or self.active_high_start_s is None:
            return
        self.play_next_lever_sound(sample_time_s)
        hold_s = max(0.0, sample_time_s - self.active_high_start_s)
        row["crossing_duration_s"] = f"{hold_s:.6f}"
        if hold_s >= self.get_lever_hold_time_s() and not row["HIT"]:
            row["HIT"] = 1
            row["MISS"] = 0
            row["CR"] = 0
            row["FA"] = 0
            row["ResultType"] = "HIT"
            self.maybe_send_go_reward(row, hold_s, start_s=sample_time_s)
            self.write_trial_log()
            self.plot_queue.put(("results", None))

    def finish_active_lever_trial(self, trial_end_s, success):
        row = self.get_active_trial_row()
        if row is None:
            self.clear_active_trial()
            return
        hold_s = 0.0
        if self.active_high_start_s is not None:
            hold_s = max(0.0, trial_end_s - self.active_high_start_s)
        success = bool(success or row["HIT"])
        row["crossing_duration_s"] = f"{hold_s:.6f}"
        row["HIT"] = int(success)
        row["MISS"] = int(not success)
        row["CR"] = 0
        row["FA"] = 0
        row["ResultType"] = "HIT" if success else "MISS"
        if success:
            self.maybe_send_go_reward(row, hold_s, start_s=trial_end_s)
        self.apply_trial_timeout(row)
        self.write_trial_log()
        self.plot_queue.put(("results", None))
        self.plot_queue.put(("log", f"Lever trial {row['trial']} hold time was {hold_s:.3f} s. Result={row['ResultType']}."))
        self.end_trial_state_interval(trial_end_s)
        self.clear_active_trial()

    def write_trial_log(self):
        self.write_csv(self.trial_log_path, self.trial_rows)

    def write_csv(self, path, rows):
        if not path or not rows:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def get_parameter_block_label(self, parameter_row=None):
        if parameter_row is None:
            return f"block{max(1, self.parameter_block_index)}"
        signature = tuple(
            (key, parameter_row[key])
            for key in parameter_row
            if key not in ("Block", "trial", "timestamp", "sound_id", "trigger_time_s", "trigger_sample", "iti_s")
        )
        if self.current_parameter_signature != signature:
            self.parameter_block_index += 1
            self.current_parameter_signature = signature
        return f"block{self.parameter_block_index}"

    def write_parameters_csv(self):
        self.write_csv(self.parameters_log_path, self.parameter_rows)

    def add_active_lick(self):
        self.active_lick_count += 1
        row = self.get_active_trial_row()
        if row is not None:
            row["lick_count"] = self.active_lick_count

    def add_active_high_interval(self, crossing_end_s):
        if self.active_high_start_s is None:
            return
        self.active_crossing_total_s += max(0.0, crossing_end_s - self.active_high_start_s)
        self.active_high_start_s = None

    def get_active_crossing_total(self, sample_time_s):
        total_s = self.active_crossing_total_s
        if self.active_high_start_s is not None:
            total_s += max(0.0, sample_time_s - self.active_high_start_s)
        return total_s

    def get_hit_threshold_s(self):
        response_window_s = max(0.0, self.parse_float(self.response_window_s, 2))
        raw_value = max(0.0, self.parse_float(self.hit_threshold_s, 50))
        if raw_value <= 1.0:
            return raw_value
        return response_window_s * min(raw_value, 100.0) / 100.0

    def evaluate_active_trial(self, sample_time_s):
        row = self.get_active_trial_row()
        if row is None:
            return
        if self.is_lick_trigger():
            self.evaluate_active_lick_trial(row)
            return
        hit_threshold_s = self.get_hit_threshold_s()
        total_s = self.get_active_crossing_total(sample_time_s)
        row["crossing_duration_s"] = f"{total_s:.6f}"
        is_dmts = row["TrialType"].endswith("DMTS")
        is_go = row["TrialType"].endswith("GO")
        is_nogo = row["TrialType"].endswith("noGo")
        if (is_go or is_dmts) and total_s >= hit_threshold_s and not row["HIT"]:
            row["HIT"] = 1
            row["MISS"] = 0
            row["CR"] = 0
            row["FA"] = 0
            row["ResultType"] = "HIT"
            self.maybe_send_go_reward(row, total_s, start_s=sample_time_s)
            self.write_trial_log()
        elif is_nogo and total_s >= hit_threshold_s and not row["FA"]:
            row["HIT"] = 0
            row["MISS"] = 0
            row["CR"] = 0
            row["FA"] = 1
            row["ResultType"] = "FA"
            self.write_trial_log()

    def evaluate_active_lick_trial(self, row):
        row["lick_count"] = self.active_lick_count
        min_lick_count = self.get_min_lick_count()
        is_dmts = row["TrialType"].endswith("DMTS")
        is_go = row["TrialType"].endswith("GO")
        is_nogo = row["TrialType"].endswith("noGo")
        if (is_go or is_dmts) and self.active_lick_count >= min_lick_count and not row["HIT"]:
            row["HIT"] = 1
            row["MISS"] = 0
            row["CR"] = 0
            row["FA"] = 0
            row["ResultType"] = "HIT"
            self.maybe_send_go_reward(row, float(self.active_lick_count), start_s=self.active_trial_start_s)
            self.write_trial_log()
        elif is_nogo and self.active_lick_count >= min_lick_count and not row["FA"]:
            row["HIT"] = 0
            row["MISS"] = 0
            row["CR"] = 0
            row["FA"] = 1
            row["ResultType"] = "FA"
            self.write_trial_log()

    def finish_active_trial(self, trial_end_s):
        row = self.get_active_trial_row()
        if row is None:
            self.clear_active_trial()
            return
        if self.is_lick_trigger():
            self.finish_active_lick_trial(row, trial_end_s)
            return
        if self.active_high_start_s is not None:
            self.add_active_high_interval(trial_end_s)
        hit_threshold_s = self.get_hit_threshold_s()
        total_s = self.active_crossing_total_s
        row["crossing_duration_s"] = f"{total_s:.6f}"
        is_dmts = row["TrialType"].endswith("DMTS")
        is_go = row["TrialType"].endswith("GO")
        is_nogo = row["TrialType"].endswith("noGo")
        if is_go or is_dmts:
            row["HIT"] = int(total_s >= hit_threshold_s)
            row["MISS"] = int(total_s < hit_threshold_s)
            row["CR"] = 0
            row["FA"] = 0
            row["ResultType"] = "HIT" if row["HIT"] else "MISS"
            if row["HIT"]:
                self.maybe_send_go_reward(row, total_s, start_s=trial_end_s)
        elif is_nogo:
            row["HIT"] = 0
            row["MISS"] = 0
            row["CR"] = int(total_s < hit_threshold_s)
            row["FA"] = int(total_s >= hit_threshold_s)
            row["ResultType"] = "CR" if row["CR"] else "FA"
            if row["FA"]:
                self.active_trial_extra_timeout_s = self.get_punish_no_go_fa_s()
        self.apply_trial_timeout(row)
        self.write_trial_log()
        self.plot_queue.put(("results", None))
        result = f", {row['ResultType']}" if row["ResultType"] else ""
        self.plot_queue.put(("log", f"Trial {row['trial']} total IR crossing time was {total_s:.3f} s. HIT={row['HIT']}{result}."))
        self.end_trial_state_interval(trial_end_s)
        self.clear_active_trial()

    def finish_active_lick_trial(self, row, trial_end_s):
        min_lick_count = self.get_min_lick_count()
        lick_count = self.active_lick_count
        row["lick_count"] = lick_count
        is_dmts = row["TrialType"].endswith("DMTS")
        is_go = row["TrialType"].endswith("GO")
        is_nogo = row["TrialType"].endswith("noGo")
        if is_go or is_dmts:
            row["HIT"] = int(lick_count >= min_lick_count)
            row["MISS"] = int(lick_count < min_lick_count)
            row["CR"] = 0
            row["FA"] = 0
            row["ResultType"] = "HIT" if row["HIT"] else "MISS"
            if row["HIT"]:
                self.maybe_send_go_reward(row, float(lick_count), start_s=trial_end_s)
        elif is_nogo:
            row["HIT"] = 0
            row["MISS"] = 0
            row["CR"] = int(lick_count < min_lick_count)
            row["FA"] = int(lick_count >= min_lick_count)
            row["ResultType"] = "CR" if row["CR"] else "FA"
            if row["FA"]:
                self.active_trial_extra_timeout_s = self.get_punish_no_go_fa_s()
        self.apply_trial_timeout(row)
        self.write_trial_log()
        self.plot_queue.put(("results", None))
        result = f", {row['ResultType']}" if row["ResultType"] else ""
        self.plot_queue.put(("log", f"Trial {row['trial']} lick count was {lick_count}. HIT={row['HIT']}{result}."))
        self.end_trial_state_interval(trial_end_s)
        self.clear_active_trial()

    def get_punish_no_go_fa_s(self):
        return min(10.0, max(0.0, self.parse_float(self.punish_no_go_fa, 0)))

    def apply_trial_timeout(self, row):
        if row["TrialType"].endswith("noGo") and row["ResultType"] == "FA":
            self.active_trial_extra_timeout_s = self.get_punish_no_go_fa_s()
        else:
            self.active_trial_extra_timeout_s = 0.0
        total_timeout_s = self.active_trial_base_iti_s + self.active_trial_extra_timeout_s
        if self.last_trigger_time > -1e11:
            self.next_trial_allowed_time_s = self.last_trigger_time + total_timeout_s
        if self.active_trial_extra_timeout_s:
            self.plot_queue.put((
                "log",
                f"noGo FA timeout added: {self.active_trial_extra_timeout_s:g} s. "
                f"Next trial allowed after {total_timeout_s:g} s from trial start.",
            ))

    def maybe_send_go_reward(self, row, total_s, start_s=None):
        if self.active_reward_decided:
            return
        self.active_reward_decided = True
        reward_probability = min(1.0, max(0.0, self.parse_float(self.reward_go, 1.0)))
        draw = random.random()
        measure = f"{int(total_s)} licks" if self.is_lick_trigger() else f"{total_s:.3f} s total IR crossing"
        if draw <= reward_probability and self.trigger_output_on_crossing.get():
            self.send_output_pulse(from_worker=True, start_s=start_s)
            self.plot_queue.put((
                "log",
                f"Trial {row['trial']} reached HIT threshold with {measure}. "
                f"Reward sent, p={reward_probability:.3f}, draw={draw:.3f}.",
            ))
        else:
            self.plot_queue.put((
                "log",
                f"Trial {row['trial']} reached HIT threshold with {measure}. "
                f"Reward skipped, p={reward_probability:.3f}, draw={draw:.3f}.",
            ))

    def get_active_trial_row(self):
        if self.active_trial_index is None:
            return None
        for row in reversed(self.trial_rows):
            if row["trial"] == self.active_trial_index:
                return row
        return None

    def clear_active_trial(self):
        self.active_trial_index = None
        self.active_trial_start_s = None
        self.active_trial_end_s = None
        self.active_high_start_s = None
        self.active_crossing_total_s = 0.0
        self.active_lick_count = 0
        self.active_reward_decided = False
        self.active_trial_base_iti_s = 0.0
        self.active_trial_extra_timeout_s = 0.0
        self.active_lever_sound_id = 1
        self.active_lever_next_sound_time_s = None
        self.active_lever_low_start_s = None
        self.active_dmts_sample_sound_id = 1
        self.active_dmts_test_sound_id = 2
        self.active_dmts_test_sound_time_s = None
        self.active_dmts_response_start_s = None
        self.active_dmts_response_end_s = None
        self.active_dmts_reward_start_s = None
        self.active_dmts_response_evaluated = False
        self.active_dmts_response_met = False
        self.active_dmts_test_sound_played = False
        self.active_dmts_response_started = False
        self.active_dmts_scored = False

    def classify_trial_sound(self, sound_id):
        if self.is_lever_task():
            return 1, "Lever"
        if self.is_dmts_task():
            return 1, "DMTS"
        values = self._parse_number_list(self.sequence_values.get(), default=[sound_id], cast=int)
        if not values or sound_id == values[0]:
            return 1, "GO"
        if len(values) > 1 and sound_id == values[1]:
            return 2, "noGo"
        return 0, "unknown"

    def update_trial_display(self, sound_id, trial_type_id, trial_type):
        self.current_trial_var.set(str(self.trial_index))
        self.last_trial_sound_var.set(str(sound_id))
        self.last_trial_type_var.set(f"{trial_type_id} {trial_type}")

    def send_output_pulse(self, from_worker=False, start_s=None):
        pulse_s = max(0, self.parse_float(self.pulse_ms, 50) / 1000.0)
        self.record_trigger_pulse(pulse_s, start_s=start_s)
        try:
            if self.reward_task is None and nidaqmx is not None:
                self.setup_tasks()
            if self.reward_task is not None:
                self.reward_task.write(True)
                time.sleep(pulse_s)
                self.reward_task.write(False)
                msg = f"Output pulse sent for {pulse_s * 1000:g} ms."
            else:
                msg = "Output pulse simulated; nidaqmx is not available."
        except Exception as exc:
            msg = f"Output pulse error: {exc}"
        if from_worker:
            self.plot_queue.put(("log", msg))
        else:
            self.log(msg)

    def record_trigger_pulse(self, pulse_s, start_s=None):
        if self.acq_start_perf is None:
            return
        if start_s is None:
            start_s = time.perf_counter() - self.acq_start_perf
        end_s = start_s + pulse_s
        self.trigger_pulses.append((start_s, end_s))
        self.full_trigger_pulses.append((start_s, end_s))
        window = max(1, self.parse_float(self.window_s, 10))
        oldest = start_s - window * 2
        while self.trigger_pulses and self.trigger_pulses[0][1] < oldest:
            self.trigger_pulses.pop(0)

    def load_sound_file(self):
        if loadmat is None:
            self.log("Cannot load sound: scipy.io.loadmat is unavailable.")
            return False
        path = self.sound_file.get()
        if not os.path.exists(path):
            self.log(f"Sound file not found: {path}")
            return False
        try:
            data = loadmat(path, squeeze_me=True, struct_as_record=False)
            self.sound_data = data["Sound"]
            self.sound_loaded = True
            self.log(f"Loaded sound file: {path}")
            return True
        except Exception as exc:
            self.log(f"Sound load error: {exc}")
            return False

    def get_sound_by_id(self, sound_id):
        if not self.sound_loaded and not self.load_sound_file():
            return None
        sound = self.sound_data
        try:
            if np is not None:
                arr = np.asarray(sound, dtype=object)
                if arr.dtype == object:
                    selected = arr.flat[sound_id - 1]
                elif arr.ndim == 1:
                    selected = arr
                else:
                    selected = arr[:, sound_id - 1]
                selected = np.asarray(selected, dtype=float).reshape(-1)
                return selected * self.parse_float(self.sound_level, 1)
        except Exception:
            pass
        self.log("Could not extract selected sound from MAT file.")
        return None

    def play_loaded_sound(self, use_sequence=False, from_worker=False, sound_id=None, start_s=None):
        if sound_id is None:
            sound_id = self.consume_next_sound_id() if use_sequence else self.parse_int(self.sound_id, 1)
        signal = self.get_sound_by_id(sound_id)
        if signal is None:
            return None
        fs = 192000
        duration_s = len(signal) / fs if len(signal) else 0.0
        msg = f"Played sound id {sound_id}."
        try:
            self.record_sound_output(signal, fs, sound_id, start_s=start_s)
            if nidaqmx is not None:
                self.play_sound_on_ni(signal, fs)
            elif sd is not None:
                sd.play(signal, fs, blocking=False)
            else:
                msg = f"Sound id {sound_id} selected; no NI or sounddevice playback backend is available."
        except Exception as exc:
            msg = f"Sound playback error: {exc}"
            duration_s = None
        if from_worker:
            self.plot_queue.put(("log", msg))
        else:
            self.log(msg)
        return duration_s

    def record_sound_output(self, signal, fs, sound_id=None, start_s=None):
        if self.acq_start_perf is None:
            return
        if start_s is None:
            start_s = time.perf_counter() - self.acq_start_perf
        values = signal.tolist() if hasattr(signal, "tolist") else list(signal)
        self.sound_outputs.append((start_s, fs, values, sound_id))
        self.full_sound_outputs.append((start_s, fs, values, sound_id))
        window = max(1, self.parse_float(self.window_s, 10))
        oldest = start_s - window * 2
        while self.sound_outputs:
            first_start, first_fs, first_values = self.sound_outputs[0][:3]
            first_end = first_start + len(first_values) / first_fs
            if first_end >= oldest:
                break
            self.sound_outputs.pop(0)

    def play_sound_on_ni(self, signal, fs):
        device = self.device.get().strip() or "Dev1"
        task = nidaqmx.Task()
        try:
            task.ao_channels.add_ao_voltage_chan(f"{device}/ao0")
            task.timing.cfg_samp_clk_timing(fs, sample_mode=AcquisitionType.FINITE, samps_per_chan=len(signal))
            values = signal.tolist() if hasattr(signal, "tolist") else list(signal)
            task.write(values, auto_start=False)
            task.start()
            task.wait_until_done(timeout=max(2.0, len(values) / fs + 1.0))
            task.stop()
        finally:
            task.close()

    def generate_sequence(self, log=True):
        length = max(1, self.parse_int(self.sequence_length, 300))
        values = self._parse_number_list(self.sequence_values.get(), default=[1, 10], cast=int)
        weights = self._parse_number_list(self.sequence_weights.get(), default=[0.5, 0.5], cast=float)
        if len(weights) != len(values) or sum(weights) <= 0:
            weights = [1.0 / len(values)] * len(values)
            self.sequence_weights.set(" ".join(str(w) for w in weights))
        rng = random
        seed_text = self.random_seed.get().strip() if hasattr(self, "random_seed") else ""
        if seed_text:
            try:
                seed = int(float(seed_text))
            except Exception:
                seed = seed_text
            rng = random.Random(seed)
        self.sound_sequence = rng.choices(values, weights=weights, k=length)
        self.sound_sequence_index = 0
        self.update_sequence_display()
        if log:
            self.log(f"Generated sound sequence: {length} entries from {values}.")

    def _parse_number_list(self, text, default, cast):
        try:
            values = [cast(item) for item in text.replace(",", " ").split()]
            return values or list(default)
        except Exception:
            return list(default)

    def update_sequence_display(self):
        if not self.sound_sequence:
            self.sequence_index_var.set("0")
            self.sequence_next_var.set(self.sound_id.get())
            return
        self.sequence_index_var.set(str(self.sound_sequence_index + 1))
        next_id = self.sound_sequence[self.sound_sequence_index]
        self.sequence_next_var.set(str(next_id))
        self.sound_id.set(str(next_id))

    def consume_next_sound_id(self):
        if not self.sound_sequence:
            self.generate_sequence(log=False)
        sound_id = self.sound_sequence[self.sound_sequence_index]
        self.sound_sequence_index += 1
        if self.sound_sequence_index >= len(self.sound_sequence):
            self.sound_sequence_index = 0
            self.plot_queue.put(("log", "Sound sequence wrapped to the beginning."))
        self.after(0, self.update_sequence_display)
        return sound_id

    def open_bin(self):
        path = filedialog.askopenfilename(initialdir=self.save_root.get(), filetypes=[("BIN files", "*.bin"), ("All files", "*.*")])
        if not path:
            return
        with open(path, "rb") as f:
            data_bytes = f.read()
        count = len(data_bytes) // 8
        values = list(struct.unpack(f"{count}d", data_bytes[: count * 8]))
        rate = self.read_rate_from_parameters(os.path.dirname(path))
        times = [i / rate for i in range(len(values))]
        self.time_buffer = times
        self.data_buffer = values
        self.current_ir_baseline = statistics.median(values) if self.subtract_baseline.get() and values else 0.0
        self.draw_plot(times, values)
        self.log(f"Opened {os.path.basename(path)}: {len(values)} samples at {rate:g} Hz.")

    def read_rate_from_parameters(self, folder):
        rate = self.parse_float(self.rate_hz, 1000)
        path = os.path.join(folder, "parameters.dat")
        if not os.path.exists(path):
            return rate
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("frec="):
                    try:
                        rate = float(line.split("=", 1)[1].strip())
                        self.rate_hz.set(str(rate))
                    except Exception:
                        pass
        return rate

    def save_nwb_placeholder(self):
        self.save_nwb(silent=False)

    def save_nwb(self, silent=False):
        if self.nwb_saving:
            msg = "NWB save is already in progress."
            if silent:
                self.log(msg)
            else:
                messagebox.showwarning("Save NWB", msg)
            return False

        if NWBFile is None or NWBHDF5IO is None or TimeSeries is None:
            msg = "Cannot save NWB: pynwb is not installed. Install it with pip install pynwb."
            if silent:
                self.log(msg)
            else:
                messagebox.showerror("Save NWB", msg)
            return False
        if h5py is None:
            msg = "Cannot save GUI-compatible NWB: h5py is not installed. Install it with pip install h5py."
            if silent:
                self.log(msg)
            else:
                messagebox.showerror("Save NWB", msg)
            return False
        if not self.exp_folder:
            msg = "No session folder is available yet. Start acquisition or open a saved session first."
            if silent:
                self.log(msg)
            else:
                messagebox.showwarning("Save NWB", msg)
            return False

        irfork_path = os.path.join(self.exp_folder, "IRFork.bin")
        if not os.path.exists(irfork_path):
            msg = f"Cannot save NWB: IRFork.bin was not found in {self.exp_folder}."
            if silent:
                self.log(msg)
            else:
                messagebox.showwarning("Save NWB", msg)
            return False

        data = self.read_irfork_binary(irfork_path)
        if len(data) == 0:
            msg = "Cannot save NWB: IRFork.bin contains no samples."
            if silent:
                self.log(msg)
            else:
                messagebox.showwarning("Save NWB", msg)
            return False

        rate = self.read_rate_from_parameters(self.exp_folder)
        identifier = self.safe_filename_component(
            f"{self.user_name.get()}_M{self.mouse_id.get()}_{os.path.basename(self.exp_folder)}"
        )
        nwb_path = os.path.join(self.exp_folder, f"{identifier}.nwb")
        nwbfile = NWBFile(
            session_description=f"BASIL acquisition for {self.project_name.get()}",
            identifier=identifier,
            session_start_time=datetime.now(timezone.utc).astimezone(),
        )
        nwbfile.add_acquisition(
            TimeSeries(
                name="IRFork",
                data=data,
                unit="volts",
                starting_time=0.0,
                rate=rate,
                description="IR fork analog input saved from IRFork.bin.",
            )
        )
        trigger_trace = self.build_trigger_trace(len(data), rate)
        nwbfile.add_acquisition(
            TimeSeries(
                name="Reward",
                data=trigger_trace,
                unit="volts",
                starting_time=0.0,
                rate=rate,
                description="Commanded reward/trigger digital output represented as a 0 to 5 V trace.",
            )
        )
        sound_epochs = self.build_contract_sound_epochs(len(data), rate)
        export_trial_rows = self.get_nwb_contract_trial_rows(len(data), rate, sound_epochs)
        trial_type_trace = self.build_contract_trial_type_trace(len(data), rate, export_trial_rows, sound_epochs)
        nwbfile.add_acquisition(
            TimeSeries(
                name="TrialType",
                data=trial_type_trace,
                unit="marker",
                starting_time=0.0,
                rate=10.0,
                description="Behavior GUI compatibility marker trace; value 99 marks trial anchors at 100 ms bins.",
            )
        )
        sound_copy, which_sound = self.build_contract_sound_traces(len(data), rate, sound_epochs)
        recorded_soundcopy = self.get_recorded_soundcopy_trace(len(data))
        if recorded_soundcopy is not None:
            sound_copy = recorded_soundcopy
        nwbfile.add_stimulus(
            TimeSeries(
                name="SoundCopy",
                data=sound_copy,
                unit="volts",
                starting_time=0.0,
                rate=rate,
                description="Continuous sound copy trace for behavior GUI compatibility; uses recorded NI SoundCopy when available.",
            )
        )
        nwbfile.add_stimulus(
            TimeSeries(
                name="WhichSound",
                data=which_sound,
                unit="sound_id",
                starting_time=0.0,
                rate=rate,
                description="Continuous encoded sound identity trace for behavior GUI compatibility.",
            )
        )
        tmp_path = os.path.join(self.exp_folder, f".{identifier}.tmp.nwb")
        try:
            self.nwb_saving = True
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            with NWBHDF5IO(tmp_path, "w") as io:
                io.write(nwbfile)
            self.write_nwb_contract_hdf5(tmp_path, rate, export_trial_rows)
            self.validate_nwb_contract_hdf5(tmp_path)
            os.replace(tmp_path, nwb_path)
        except Exception as exc:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            msg = f"Could not save NWB file: {exc}"
            self.log(msg)
            if not silent:
                messagebox.showerror("Save NWB", msg)
            return False
        finally:
            self.nwb_saving = False

        msg = f"Saved NWB file: {nwb_path}"
        self.log(msg)
        if not silent:
            messagebox.showinfo("Save NWB", msg)
        return True

    def safe_filename_component(self, text):
        cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(text)).strip(" .")
        return cleaned or "BASIL_session"

    def write_nwb_contract_hdf5(self, path, rate, trial_rows):
        utf8 = h5py.string_dtype(encoding="utf-8")
        created_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        with h5py.File(path, "a") as h5f:
            self.replace_hdf5_dataset(h5f, "file_create_date", [created_at], dtype=utf8)

            trials = h5f.require_group("intervals").require_group("trials")
            trial_ids = [int(row.get("trial", index + 1)) for index, row in enumerate(trial_rows)]
            sound_ids = [int(row.get("sound_id", 0) or 0) for row in trial_rows]
            hmcf = [self.nwb_contract_hmcf(row) for row in trial_rows]
            trial_types = [self.nwb_contract_trial_type(row) for row in trial_rows]
            self.replace_hdf5_dataset(trials, "id", trial_ids)
            self.replace_hdf5_dataset(trials, "sound_ids", sound_ids)
            self.replace_hdf5_dataset(trials, "HMCF", hmcf, dtype=utf8)
            self.replace_hdf5_dataset(trials, "trial_type", trial_types, dtype=utf8)

            parameters = h5f.require_group("acquisition").require_group("Parameters")
            parameter_items = self.build_nwb_contract_parameters(rate, len(trial_rows))
            self.replace_hdf5_dataset(parameters, "key", [key for key, value in parameter_items], dtype=utf8)
            self.replace_hdf5_dataset(parameters, "value", [value for key, value in parameter_items], dtype=utf8)

    def replace_hdf5_dataset(self, parent, name, data, dtype=None):
        if name in parent:
            del parent[name]
        if dtype is None:
            parent.create_dataset(name, data=data)
        else:
            parent.create_dataset(name, data=data, dtype=dtype)

    def build_nwb_contract_parameters(self, rate, exported_trial_count=None):
        params = self.get_current_parameters()
        items = [
            ("User", params["UserName"]),
            ("Mouse", params["MouseId"]),
            ("Project", params["ProjectName"]),
            ("Output", params["OuputformatDropDown"]),
            ("Device", self.device.get()),
            ("Channels", self.channels.get()),
            ("frec", rate),
            ("TaskType", params["TaskType"]),
            ("TriggerType", params["TriggerTypeDropDown"]),
            ("Threshold", params["LeverThreshold"]),
            ("SampleSoundId", params["SampleSoundId"]),
            ("TestSoundId", params["TestSoundId"]),
            ("Delay_s", params["Delay_s"]),
            ("SoundDuration_s", params["SoundDuration_s"]),
            ("ResponseWindow_s", params["ResponseWindow_s"]),
            ("Rewardduration_ms", params["Rewardduration_ms"]),
            ("HIT", params["HIT"]),
            ("PunishInterval", params["PunishInterval"]),
            ("RewardGo", params["RewardGo"]),
            ("RewardProb", params["RewardProb"]),
            ("PunishNoGoFA", params["PunishNoGoFA"]),
            ("Minlickcount", params["Minlickcount"]),
            ("Lickthreshold", params["Lickthreshold"]),
            ("NWBExportedTrials", exported_trial_count if exported_trial_count is not None else len(self.trial_rows)),
            ("NWBOriginalTrialRows", len(self.trial_rows)),
            ("NWBTrialAnchor", "sound_epoch_start_or_trigger_time"),
        ]
        if self.parameter_rows:
            latest = self.parameter_rows[-1]
            for key, value in latest.items():
                items.append((key, value))
        seen = set()
        unique_items = []
        for key, value in items:
            key = str(key)
            if key in seen:
                continue
            seen.add(key)
            unique_items.append((key, str(value)))
        return unique_items

    def validate_nwb_contract_hdf5(self, path):
        required_paths = (
            "/stimulus/presentation/SoundCopy/data",
            "/stimulus/presentation/WhichSound/data",
            "/acquisition/Reward/data",
            "/acquisition/TrialType/data",
            "/acquisition/IRFork/data",
            "/intervals/trials/id",
            "/intervals/trials/sound_ids",
            "/intervals/trials/HMCF",
            "/intervals/trials/trial_type",
            "/file_create_date",
            "/acquisition/Parameters/key",
            "/acquisition/Parameters/value",
        )
        with h5py.File(path, "r") as h5f:
            missing = [item for item in required_paths if item not in h5f]
            if missing:
                raise RuntimeError(f"NWB contract paths are missing: {', '.join(missing)}")

            trial_count = len(h5f["/intervals/trials/id"])
            aligned_paths = (
                "/intervals/trials/sound_ids",
                "/intervals/trials/HMCF",
                "/intervals/trials/trial_type",
            )
            for item in aligned_paths:
                if len(h5f[item]) != trial_count:
                    raise RuntimeError(f"NWB contract trial table length mismatch: {item}")

            parameter_key_count = len(h5f["/acquisition/Parameters/key"])
            parameter_value_count = len(h5f["/acquisition/Parameters/value"])
            if parameter_key_count != parameter_value_count:
                raise RuntimeError("NWB contract parameter key/value length mismatch.")

            trial_type_values = {
                self.decode_hdf5_string(value)
                for value in h5f["/intervals/trials/trial_type"][()]
                if self.decode_hdf5_string(value)
            }
            bad_trial_types = trial_type_values - {"Go", "NoGo", "DMTS"}
            if bad_trial_types:
                raise RuntimeError(f"NWB contract trial_type has unsupported values: {sorted(bad_trial_types)}")

            hmcf_values = {
                self.decode_hdf5_string(value)
                for value in h5f["/intervals/trials/HMCF"][()]
                if self.decode_hdf5_string(value)
            }
            bad_hmcf = hmcf_values - {"Hit", "Miss", "Correct", "FalseAlarm"}
            if bad_hmcf:
                raise RuntimeError(f"NWB contract HMCF has unsupported values: {sorted(bad_hmcf)}")

            ir_count = len(h5f["/acquisition/IRFork/data"])
            for item in (
                "/stimulus/presentation/SoundCopy/data",
                "/stimulus/presentation/WhichSound/data",
                "/acquisition/Reward/data",
            ):
                if len(h5f[item]) != ir_count:
                    raise RuntimeError(f"NWB contract continuous signal length mismatch: {item}")

            anchor_count = int((h5f["/acquisition/TrialType/data"][()] == 99).sum())
            if anchor_count != trial_count:
                raise RuntimeError(
                    f"NWB contract trial anchor count mismatch: {anchor_count} anchors for {trial_count} trial rows."
                )
            if trial_count and anchor_count == 0:
                raise RuntimeError("NWB contract TrialType trace has trials but no value 99 anchors.")

    def decode_hdf5_string(self, value):
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    def nwb_contract_trial_type(self, row):
        trial_type = str(row.get("TrialType", ""))
        if trial_type.endswith("GO"):
            return "Go"
        if trial_type.endswith("noGo"):
            return "NoGo"
        if trial_type.endswith("DMTS"):
            return "DMTS"
        return ""

    def nwb_contract_hmcf(self, row):
        result = str(row.get("ResultType", "")).upper()
        if result == "HIT":
            return "Hit"
        if result == "MISS":
            return "Miss"
        if result == "CR":
            return "Correct"
        if result == "FA":
            return "FalseAlarm"
        return ""

    def read_irfork_binary(self, path):
        if np is not None:
            return np.fromfile(path, dtype="<f8")
        with open(path, "rb") as f:
            data_bytes = f.read()
        count = len(data_bytes) // 8
        if count <= 0:
            return []
        return list(struct.unpack(f"{count}d", data_bytes[: count * 8]))

    def build_trigger_trace(self, sample_count, rate):
        if np is not None:
            trace = np.zeros(sample_count, dtype=float)
        else:
            trace = [0.0] * sample_count
        for start_s, end_s in self.full_trigger_pulses:
            start_idx = max(0, int(start_s * rate))
            end_idx = min(sample_count, max(start_idx + 1, int(end_s * rate)))
            if start_idx < sample_count:
                if np is not None:
                    trace[start_idx:end_idx] = 5.0
                else:
                    trace[start_idx:end_idx] = [5.0] * (end_idx - start_idx)
        return trace

    def build_contract_sound_epochs(self, sample_count, rate):
        duration_s = sample_count / rate if rate else 0.0
        epochs = []
        for sound_output in self.full_sound_outputs:
            start_s, fs, sound_values = sound_output[:3]
            sound_id = sound_output[3] if len(sound_output) > 3 else 0
            if fs <= 0 or start_s >= duration_s:
                continue
            epochs.append({
                "start_s": max(0.0, float(start_s)),
                "fs": fs,
                "values": sound_values,
                "sound_id": int(sound_id or 0),
            })
        return epochs

    def get_recorded_soundcopy_trace(self, sample_count):
        soundcopy_path = os.path.join(self.exp_folder, "SoundCopy.bin") if self.exp_folder else ""
        if soundcopy_path and os.path.exists(soundcopy_path):
            values = self.read_irfork_binary(soundcopy_path)
        elif self.full_soundcopy_buffer:
            values = self.full_soundcopy_buffer
        else:
            return None

        if len(values) == 0:
            return None
        if np is not None:
            trace = np.asarray(values, dtype=float).reshape(-1)
            if len(trace) < sample_count:
                trace = np.pad(trace, (0, sample_count - len(trace)), mode="constant")
            elif len(trace) > sample_count:
                trace = trace[:sample_count]
            if not np.any(np.abs(trace) > 1e-12):
                return None
            return trace

        trace = [float(value) for value in values]
        if len(trace) < sample_count:
            trace.extend([0.0] * (sample_count - len(trace)))
        elif len(trace) > sample_count:
            trace = trace[:sample_count]
        if not any(abs(value) > 1e-12 for value in trace):
            return None
        return trace

    def get_nwb_contract_trial_rows(self, sample_count, rate, sound_epochs):
        duration_s = sample_count / rate if rate else 0.0
        rows = []
        for row in self.trial_rows:
            anchor_s = self.nwb_contract_trial_anchor_s(row, sound_epochs)
            if anchor_s is None or anchor_s >= duration_s:
                continue
            rows.append(row)
        skipped = len(self.trial_rows) - len(rows)
        if skipped:
            self.log(
                f"NWB export skipped {skipped} trial rows outside the continuous recording "
                f"duration ({duration_s:.3f} s)."
            )
        return rows

    def nwb_contract_trial_anchor_s(self, row, sound_epochs):
        try:
            trigger_time_s = float(row.get("trigger_time_s", 0.0))
        except Exception:
            return None
        try:
            sound_id = int(row.get("sound_id", 0) or 0)
        except Exception:
            sound_id = 0
        best_start_s = None
        best_distance_s = None
        for epoch in sound_epochs:
            if sound_id and epoch["sound_id"] not in (0, sound_id):
                continue
            start_s = epoch["start_s"]
            if start_s < trigger_time_s - 0.25 or start_s > trigger_time_s + 1.0:
                continue
            distance_s = abs(start_s - trigger_time_s)
            if best_distance_s is None or distance_s < best_distance_s:
                best_start_s = start_s
                best_distance_s = distance_s
        return best_start_s if best_start_s is not None else trigger_time_s

    def build_contract_sound_traces(self, sample_count, rate, sound_epochs):
        if np is not None:
            sound_copy = np.zeros(sample_count, dtype=float)
            which_sound = np.zeros(sample_count, dtype=int)
        else:
            sound_copy = [0.0] * sample_count
            which_sound = [0] * sample_count
        for epoch in sound_epochs:
            start_s = epoch["start_s"]
            fs = epoch["fs"]
            sound_values = epoch["values"]
            sound_id = epoch["sound_id"]
            start_idx = int(max(0.0, start_s) * rate)
            output_count = int(math.ceil(len(sound_values) * rate / fs)) if fs else 0
            for offset in range(output_count):
                target_idx = start_idx + offset
                if target_idx >= sample_count:
                    break
                source_start = min(len(sound_values), int(offset * fs / rate))
                source_end = min(len(sound_values), max(source_start + 1, int((offset + 1) * fs / rate)))
                if source_start < source_end:
                    source_bin = sound_values[source_start:source_end]
                    if np is not None:
                        sound_copy[target_idx] = float(np.max(np.abs(source_bin)))
                    else:
                        sound_copy[target_idx] = max(abs(float(value)) for value in source_bin)
                which_sound[target_idx] = int(sound_id or 0)
        return sound_copy, which_sound

    def build_contract_trial_type_trace(self, ir_sample_count, ir_rate, trial_rows, sound_epochs):
        trial_bin_s = 0.1
        duration_s = ir_sample_count / ir_rate if ir_rate else 0.0
        marker_count = max(1, int(math.ceil(duration_s / trial_bin_s)) + 1)
        if np is not None:
            trace = np.zeros(marker_count, dtype=int)
        else:
            trace = [0] * marker_count
        for row in trial_rows:
            anchor_s = self.nwb_contract_trial_anchor_s(row, sound_epochs)
            if anchor_s is None:
                continue
            marker_idx = int(round(anchor_s / trial_bin_s))
            if 0 <= marker_idx < marker_count:
                trace[marker_idx] = 99
        return trace

    def _drain_plot_queue(self):
        try:
            while True:
                kind, payload = self.plot_queue.get_nowait()
                if kind == "plot":
                    self.draw_plot(*payload)
                elif kind == "log":
                    self.log(payload)
                elif kind == "status":
                    self.set_status(payload)
                elif kind == "results":
                    self.redraw_results_window()
        except queue.Empty:
            pass
        self.after(50, self._drain_plot_queue)

    def open_results_window(self):
        if self.results_window is not None and self.results_window.winfo_exists():
            self.results_window.lift()
            self.redraw_results_window()
            return

        self.results_window = tk.Toplevel(self)
        self.results_window.title("BASIL Trial Results")
        self.results_window.geometry("900x520")
        self.results_window.protocol("WM_DELETE_WINDOW", self.close_results_window)
        frame = ttk.Frame(self.results_window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.results_canvas = tk.Canvas(frame, bg="white", highlightthickness=0)
        self.results_canvas.grid(row=0, column=0, sticky="nsew")
        self.results_canvas.bind("<Configure>", lambda _event: self.redraw_results_window())
        self.redraw_results_window()

    def close_results_window(self):
        if self.results_window is not None and self.results_window.winfo_exists():
            self.results_window.destroy()
        self.results_window = None
        self.results_canvas = None

    def redraw_results_window(self):
        if self.results_canvas is None:
            return
        if self.results_window is None or not self.results_window.winfo_exists():
            self.results_canvas = None
            self.results_window = None
            return

        canvas = self.results_canvas
        canvas.delete("all")
        width = max(520, canvas.winfo_width())
        height = max(320, canvas.winfo_height())
        completed = [row for row in self.trial_rows if row.get("ResultType")]
        if not completed:
            canvas.create_text(width / 2, height / 2, text="No completed trials yet", fill="#555555")
            return

        counts = {key: 0 for key in ("HIT", "MISS", "CR", "FA")}
        for row in completed:
            result = row.get("ResultType", "")
            if result in counts:
                counts[result] += 1

        go_total = counts["HIT"] + counts["MISS"]
        nogo_total = counts["CR"] + counts["FA"]
        hit_rate = counts["HIT"] / go_total if go_total else 0.0
        cr_rate = counts["CR"] / nogo_total if nogo_total else 0.0
        title = (
            f"Trials {len(completed)}   HIT {counts['HIT']}   MISS {counts['MISS']}   "
            f"CR {counts['CR']}   FA {counts['FA']}   "
            f"GO hit {hit_rate:.0%}   noGo CR {cr_rate:.0%}"
        )
        canvas.create_text(18, 18, text=title, anchor="w", fill="#222222", font=("Segoe UI", 10, "bold"))

        left = 54
        right = width - 24
        condition_left = None
        if width >= 760:
            condition_width = min(240, max(190, width * 0.28))
            condition_left = width - condition_width
            right = condition_left - 28
        raster_top = 52
        raster_bottom = min(190, height * 0.42)
        rate_top = raster_bottom + 54
        rate_bottom = height - 36
        plot_width = max(1, right - left)

        recent = completed[-80:]
        cell_w = plot_width / max(1, len(recent))
        colors = {
            "HIT": "#2ca02c",
            "MISS": "#ff7f0e",
            "CR": "#1f77b4",
            "FA": "#d62728",
        }
        y_positions = {
            "HIT": raster_top + 16,
            "MISS": raster_top + 48,
            "CR": raster_top + 80,
            "FA": raster_top + 112,
        }
        for result, y in y_positions.items():
            canvas.create_text(left - 10, y, text=result, anchor="e", fill="#333333")
            canvas.create_line(left, y, right, y, fill="#eeeeee")
        for index, row in enumerate(recent):
            result = row.get("ResultType", "")
            y = y_positions.get(result, raster_top + 16)
            x0 = left + index * cell_w + 1
            x1 = left + (index + 1) * cell_w - 1
            canvas.create_rectangle(x0, y - 9, max(x0 + 2, x1), y + 9, fill=colors.get(result, "#777777"), outline="")
        canvas.create_text(left, raster_bottom + 18, text="Recent trial outcomes", anchor="w", fill="#333333")

        self._draw_rate_panel(canvas, completed, left, right, rate_top, rate_bottom)
        if condition_left is not None:
            self._draw_condition_panel(canvas, completed, condition_left, width - 24, 52, height - 36)

    def _draw_condition_panel(self, canvas, rows, left, right, top, bottom):
        canvas.create_rectangle(left, top, right, bottom, outline="#dddddd")
        canvas.create_text(left, top - 20, text="HIT/CR by condition", anchor="w", fill="#333333")

        label_width = 72
        bar_left = left + label_width
        bar_right = right - 12
        plot_top = top + 34
        plot_bottom = bottom - 24
        for fraction in (0.0, 0.5, 1.0):
            x = bar_left + fraction * max(1, bar_right - bar_left)
            canvas.create_line(x, plot_top - 14, x, plot_bottom, fill="#eeeeee")
            canvas.create_text(x, bottom - 10, text=f"{fraction:.1f}", anchor="n", fill="#555555", font=("Segoe UI", 8))

        conditions = {}
        for row in rows:
            trial_type = str(row.get("TrialType", ""))
            sound_id = row.get("sound_id", "")
            key = (sound_id, trial_type)
            if key not in conditions:
                conditions[key] = {"correct": 0, "total": 0}
            result = row.get("ResultType", "")
            conditions[key]["total"] += 1
            if trial_type.endswith("noGo"):
                conditions[key]["correct"] += int(result == "CR")
            elif trial_type.endswith("GO") or trial_type.endswith("Lever"):
                conditions[key]["correct"] += int(result == "HIT")
            else:
                conditions[key]["correct"] += int(result in ("HIT", "CR"))

        def sort_key(item):
            sound_id, trial_type = item[0]
            try:
                sound_sort = (0, int(sound_id))
            except (TypeError, ValueError):
                sound_sort = (1, str(sound_id))
            return (str(trial_type), sound_sort)

        ordered = sorted(conditions.items(), key=sort_key)
        max_rows = max(1, int((plot_bottom - plot_top) // 24))
        hidden_count = max(0, len(ordered) - max_rows)
        ordered = ordered[:max_rows]
        row_gap = (plot_bottom - plot_top) / max(1, len(ordered))
        colors = {
            "GO": "#2ca02c",
            "Lever": "#2ca02c",
            "noGo": "#1f77b4",
        }
        for index, ((sound_id, trial_type), stats) in enumerate(ordered):
            y = plot_top + index * row_gap + row_gap / 2
            total = max(1, stats["total"])
            fraction = stats["correct"] / total
            type_name = str(trial_type).split(maxsplit=1)[-1] if trial_type else "condition"
            color = colors.get(type_name, "#777777")
            label = f"S{sound_id} {type_name}"
            bar_end = bar_left + fraction * max(1, bar_right - bar_left)
            canvas.create_text(left + label_width - 8, y, text=label, anchor="e", fill="#333333", font=("Segoe UI", 8))
            canvas.create_rectangle(bar_left, y - 7, bar_right, y + 7, fill="#f7f7f7", outline="#dddddd")
            canvas.create_rectangle(bar_left, y - 7, bar_end, y + 7, fill=color, outline="")
            canvas.create_text(bar_right, y - 10, text=f"{fraction:.0%} n={stats['total']}", anchor="e", fill="#333333", font=("Segoe UI", 8))
        if hidden_count:
            canvas.create_text(left + 8, bottom - 6, text=f"+{hidden_count} more", anchor="sw", fill="#555555", font=("Segoe UI", 8))

    def _draw_rate_panel(self, canvas, rows, left, right, top, bottom):
        canvas.create_rectangle(left, top, right, bottom, outline="#dddddd")
        for fraction in (0.0, 0.5, 1.0):
            y = bottom - fraction * (bottom - top)
            canvas.create_line(left, y, right, y, fill="#eeeeee")
            canvas.create_text(left - 8, y, text=f"{fraction:.1f}", anchor="e", fill="#555555")

        hit_points = []
        cr_points = []
        result_points = []
        go_hits = go_total = nogo_cr = nogo_total = 0
        n = len(rows)
        for index, row in enumerate(rows, start=1):
            result = row.get("ResultType", "")
            if result in ("HIT", "MISS"):
                go_total += 1
                go_hits += int(result == "HIT")
                result_score = 1 if result == "HIT" else 0
            elif result in ("CR", "FA"):
                nogo_total += 1
                nogo_cr += int(result == "CR")
                result_score = 1 if result == "CR" else 0
            else:
                result_score = None
            x = left + ((index - 1) / max(1, n - 1)) * (right - left)
            if result_score is not None:
                result_points.append((x, bottom - result_score * (bottom - top), result))
            hit_points.append((x, bottom - (go_hits / go_total if go_total else 0.0) * (bottom - top)))
            cr_points.append((x, bottom - (nogo_cr / nogo_total if nogo_total else 0.0) * (bottom - top)))

        colors = {
            "HIT": "#2ca02c",
            "MISS": "#ff7f0e",
            "CR": "#1f77b4",
            "FA": "#d62728",
        }
        for x, y, result in result_points:
            canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=colors.get(result, "#777777"), outline="")
        self._draw_polyline(canvas, hit_points, "#2ca02c")
        self._draw_polyline(canvas, cr_points, "#1f77b4")
        canvas.create_text(left, top - 20, text="Running performance", anchor="w", fill="#333333")
        canvas.create_line(right - 170, top - 20, right - 140, top - 20, fill="#2ca02c", width=3)
        canvas.create_text(right - 134, top - 20, text="GO hit", anchor="w", fill="#333333")
        canvas.create_line(right - 82, top - 20, right - 52, top - 20, fill="#1f77b4", width=3)
        canvas.create_text(right - 46, top - 20, text="noGo CR", anchor="w", fill="#333333")

    def _draw_polyline(self, canvas, points, color):
        if len(points) == 1:
            x, y = points[0]
            canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill=color, outline="")
            return
        coords = []
        for x, y in points:
            coords.extend((x, y))
        canvas.create_line(*coords, fill=color, width=3, smooth=True)

    def draw_plot(self, times, values):
        self.plot_canvas.delete("all")
        width = max(10, self.plot_canvas.winfo_width())
        height = max(10, self.plot_canvas.winfo_height())
        if not times or not values:
            return
        max_points = 1200
        step = max(1, len(values) // max_points)
        times = times[::step]
        values = values[::step]
        ir_baseline = self.current_ir_baseline if self.subtract_baseline.get() else 0.0
        values = [value - ir_baseline for value in values]
        min_t, max_t = times[0], times[-1] if times[-1] != times[0] else times[0] + 1
        min_v, max_v = min(values), max(values)
        overlay_min_v, overlay_max_v = 0.0, 1.0
        visible_trigger = any(end_s >= min_t and start_s <= max_t for start_s, end_s in self.trigger_pulses)
        visible_sound = any(
            start_s + len(sound_values) / sound_fs >= min_t and start_s <= max_t
            for start_s, sound_fs, sound_values in (sound_output[:3] for sound_output in self.sound_outputs)
        )
        visible_trial_state = any(
            (end_s if end_s is not None else max_t) >= min_t and start_s <= max_t
            for start_s, end_s in self.trial_state_intervals
        )
        if visible_trigger:
            overlay_min_v = min(overlay_min_v, 0.0)
            overlay_max_v = max(overlay_max_v, 5.0)
        if visible_trial_state:
            overlay_min_v = min(overlay_min_v, 0.0)
            overlay_max_v = max(overlay_max_v, 1.0)
        if visible_sound:
            for sound_output in self.sound_outputs:
                start_s, sound_fs, sound_values = sound_output[:3]
                sound_end = start_s + len(sound_values) / sound_fs
                if sound_end < min_t or start_s > max_t or not sound_values:
                    continue
                overlay_min_v = min(overlay_min_v, min(sound_values))
                overlay_max_v = max(overlay_max_v, max(sound_values))
        if not self.auto_scale.get():
            min_v = self.parse_float(self.left_y_min, -1.0)
            max_v = self.parse_float(self.left_y_max, 5.0)
            overlay_min_v = self.parse_float(self.right_y_min, -1.0)
            overlay_max_v = self.parse_float(self.right_y_max, 5.0)
            if max_v < min_v:
                min_v, max_v = max_v, min_v
            if overlay_max_v < overlay_min_v:
                overlay_min_v, overlay_max_v = overlay_max_v, overlay_min_v
        if max_v == min_v:
            max_v = min_v + 1
        if overlay_max_v == overlay_min_v:
            overlay_max_v = overlay_min_v + 1
        left_pad = 42
        right_pad = 52
        top_pad = 12
        bottom_pad = 34
        plot_width = max(1, width - left_pad - right_pad)
        plot_height = max(1, height - top_pad - bottom_pad)
        points = []
        for t, v in zip(times, values):
            x = left_pad + (t - min_t) / (max_t - min_t) * plot_width
            y = height - bottom_pad - (v - min_v) / (max_v - min_v) * plot_height
            points.extend([x, y])
        x_axis_y = height - bottom_pad
        self.draw_active_trial_shading(min_t, max_t, left_pad, top_pad, plot_width, x_axis_y)
        self.plot_canvas.create_line(left_pad, x_axis_y, width - right_pad, x_axis_y, fill="#cccccc")
        self.plot_canvas.create_line(left_pad, top_pad, left_pad, x_axis_y, fill="#cccccc")
        right_axis_x = left_pad + plot_width
        self.plot_canvas.create_line(right_axis_x, top_pad, right_axis_x, x_axis_y, fill="#cccccc")
        first_second = math.ceil(min_t)
        last_second = math.floor(max_t)
        for second in range(first_second, last_second + 1):
            tick_x = left_pad + (second - min_t) / (max_t - min_t) * plot_width
            self.plot_canvas.create_line(tick_x, top_pad, tick_x, x_axis_y, fill="#eeeeee")
        for i in range(5):
            frac = i / 4
            tick_x = left_pad + frac * plot_width
            tick_t = min_t + frac * (max_t - min_t)
            self.plot_canvas.create_line(tick_x, x_axis_y, tick_x, x_axis_y + 4, fill="#999999")
            self.plot_canvas.create_text(tick_x, x_axis_y + 16, text=f"{tick_t:.1f}", fill="#555555")
            left_tick_v = min_v + (1.0 - frac) * (max_v - min_v)
            right_tick_v = overlay_min_v + (1.0 - frac) * (overlay_max_v - overlay_min_v)
            tick_y = top_pad + frac * plot_height
            self.plot_canvas.create_text(left_pad - 5, tick_y, text=f"{left_tick_v:.1f}", anchor="e", fill="#1f77b4", font=("Segoe UI", 8))
            self.plot_canvas.create_text(right_axis_x + 5, tick_y, text=f"{right_tick_v:.1f}", anchor="w", fill="#555555", font=("Segoe UI", 8))
        self.plot_canvas.create_text(width / 2, height - 6, text="Time (s)", fill="#555555")
        self.draw_trial_state_trace(min_t, max_t, overlay_min_v, overlay_max_v, left_pad, plot_width, plot_height, x_axis_y)
        self.draw_trigger_trace(min_t, max_t, overlay_min_v, overlay_max_v, left_pad, top_pad, plot_width, plot_height, x_axis_y)
        self.draw_sound_trace(min_t, max_t, overlay_min_v, overlay_max_v, left_pad, plot_width, plot_height, x_axis_y)
        if len(points) >= 4:
            self.plot_canvas.create_line(*points, fill="#1f77b4", width=2)
        self.plot_canvas.create_text(
            8,
            8,
            anchor="nw",
            text=f"Left {min_v:.2f} to {max_v:.2f} V, right {overlay_min_v:.2f} to {overlay_max_v:.2f}, baseline {ir_baseline:.2f} V",
            fill="#555555",
        )
        self.plot_canvas.create_text(width - 120, 10, anchor="nw", text="IRFork", fill="#1f77b4")
        self.plot_canvas.create_text(width - 120, 26, anchor="nw", text="Trigger output", fill="#d97904")
        self.plot_canvas.create_text(width - 120, 42, anchor="nw", text="Sound output", fill="#2ca02c")
        self.plot_canvas.create_text(width - 120, 58, anchor="nw", text="Trial state", fill="#6f42c1")

    def draw_active_trial_shading(self, min_t, max_t, left_pad, top_pad, plot_width, x_axis_y):
        if self.active_trial_index is None or self.active_trial_start_s is None:
            return
        shade_start_s = max(self.active_trial_start_s, min_t)
        shade_end_s = self.active_trial_end_s if self.active_trial_end_s is not None else max_t
        shade_end_s = min(max(shade_end_s, shade_start_s), max_t)
        if shade_end_s < min_t or shade_start_s > max_t:
            return
        x0 = left_pad + (shade_start_s - min_t) / (max_t - min_t) * plot_width
        x1 = left_pad + (shade_end_s - min_t) / (max_t - min_t) * plot_width
        if x1 <= x0:
            x1 = x0 + 1
        self.plot_canvas.create_rectangle(x0, top_pad, x1, x_axis_y, fill="#eeeeee", outline="")
        self.plot_canvas.create_line(x0, top_pad, x0, x_axis_y, fill="#bdbdbd", dash=(4, 3))

    def draw_trial_state_trace(self, min_t, max_t, min_v, max_v, left_pad, plot_width, plot_height, x_axis_y):
        if not self.trial_state_intervals:
            return

        def x_for(t):
            return left_pad + (t - min_t) / (max_t - min_t) * plot_width

        def y_for(v):
            return x_axis_y - (v - min_v) / (max_v - min_v) * plot_height

        low_y = y_for(0.0)
        high_y = y_for(1.0)
        if min_v <= 0.0 <= max_v:
            self.plot_canvas.create_line(left_pad, low_y, left_pad + plot_width, low_y, fill="#d8ccef")
        for start_s, end_s in list(self.trial_state_intervals):
            interval_end_s = end_s if end_s is not None else max_t
            if interval_end_s < min_t or start_s > max_t:
                continue
            start_x = x_for(max(start_s, min_t))
            end_x = x_for(min(interval_end_s, max_t))
            if end_x <= start_x:
                end_x = start_x + 1
            self.plot_canvas.create_line(start_x, low_y, start_x, high_y, fill="#6f42c1", width=2)
            self.plot_canvas.create_line(start_x, high_y, end_x, high_y, fill="#6f42c1", width=2)
            if end_s is not None and end_s <= max_t:
                self.plot_canvas.create_line(end_x, high_y, end_x, low_y, fill="#6f42c1", width=2)

    def draw_trigger_trace(self, min_t, max_t, min_v, max_v, left_pad, top_pad, plot_width, plot_height, x_axis_y):
        def x_for(t):
            return left_pad + (t - min_t) / (max_t - min_t) * plot_width

        def y_for(v):
            return x_axis_y - (v - min_v) / (max_v - min_v) * plot_height

        low_y = y_for(0.0)
        high_y = y_for(5.0)
        if top_pad <= low_y <= x_axis_y:
            self.plot_canvas.create_line(left_pad, low_y, left_pad + plot_width, low_y, fill="#f1c27d")

        for start_s, end_s in list(self.trigger_pulses):
            if end_s < min_t or start_s > max_t:
                continue
            start_x = x_for(max(start_s, min_t))
            end_x = x_for(min(end_s, max_t))
            self.plot_canvas.create_line(start_x, low_y, start_x, high_y, fill="#d97904", width=2)
            self.plot_canvas.create_line(start_x, high_y, end_x, high_y, fill="#d97904", width=2)
            self.plot_canvas.create_line(end_x, high_y, end_x, low_y, fill="#d97904", width=2)

    def draw_sound_trace(self, min_t, max_t, min_v, max_v, left_pad, plot_width, plot_height, x_axis_y):
        visible_width = max(1, int(plot_width))

        def x_for(t):
            return left_pad + (t - min_t) / (max_t - min_t) * plot_width

        def y_for(v):
            return x_axis_y - (v - min_v) / (max_v - min_v) * plot_height

        for sound_output in list(self.sound_outputs):
            start_s, fs, values = sound_output[:3]
            if not values:
                continue
            end_s = start_s + len(values) / fs
            if end_s < min_t or start_s > max_t:
                continue
            first_idx = max(0, int((min_t - start_s) * fs))
            last_idx = min(len(values), int((max_t - start_s) * fs) + 1)
            if last_idx <= first_idx:
                continue
            sample_count = last_idx - first_idx
            step = max(1, sample_count // visible_width)
            points = []
            for idx in range(first_idx, last_idx, step):
                t = start_s + idx / fs
                points.extend([x_for(t), y_for(values[idx])])
            if len(points) >= 4:
                self.plot_canvas.create_line(*points, fill="#2ca02c", width=1)

    def on_close(self):
        self.stop_live()
        self.destroy()


if __name__ == "__main__":
    app = BehaviorAcquisitionApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
