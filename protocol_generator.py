import os
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk


APP_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_NI_SCRIPT = os.path.join(APP_DIR, "setup_valves_IRFork.m").replace(os.sep, "/")


@dataclass(frozen=True)
class Parameter:
    key: str
    label: str
    default: str
    section: str
    kind: str = "text"
    choices: tuple[str, ...] = ()


PARAMETERS = [
    Parameter("UserName", "User", "username", "Session"),
    Parameter("MouseId", "Mouse ID", "1", "Session", "int"),
    Parameter("ProjectName", "Project", "ProjectName", "Session"),
    Parameter("NICard_filename", "NI script", DEFAULT_NI_SCRIPT, "Session"),
    Parameter("Sound_filename", "Sound file", "", "Session"),
    Parameter("frec", "Acquisition rate Hz", "1000", "Session", "float"),
    Parameter("bin", "Callback/bin s", "0.1", "Session", "float"),
    Parameter("TriggerTypeDropDown", "Trigger", "IRFork", "Session", "choice", ("IRFork", "Lick", "None")),
    Parameter("OuputformatDropDown", "Output format", "NWB", "Session", "choice", ("NWB", "BIDS", "No standard")),
    Parameter("TaskType", "Task type", "ClassicGoNoGo", "GoNoGo"),
    Parameter("MaxTrials", "Max trials", "300", "GoNoGo", "int"),
    Parameter("GoWeight", "Go weight", "0.5", "GoNoGo", "float"),
    Parameter("NoGoWeight", "No-go weight", "0.5", "GoNoGo", "float"),
    Parameter("GoSoundId", "Go sound ID", "1", "GoNoGo", "int"),
    Parameter("NoGoSoundId", "No-go sound ID", "10", "GoNoGo", "int"),
    Parameter("SoundLevel", "Sound level", "1", "GoNoGo", "float"),
    Parameter("RandomSeed", "Random seed", "0", "GoNoGo", "int"),
    Parameter("ITI_s", "ITI", "2", "GoNoGoTiming", "float"),
    Parameter("ITIrandMin_s", "rand min", "0", "GoNoGoTiming", "float"),
    Parameter("ITIrandMax_s", "rand max", "0", "GoNoGoTiming", "float"),
    Parameter("Sounddelay_s", "Sound delay s", "0", "GoNoGoTiming", "float"),
    Parameter("SoundDuration_s", "Sound duration s", "0.2", "GoNoGoTiming", "float"),
    Parameter("TrialDuration_s", "Trial duration s", "2.2", "GoNoGoTiming", "float"),
    Parameter("ResponseWindow_s", "Response window s", "2", "GoNoGoTiming", "float"),
    Parameter("RewardDelay_s", "Reward delay s", "0", "GoNoGoTiming", "float"),
    Parameter("Rewardduration_ms", "Reward duration ms", "40", "GoNoGoOutcome", "float"),
    Parameter("RewardGoProb", "RewardGo Prob", "1", "GoNoGoOutcome", "float"),
    Parameter("Pavlov", "Pavlov", "0", "GoNoGoOutcome", "float"),
    Parameter("PunishNoGoFA", "Timeout false alarms", "1", "GoNoGoOutcome", "float"),
    Parameter("HITThreshold_percent", "HIT threshold %", "50", "GoNoGoOutcome", "float"),
    Parameter("Minlickcount", "Min lick count", "1", "GoNoGoOutcome", "int"),
    Parameter("Lickthreshold", "Signal threshold V", "1", "GoNoGoOutcome", "float"),
    Parameter("LeverTaskType", "Task type", "Lever", "Lever"),
    Parameter("LeverThreshold", "Lever threshold V", "1", "Lever", "float"),
    Parameter("LeverGoSoundId", "GO sound ID", "1", "Lever", "int"),
    Parameter("LeverSoundLevel", "Sound level", "1", "Lever", "float"),
    Parameter("LeverRequireRelease", "Require release", "0", "Lever", "choice", ("0", "1")),
    Parameter("LeverHoldTime_s", "Lever hold time s", "1", "LeverTiming", "float"),
    Parameter("LeverStartDebounce_s", "Start debounce s", "0.1", "LeverTiming", "float"),
    Parameter("LeverReleaseDebounce_s", "Release debounce s", "0.05", "LeverTiming", "float"),
    Parameter("LeverReleaseWindow_s", "Release window s", "0.25", "LeverTiming", "float"),
    Parameter("LeverRewardduration_ms", "Reward duration ms", "40", "LeverOutcome", "float"),
    Parameter("LeverRewardGo", "RewardGo Prob", "1", "LeverOutcome", "float"),
    Parameter("DMTSTaskType", "Task type", "DMTS", "DMTS"),
    Parameter("DMTSMaxTrials", "Max trials", "300", "DMTS", "int"),
    Parameter("DMTSMatchWeight", "Match weight", "0.5", "DMTS", "float"),
    Parameter("DMTSNonMatchWeight", "Non-match weight", "0.5", "DMTS", "float"),
    Parameter("DMTSSampleSoundId", "Sample sound ID", "1", "DMTS", "int"),
    Parameter("DMTSTestSoundId", "Test sound ID", "1", "DMTS", "int"),
    Parameter("DMTSRandomMatchTrials", "Random DMTS sounds", "1", "DMTS", "choice", ("0", "1")),
    Parameter("DMTSSoundIds", "Sound IDs", "1:16", "DMTS"),
    Parameter("DMTSSoundLevel", "Sound level", "1", "DMTS", "float"),
    Parameter("DMTSRandomSeed", "Random seed", "0", "DMTS", "int"),
    Parameter("DMTSITI_s", "ITI", "2", "DMTSTiming", "float"),
    Parameter("DMTSITIrandMin_s", "ITI min", "0", "DMTSTiming", "float"),
    Parameter("DMTSITIrandMax_s", "ITI max", "0", "DMTSTiming", "float"),
    Parameter("DMTSSoundDuration_s", "Sound duration s", "0.2", "DMTSTiming", "float"),
    Parameter("DMTSDelay_s", "Delay s", "2", "DMTSTiming", "float"),
    Parameter("DMTSResponseWindow_s", "Response window s", "2", "DMTSTiming", "float"),
    Parameter("DMTSRewardDelay_s", "Reward delay s", "0", "DMTSTiming", "float"),
    Parameter("DMTSRewardduration_ms", "Reward duration ms", "40", "DMTSOutcome", "float"),
    Parameter("DMTSRewardProb", "Reward prob", "1", "DMTSOutcome", "float"),
    Parameter("DMTSHITThreshold_percent", "Threshold of RW for HIT %", "50", "DMTSOutcome", "float"),
    Parameter("TACTaskType", "Task type", "tAC", "TAC"),
    Parameter("TACMaxTrials", "Max trials", "300", "TAC", "int"),
    Parameter("TACLeftWeight", "Left weight", "0.5", "TAC", "float"),
    Parameter("TACRightWeight", "Right weight", "0.5", "TAC", "float"),
    Parameter("TACLeftSoundId", "Left sound ID", "1", "TAC", "int"),
    Parameter("TACRightSoundId", "Right sound ID", "10", "TAC", "int"),
    Parameter("TACSoundLevel", "Sound level", "1", "TAC", "float"),
    Parameter("TACRandomSeed", "Random seed", "0", "TAC", "int"),
    Parameter("TACLeftChannel", "Left lick channel", "ai0", "TAC", "text"),
    Parameter("TACRightChannel", "Right lick channel", "ai1", "TAC", "text"),
    Parameter("TACITI_s", "ITI", "2", "TACTiming", "float"),
    Parameter("TACITIrandMin_s", "ITI min", "0", "TACTiming", "float"),
    Parameter("TACITIrandMax_s", "ITI max", "0", "TACTiming", "float"),
    Parameter("TACSounddelay_s", "Sound delay s", "0", "TACTiming", "float"),
    Parameter("TACSoundDuration_s", "Sound duration s", "0.2", "TACTiming", "float"),
    Parameter("TACTrialDuration_s", "Trial duration s", "2.2", "TACTiming", "float"),
    Parameter("TACResponseWindow_s", "Response window s", "2", "TACTiming", "float"),
    Parameter("TACRewardDelay_s", "Reward delay s", "0", "TACTiming", "float"),
    Parameter("TACRewardduration_ms", "Reward duration ms", "40", "TACOutcome", "float"),
    Parameter("TACRewardGo", "RewardGo Prob", "1", "TACOutcome", "float"),
    Parameter("TACPunishNoGoFA", "Wrong timeout s", "1", "TACOutcome", "float"),
    Parameter("TACMinlickcount", "Choice lick count", "1", "TACOutcome", "int"),
    Parameter("TACLeftThreshold", "Left threshold V", "1", "TACOutcome", "float"),
    Parameter("TACRightThreshold", "Right threshold V", "1", "TACOutcome", "float"),
    Parameter("TACPreTaskType", "Task type", "tACPretraining", "TACPre"),
    Parameter("TACPreMaxTrials", "Max rewards", "0", "TACPre", "int"),
    Parameter("TACPreLeftChannel", "Left lick channel", "ai0", "TACPre", "text"),
    Parameter("TACPreRightChannel", "Right lick channel", "ai1", "TACPre", "text"),
    Parameter("TACPreLeftThreshold", "Left threshold V", "1", "TACPre", "float"),
    Parameter("TACPreRightThreshold", "Right threshold V", "1", "TACPre", "float"),
    Parameter("TACPreRewardduration_ms", "Reward duration ms", "40", "TACPre", "float"),
    Parameter("TACPreRewardGo", "RewardGo Prob", "1", "TACPre", "float"),
]

COMMON_SECTIONS = ("Session",)
BEHAVIOR_TABS = [
    ("Classic Go/No-go", ("GoNoGo", "GoNoGoTiming", "GoNoGoOutcome")),
    ("Lever", ("Lever", "LeverTiming", "LeverOutcome")),
    ("DMTS", ("DMTS", "DMTSTiming", "DMTSOutcome")),
    ("tAC", ("TAC", "TACTiming", "TACOutcome")),
    ("tAC Pretraining", ("TACPre",)),
]
SECTION_LABELS = {
    "GoNoGo": "Task",
    "GoNoGoTiming": "Timing",
    "GoNoGoOutcome": "Outcome",
    "Lever": "Lever",
    "LeverTiming": "Timing",
    "LeverOutcome": "Outcome",
    "DMTS": "Task",
    "DMTSTiming": "Timing",
    "DMTSOutcome": "Outcome",
    "TAC": "Task",
    "TACTiming": "Timing",
    "TACOutcome": "Outcome",
    "TACPre": "Pretraining",
}


class ProtocolGenerator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Protocol Generator")
        self.geometry("1180x720")
        self.minsize(980, 620)
        self.variables = {}
        self.status_var = tk.StringVar(value="Ready.")
        self.current_path = tk.StringVar(value=os.path.join(APP_DIR, "protocols", "go_nogo_parameters.dat"))
        self._pending_redraw = None
        self._syncing_weight = False
        self._hit_widgets = []
        self._lick_widgets = []
        self._build_ui()
        self._bind_updates()
        self.sync_trial_duration()
        self.update_response_visibility()
        self.redraw_preview()

    def _build_ui(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=0, minsize=440)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        left = ttk.Frame(root)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        self._populate_sections(left, COMMON_SECTIONS, row_offset=0)

        self.notebook = ttk.Notebook(left)
        self.notebook.grid(row=1, column=0, sticky="nsew")
        for name, sections in BEHAVIOR_TABS:
            tab = ttk.Frame(self.notebook)
            tab.columnconfigure(0, weight=1)
            tab.rowconfigure(0, weight=1)
            self.notebook.add(tab, text=name)
            scrollable = self._add_scrollable_area(tab)
            self._populate_sections(scrollable, sections, row_offset=0)
        self.notebook.bind("<<NotebookTabChanged>>", lambda _event: self.on_tab_changed())

        right = ttk.Frame(root)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        plot_frame = ttk.LabelFrame(right, text="Protocol Preview")
        plot_frame.grid(row=0, column=0, sticky="nsew")
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(plot_frame, bg="white", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.canvas.bind("<Configure>", lambda _event: self.schedule_redraw())
        self.summary_var = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.summary_var).grid(row=1, column=0, sticky="w", pady=(8, 0))

        actions = ttk.Frame(root)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        actions.columnconfigure(1, weight=1)
        ttk.Button(actions, text="New Defaults", command=self.reset_defaults).grid(row=0, column=0, padx=(0, 6))
        ttk.Entry(actions, textvariable=self.current_path).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(actions, text="Load .dat", command=self.load_dat).grid(row=0, column=2, padx=6)
        ttk.Button(actions, text="Save .dat", command=self.save_dat).grid(row=0, column=3, padx=(6, 0))
        ttk.Label(actions, textvariable=self.status_var).grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))

    def _add_scrollable_area(self, parent):
        canvas = tk.Canvas(parent, width=430, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        inner_window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(inner_window, width=event.width))
        canvas.bind("<Enter>", lambda _event, target=canvas: self._activate_scroll_canvas(target))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))
        canvas.bind("<Destroy>", lambda _event: canvas.unbind_all("<MouseWheel>"))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        inner.columnconfigure(0, weight=1)
        return inner

    def _activate_scroll_canvas(self, canvas):
        self._active_scroll_canvas = canvas
        canvas.bind_all("<MouseWheel>", self._on_parameter_mousewheel)

    def _on_parameter_mousewheel(self, event):
        canvas = getattr(self, "_active_scroll_canvas", None)
        if canvas is None:
            return
        try:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except tk.TclError:
            pass

    def _populate_sections(self, parent, sections, row_offset):
        parent.columnconfigure(0, weight=1)
        for row, section in enumerate(sections, start=row_offset):
            frame = ttk.LabelFrame(parent, text=SECTION_LABELS.get(section, section))
            frame.grid(row=row, column=0, sticky="ew", padx=2, pady=(0, 8))
            frame.columnconfigure(1, weight=1)
            field_row = 0
            params = [item for item in PARAMETERS if item.section == section]
            if section == "GoNoGoTiming":
                self._add_iti_fields(frame, field_row)
                field_row += 1
                params = [p for p in params if p.key not in {"ITI_s", "ITIrandMin_s", "ITIrandMax_s"}]
            for parameter in params:
                self._add_parameter_field(frame, parameter, field_row)
                field_row += 1

    def _add_iti_fields(self, parent, row):
        ttk.Label(parent, text="ITI").grid(row=row, column=0, sticky="w", padx=6, pady=3)
        holder = ttk.Frame(parent)
        holder.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(4, 6), pady=3)
        for idx, key in enumerate(("ITI_s", "ITIrandMin_s", "ITIrandMax_s")):
            parameter = self.get_parameter(key)
            var = tk.StringVar(value=parameter.default)
            self.variables[key] = var
            ttk.Label(holder, text=parameter.label).grid(row=0, column=idx * 2, padx=(0, 3))
            ttk.Entry(holder, textvariable=var, width=7).grid(row=0, column=idx * 2 + 1, padx=(0, 8))

    def _add_parameter_field(self, parent, parameter, row):
        label = ttk.Label(parent, text=parameter.label)
        label.grid(row=row, column=0, sticky="w", padx=6, pady=3)
        var = tk.StringVar(value=parameter.default)
        self.variables[parameter.key] = var
        if parameter.kind == "choice":
            widget = ttk.Combobox(parent, textvariable=var, values=parameter.choices, state="readonly", width=22)
        else:
            state = "readonly" if parameter.key == "TrialDuration_s" else "normal"
            widget = ttk.Entry(parent, textvariable=var, width=25, state=state)
        widget.grid(row=row, column=1, sticky="ew", padx=(4, 6), pady=3)
        if parameter.key in {"NICard_filename", "Sound_filename"}:
            command = self.choose_ni_script if parameter.key == "NICard_filename" else self.choose_sound_file
            ttk.Button(parent, text="Browse", command=command).grid(row=row, column=2, padx=(0, 6), pady=3)
        if parameter.key == "HITThreshold_percent":
            self._hit_widgets = [label, widget]
        if parameter.key in {"Minlickcount", "Lickthreshold"}:
            self._lick_widgets.extend([label, widget])

    def _bind_updates(self):
        for variable in self.variables.values():
            variable.trace_add("write", lambda *_args: self.schedule_redraw())
        for key in ("Sounddelay_s", "SoundDuration_s", "RewardDelay_s", "ResponseWindow_s", "Rewardduration_ms"):
            self.variables[key].trace_add("write", lambda *_args: self.sync_trial_duration())
        for key in ("TACSounddelay_s", "TACSoundDuration_s", "TACRewardDelay_s", "TACResponseWindow_s", "TACRewardduration_ms"):
            self.variables[key].trace_add("write", lambda *_args: self.sync_tac_trial_duration())
        self.variables["GoWeight"].trace_add("write", lambda *_args: self.sync_weight("GoWeight"))
        self.variables["NoGoWeight"].trace_add("write", lambda *_args: self.sync_weight("NoGoWeight"))
        self.variables["TACLeftWeight"].trace_add("write", lambda *_args: self.sync_tac_weight("TACLeftWeight"))
        self.variables["TACRightWeight"].trace_add("write", lambda *_args: self.sync_tac_weight("TACRightWeight"))
        self.variables["TriggerTypeDropDown"].trace_add("write", lambda *_args: self.update_response_visibility())

    def get_parameter(self, key):
        return next(parameter for parameter in PARAMETERS if parameter.key == key)

    def on_tab_changed(self):
        if self.active_behavior() == "Lever":
            self.current_path.set(os.path.join(APP_DIR, "protocols", "lever_parameters.dat"))
        elif self.active_behavior() == "DMTS":
            self.current_path.set(os.path.join(APP_DIR, "protocols", "dmts_parameters.dat"))
        elif self.active_behavior() == "tAC":
            self.current_path.set(os.path.join(APP_DIR, "protocols", "tac_parameters.dat"))
        elif self.active_behavior() == "tAC Pretraining":
            self.current_path.set(os.path.join(APP_DIR, "protocols", "tac_pretraining_parameters.dat"))
        else:
            self.current_path.set(os.path.join(APP_DIR, "protocols", "go_nogo_parameters.dat"))
        self.schedule_redraw()

    def active_behavior(self):
        if not hasattr(self, "notebook"):
            return "Classic Go/No-go"
        return self.notebook.tab(self.notebook.select(), "text")

    def active_parameters(self):
        sections = set(COMMON_SECTIONS)
        for tab, tab_sections in BEHAVIOR_TABS:
            if tab == self.active_behavior():
                sections.update(tab_sections)
        return [parameter for parameter in PARAMETERS if parameter.section in sections]

    def choose_ni_script(self):
        self.choose_file("NICard_filename", [("MATLAB files", "*.m"), ("All files", "*.*")])

    def choose_sound_file(self):
        self.choose_file("Sound_filename", [("Sound files", "*.mat *.wav"), ("All files", "*.*")])

    def choose_file(self, key, filetypes):
        path = filedialog.askopenfilename(initialdir=APP_DIR, filetypes=filetypes)
        if path:
            self.variables[key].set(path.replace(os.sep, "/"))

    def sync_weight(self, changed_key):
        if self._syncing_weight:
            return
        value = self.parse_float(changed_key, None)
        if value is None or not 0 <= value <= 1:
            return
        paired = "NoGoWeight" if changed_key == "GoWeight" else "GoWeight"
        self._syncing_weight = True
        self.variables[paired].set(f"{1.0 - value:.6g}")
        self._syncing_weight = False

    def sync_tac_weight(self, changed_key):
        if self._syncing_weight:
            return
        value = self.parse_float(changed_key, None)
        if value is None or not 0 <= value <= 1:
            return
        paired = "TACRightWeight" if changed_key == "TACLeftWeight" else "TACLeftWeight"
        self._syncing_weight = True
        self.variables[paired].set(f"{1.0 - value:.6g}")
        self._syncing_weight = False

    def sync_trial_duration(self):
        values = [self.parse_float(key, None) for key in ("Sounddelay_s", "SoundDuration_s", "RewardDelay_s", "ResponseWindow_s", "Rewardduration_ms")]
        if any(value is None or value < 0 for value in values):
            return
        sound_end_s = values[0] + values[1]
        latest_reward_end_s = values[3] + values[2] + values[4] / 1000.0
        self.variables["TrialDuration_s"].set(f"{max(sound_end_s, latest_reward_end_s):.6g}")

    def sync_tac_trial_duration(self):
        values = [
            self.parse_float(key, None)
            for key in ("TACSounddelay_s", "TACSoundDuration_s", "TACRewardDelay_s", "TACResponseWindow_s", "TACRewardduration_ms")
        ]
        if any(value is None or value < 0 for value in values):
            return
        sound_end_s = values[0] + values[1]
        latest_reward_end_s = values[3] + values[2] + values[4] / 1000.0
        self.variables["TACTrialDuration_s"].set(f"{max(sound_end_s, latest_reward_end_s):.6g}")

    def update_response_visibility(self):
        trigger = self.variables["TriggerTypeDropDown"].get()
        for widget in self._hit_widgets:
            widget.grid() if trigger == "IRFork" else widget.grid_remove()
        for widget in self._lick_widgets:
            widget.grid() if trigger == "Lick" else widget.grid_remove()

    def reset_defaults(self):
        for parameter in self.active_parameters():
            self.variables[parameter.key].set(parameter.default)
        self.sync_trial_duration()
        self.sync_tac_trial_duration()
        self.update_response_visibility()
        self.status_var.set("Defaults restored.")

    def load_dat(self):
        path = filedialog.askopenfilename(initialdir=os.path.join(APP_DIR, "protocols"), filetypes=[("DAT files", "*.dat"), ("All files", "*.*")])
        if not path:
            return
        values = read_dat(path)
        is_lever = values.get("TaskType") == "Lever" or "LeverThreshold" in values
        is_dmts = values.get("TaskType") == "DMTS" or "DMTSDelay_s" in values
        is_tac_pre = values.get("TaskType") in {"tACPretraining", "tAC-pretraining", "tAC_pretraining"}
        is_tac = values.get("TaskType") == "tAC" or "TACLeftChannel" in values
        self.notebook.select(4 if is_tac_pre else 3 if is_tac else 2 if is_dmts else 1 if is_lever else 0)
        for key, value in values.items():
            target = self.alias_for_loaded_key(key, is_lever, is_dmts, is_tac, is_tac_pre)
            if target in self.variables:
                self.variables[target].set(value)
        self.sync_trial_duration()
        self.sync_tac_trial_duration()
        self.update_response_visibility()
        self.current_path.set(path)
        self.status_var.set(f"Loaded {os.path.basename(path)}.")

    def alias_for_loaded_key(self, key, is_lever, is_dmts=False, is_tac=False, is_tac_pre=False):
        if is_tac_pre:
            return {
                "TaskType": "TACPreTaskType",
                "MaxTrials": "TACPreMaxTrials",
                "Rewardduration_ms": "TACPreRewardduration_ms",
                "RewardGo": "TACPreRewardGo",
                "RewardGoProb": "TACPreRewardGo",
                "TACLeftChannel": "TACPreLeftChannel",
                "TACRightChannel": "TACPreRightChannel",
                "TACLeftThreshold": "TACPreLeftThreshold",
                "TACRightThreshold": "TACPreRightThreshold",
            }.get(key, key)
        if is_tac:
            return {
                "TaskType": "TACTaskType",
                "MaxTrials": "TACMaxTrials",
                "GoWeight": "TACLeftWeight",
                "NoGoWeight": "TACRightWeight",
                "GoSoundId": "TACLeftSoundId",
                "NoGoSoundId": "TACRightSoundId",
                "SoundLevel": "TACSoundLevel",
                "RandomSeed": "TACRandomSeed",
                "ITI_s": "TACITI_s",
                "ITIrandMin_s": "TACITIrandMin_s",
                "ITIrandMax_s": "TACITIrandMax_s",
                "Sounddelay_s": "TACSounddelay_s",
                "SoundDuration_s": "TACSoundDuration_s",
                "TrialDuration_s": "TACTrialDuration_s",
                "ResponseWindow_s": "TACResponseWindow_s",
                "RewardDelay_s": "TACRewardDelay_s",
                "Rewardduration_ms": "TACRewardduration_ms",
                "RewardGo": "TACRewardGo",
                "RewardGoProb": "TACRewardGo",
                "PunishNoGoFA": "TACPunishNoGoFA",
                "Minlickcount": "TACMinlickcount",
                "TACMinlickcount": "TACMinlickcount",
                "TACLeftChannel": "TACLeftChannel",
                "TACRightChannel": "TACRightChannel",
                "TACLeftThreshold": "TACLeftThreshold",
                "TACRightThreshold": "TACRightThreshold",
            }.get(key, key)
        if is_dmts:
            return {
                "TaskType": "DMTSTaskType",
                "MaxTrials": "DMTSMaxTrials",
                "GoWeight": "DMTSMatchWeight",
                "NoGoWeight": "DMTSNonMatchWeight",
                "SampleSoundId": "DMTSSampleSoundId",
                "TestSoundId": "DMTSTestSoundId",
                "DMTSRandomMatchTrials": "DMTSRandomMatchTrials",
                "DMTSSoundIds": "DMTSSoundIds",
                "SoundLevel": "DMTSSoundLevel",
                "RandomSeed": "DMTSRandomSeed",
                "ITI_s": "DMTSITI_s",
                "ITIrandMin_s": "DMTSITIrandMin_s",
                "ITIrandMax_s": "DMTSITIrandMax_s",
                "SoundDuration_s": "DMTSSoundDuration_s",
                "Delay_s": "DMTSDelay_s",
                "ResponseWindow_s": "DMTSResponseWindow_s",
                "RewardDelay_s": "DMTSRewardDelay_s",
                "Rewardduration_ms": "DMTSRewardduration_ms",
                "RewardProb": "DMTSRewardProb",
                "HITThreshold_percent": "DMTSHITThreshold_percent",
            }.get(key, key)
        if is_lever:
            return {
                "TaskType": "LeverTaskType",
                "GoSoundId": "LeverGoSoundId",
                "SoundLevel": "LeverSoundLevel",
                "Rewardduration_ms": "LeverRewardduration_ms",
                "RewardGo": "LeverRewardGo",
                "RewardGoProb": "LeverRewardGo",
            }.get(key, key)
        return {
            "RewardGo": "RewardGoProb",
            "HITThreshold_s": "HITThreshold_percent",
            "HIT_s": "HITThreshold_percent",
        }.get(key, key)

    def save_dat(self):
        errors = self.validate()
        if errors:
            messagebox.showerror("Check parameters", "\n".join(errors[:8]))
            return
        path = filedialog.asksaveasfilename(
            initialdir=os.path.dirname(self.current_path.get()) or APP_DIR,
            initialfile=os.path.basename(self.current_path.get()) or "parameters.dat",
            defaultextension=".dat",
            filetypes=[("DAT files", "*.dat"), ("All files", "*.*")],
        )
        if not path:
            return
        values = {parameter.key: self.variables[parameter.key].get().strip() for parameter in self.active_parameters()}
        write_dat(path, values, self.active_parameters())
        self.current_path.set(path)
        self.status_var.set(f"Saved {os.path.basename(path)}.")

    def validate(self):
        errors = []
        trigger = self.variables["TriggerTypeDropDown"].get()
        for parameter in self.active_parameters():
            if parameter.key == "HITThreshold_percent" and trigger != "IRFork":
                continue
            if parameter.key in {"Minlickcount", "Lickthreshold"} and trigger != "Lick":
                continue
            if parameter.kind == "float" and self.parse_float(parameter.key, None) is None:
                errors.append(f"{parameter.label} must be numeric.")
            if parameter.kind == "int" and self.parse_int(parameter.key, None) is None:
                errors.append(f"{parameter.label} must be an integer.")
        if self.active_behavior() == "Lever":
            if self.parse_float("LeverThreshold", 0) <= 0:
                errors.append("Lever threshold V must be greater than 0.")
            if self.parse_float("LeverHoldTime_s", 0) <= 0:
                errors.append("Lever hold time s must be greater than 0.")
            if self.parse_float("LeverStartDebounce_s", -1) < 0:
                errors.append("Start debounce s must be positive or 0.")
            if self.parse_float("LeverReleaseDebounce_s", -1) < 0:
                errors.append("Release debounce s must be positive or 0.")
            if self.parse_float("LeverReleaseWindow_s", -1) < 0:
                errors.append("Release window s must be positive or 0.")
            if not 0 <= self.parse_float("LeverRewardGo", -1) <= 1:
                errors.append("RewardGo Prob must be between 0 and 1.")
            return errors
        if self.active_behavior() == "DMTS":
            if self.parse_int("DMTSSampleSoundId", 0) < 1:
                errors.append("Sample sound ID must be a positive integer.")
            if self.parse_int("DMTSTestSoundId", 0) < 1:
                errors.append("Test sound ID must be a positive integer.")
            if self.variables["DMTSSoundIds"].get().strip() and not self.parse_dmts_sound_ids():
                errors.append("Sound IDs must use entries such as 1:16 or 1,2,3,4.")
            if self.parse_float("DMTSITI_s", -1) < 0:
                errors.append("ITI must be positive or 0.")
            iti_min = self.parse_float("DMTSITIrandMin_s", None)
            iti_max = self.parse_float("DMTSITIrandMax_s", None)
            if iti_min is None or iti_min < 0:
                errors.append("ITI min must be positive or 0.")
            if iti_max is None or iti_max < 0:
                errors.append("ITI max must be positive or 0.")
            if iti_min is not None and iti_max is not None and iti_min > iti_max:
                errors.append("ITI min must be smaller than or equal to ITI max.")
            if self.parse_float("DMTSSoundDuration_s", 0) <= 0:
                errors.append("Sound duration s must be greater than 0.")
            if self.parse_float("DMTSDelay_s", -1) < 0:
                errors.append("Delay s must be positive or 0.")
            if self.parse_float("DMTSResponseWindow_s", 0) <= 0:
                errors.append("Response window s must be greater than 0.")
            if self.parse_float("DMTSRewardDelay_s", -1) < 0:
                errors.append("Reward delay s must be positive or 0.")
            if self.parse_float("DMTSRewardduration_ms", -1) < 0:
                errors.append("Reward duration ms must be positive or 0.")
            if not 0 <= self.parse_float("DMTSRewardProb", -1) <= 1:
                errors.append("Reward prob must be between 0 and 1.")
            if not 0 <= self.parse_float("DMTSHITThreshold_percent", -1) <= 100:
                errors.append("Threshold of RW for HIT % must be between 0 and 100.")
            return errors
        if self.active_behavior() == "tAC":
            if self.parse_int("TACLeftSoundId", 0) < 1:
                errors.append("Left sound ID must be a positive integer.")
            if self.parse_int("TACRightSoundId", 0) < 1:
                errors.append("Right sound ID must be a positive integer.")
            if self.parse_int("TACLeftSoundId", 0) == self.parse_int("TACRightSoundId", 0):
                errors.append("Left and right sound IDs must be different.")
            if abs((self.parse_float("TACLeftWeight", 0) + self.parse_float("TACRightWeight", 0)) - 1.0) > 1e-6:
                errors.append("Left and right weights must sum to 1.")
            if self.parse_float("TACITI_s", -1) < 0:
                errors.append("ITI must be positive or 0.")
            iti_min = self.parse_float("TACITIrandMin_s", None)
            iti_max = self.parse_float("TACITIrandMax_s", None)
            if iti_min is None or iti_min < 0:
                errors.append("ITI min must be positive or 0.")
            if iti_max is None or iti_max < 0:
                errors.append("ITI max must be positive or 0.")
            if iti_min is not None and iti_max is not None and iti_min > iti_max:
                errors.append("ITI min must be smaller than or equal to ITI max.")
            if self.parse_float("TACSoundDuration_s", 0) <= 0:
                errors.append("Sound duration s must be greater than 0.")
            if self.parse_float("TACResponseWindow_s", 0) <= 0:
                errors.append("Response window s must be greater than 0.")
            if self.parse_float("TACRewardDelay_s", -1) < 0:
                errors.append("Reward delay s must be positive or 0.")
            if self.parse_float("TACRewardduration_ms", -1) < 0:
                errors.append("Reward duration ms must be positive or 0.")
            if not 0 <= self.parse_float("TACRewardGo", -1) <= 1:
                errors.append("RewardGo Prob must be between 0 and 1.")
            if self.parse_int("TACMinlickcount", 0) < 1:
                errors.append("Choice lick count must be at least 1.")
            if self.parse_float("TACLeftThreshold", 0) <= 0:
                errors.append("Left threshold must be greater than 0.")
            if self.parse_float("TACRightThreshold", 0) <= 0:
                errors.append("Right threshold must be greater than 0.")
            return errors
        if self.active_behavior() == "tAC Pretraining":
            if self.parse_int("TACPreMaxTrials", 0) < 0:
                errors.append("Max rewards must be positive or 0.")
            if self.parse_float("TACPreRewardduration_ms", -1) < 0:
                errors.append("Reward duration ms must be positive or 0.")
            if not 0 <= self.parse_float("TACPreRewardGo", -1) <= 1:
                errors.append("RewardGo Prob must be between 0 and 1.")
            if self.parse_float("TACPreLeftThreshold", 0) <= 0:
                errors.append("Left threshold must be greater than 0.")
            if self.parse_float("TACPreRightThreshold", 0) <= 0:
                errors.append("Right threshold must be greater than 0.")
            return errors
        if abs((self.parse_float("GoWeight", 0) + self.parse_float("NoGoWeight", 0)) - 1.0) > 1e-6:
            errors.append("Go and no-go weights must sum to 1.")
        if trigger == "IRFork" and not 0 <= self.parse_float("HITThreshold_percent", -1) <= 100:
            errors.append("HIT threshold % must be between 0 and 100.")
        if trigger == "Lick" and self.parse_int("Minlickcount", 0) < 1:
            errors.append("Min lick count must be at least 1.")
        if not 0 <= self.parse_float("RewardGoProb", -1) <= 1:
            errors.append("RewardGo Prob must be between 0 and 1.")
        if not 0 <= self.parse_float("Pavlov", -1) <= 1:
            errors.append("Pavlov must be between 0 and 1.")
        if not 0 <= self.parse_float("PunishNoGoFA", -1) <= 25:
            errors.append("Timeout false alarms must be between 0 and 25 seconds.")
        return errors

    def schedule_redraw(self):
        if self._pending_redraw is not None:
            self.after_cancel(self._pending_redraw)
        self._pending_redraw = self.after(40, self.redraw_preview)

    def redraw_preview(self):
        self._pending_redraw = None
        self.canvas.delete("all")
        if self.active_behavior() == "Lever":
            self.draw_lever_preview()
        elif self.active_behavior() == "DMTS":
            self.draw_dmts_preview()
        elif self.active_behavior() == "tAC":
            self.draw_tac_preview()
        elif self.active_behavior() == "tAC Pretraining":
            self.draw_tac_pretraining_preview()
        else:
            self.draw_go_nogo_preview()

    def draw_go_nogo_preview(self):
        canvas = self.canvas
        width = max(500, canvas.winfo_width())
        margin_left, margin_right, margin_top, row_gap = 132, 28, 36, 46
        timing = self.go_nogo_timing()
        total_s = max(timing["cycle"], 0.1)
        scale = (width - margin_left - margin_right) / total_s
        rows = [
            ("ITI", 0, "#6c757d", [(timing["iti_start"], timing["iti_end"], "ITI")]),
            ("Sound onset", 1, "#1f77b4", [(timing["sound_start"], timing["sound_end"], "sound")]),
            ("Response/reward window", 2, "#2ca02c", [(timing["response_start"], timing["response_end"], "response window")]),
            ("Reward possible", 3, "#17a589", [(timing["reward_start"], timing["reward_end"], "delayed reward")]),
            ("Timeout (FA)", 4, "#d62728", [(timing["timeout_start"], timing["timeout_end"], "timeout")]),
            ("Trial", 5, "#9467bd", [(timing["trial_start"], timing["trial_end"], "trial")]),
        ]
        self.draw_axis(margin_left, margin_top + row_gap * 5 + 34, width - margin_right, total_s, scale)
        for label, idx, color, spans in rows:
            y = margin_top + row_gap * idx
            canvas.create_text(margin_left - 12, y, text=label, anchor="e")
            canvas.create_line(margin_left, y, width - margin_right, y, fill="#dddddd")
            for start, end, text in spans:
                self.draw_span(margin_left, y, scale, start, end, color, text)
        self.draw_double_arrow(margin_left, margin_top + 22, scale, timing["iti_rand_min_end"], timing["iti_rand_max_end"], "#6c757d", "rand range")
        if timing["reward_delay"] > 0:
            self.draw_double_arrow(
                margin_left,
                margin_top + row_gap * 3 + 18,
                scale,
                timing["response_start"],
                timing["reward_start"],
                "#17a589",
                "RewardDelay_s",
            )
        self.summary_var.set(
            f"Go/no-go response window starts at trial start; reward delay {timing['reward_delay']:.3g} s"
        )

    def draw_lever_preview(self):
        canvas = self.canvas
        width = max(500, canvas.winfo_width())
        margin_left, margin_right, margin_top, row_gap = 132, 28, 46, 62
        crossing_time = 1.0
        hold = max(0, self.parse_float("LeverHoldTime_s", 1))
        start_debounce = max(0, self.parse_float("LeverStartDebounce_s", 0.1))
        reward_s = max(0, self.parse_float("LeverRewardduration_ms", 40) / 1000)
        reward_start = crossing_time + hold
        total_s = max(reward_start + reward_s, 2.0)
        scale = (width - margin_left - margin_right) / total_s
        signal_y, hold_y, sound_y, reward_y = margin_top, margin_top + row_gap, margin_top + row_gap * 2, margin_top + row_gap * 3
        self.draw_axis(margin_left, reward_y + 42, width - margin_right, total_s, scale)
        for label, y in (("Lever signal", signal_y), ("Above threshold", hold_y), ("Sound trigger", sound_y), ("Reward valve", reward_y)):
            canvas.create_text(margin_left - 12, y, text=label, anchor="e")
            canvas.create_line(margin_left, y, width - margin_right, y, fill="#dddddd")
        coords = []
        for t, y in [(0, signal_y + 22), (0.75, signal_y + 22), (crossing_time, signal_y - 18), (reward_start, signal_y - 18), (total_s, signal_y + 22)]:
            coords.extend((margin_left + t * scale, y))
        canvas.create_line(*coords, fill="#555555", width=3)
        canvas.create_line(margin_left, signal_y, width - margin_right, signal_y, fill="#d62728", dash=(4, 3))
        self.draw_span(margin_left, sound_y, scale, crossing_time, crossing_time + 0.05, "#1f77b4", "sound")
        self.draw_span(margin_left, hold_y, scale, crossing_time, reward_start, "#9467bd", "above threshold")
        self.draw_span(margin_left, hold_y, scale, crossing_time, crossing_time + start_debounce, "#8c564b", "accepted")
        self.draw_double_arrow(margin_left, hold_y + 18, scale, crossing_time, reward_start, "#9467bd", "LeverHoldTime_s")
        if self.variables["LeverRequireRelease"].get() == "1":
            self.draw_double_arrow(margin_left, reward_y + 18, scale, reward_start, total_s, "#d62728", "release after hold")
        self.draw_span(margin_left, reward_y, scale, reward_start, reward_start + reward_s, "#2ca02c", "reward")
        x = margin_left + crossing_time * scale
        canvas.create_line(x, margin_top - 24, x, reward_y + 18, fill="#333333", dash=(4, 3))
        canvas.create_text(x, margin_top - 28, text="threshold crossed", anchor="s")
        summary = f"Lever press accepted after {start_debounce:.3g} s above threshold; hold {hold:.3g} s"
        if self.variables["LeverRequireRelease"].get() == "1":
            summary += ", reward on release after target hold"
        else:
            summary += " before reward"
        self.summary_var.set(summary)

    def draw_tac_pretraining_preview(self):
        canvas = self.canvas
        width = max(500, canvas.winfo_width())
        margin_left, margin_right, margin_top, row_gap = 132, 28, 58, 62
        left_t = 0.25
        right_t = 0.75
        reward_s = max(0, self.parse_float("TACPreRewardduration_ms", 40) / 1000)
        total_s = 1.25
        scale = (width - margin_left - margin_right) / total_s
        left_y = margin_top
        right_y = margin_top + row_gap
        reward_y = margin_top + row_gap * 2
        self.draw_axis(margin_left, reward_y + 42, width - margin_right, total_s, scale)
        for label, y in (("Left lick", left_y), ("Right lick", right_y), ("Left reward", reward_y)):
            canvas.create_text(margin_left - 12, y, text=label, anchor="e")
            canvas.create_line(margin_left, y, width - margin_right, y, fill="#dddddd")
        self.draw_span(margin_left, left_y, scale, left_t, left_t + 0.04, "#1f77b4", "left")
        self.draw_span(margin_left, right_y, scale, right_t, right_t + 0.04, "#d62728", "right")
        self.draw_span(margin_left, reward_y, scale, right_t, right_t + reward_s, "#2ca02c", "reward")
        self.draw_double_arrow(margin_left, margin_top + row_gap + 22, scale, left_t, right_t, "#6c757d", "sequence")
        self.summary_var.set(
            "tAC pretraining: no sound, no ITI; "
            f"{self.variables['TACPreLeftChannel'].get()} lick then "
            f"{self.variables['TACPreRightChannel'].get()} lick gives left reward"
        )

    def draw_tac_preview(self):
        canvas = self.canvas
        width = max(500, canvas.winfo_width())
        margin_left, margin_right, margin_top, row_gap = 132, 28, 36, 46
        timing = self.tac_timing()
        total_s = max(timing["cycle"], 0.1)
        scale = (width - margin_left - margin_right) / total_s
        rows = [
            ("ITI", 0, "#6c757d", [(timing["iti_start"], timing["iti_end"], "ITI")]),
            ("Sound", 1, "#1f77b4", [(timing["sound_start"], timing["sound_end"], "sound")]),
            ("Choice window", 2, "#2ca02c", [(timing["response_start"], timing["response_end"], "left/right licks")]),
            ("Reward possible", 3, "#17a589", [(timing["reward_start"], timing["reward_end"], "correct choice")]),
            ("Wrong timeout", 4, "#d62728", [(timing["timeout_start"], timing["timeout_end"], "wrong")]),
            ("Trial", 5, "#9467bd", [(timing["trial_start"], timing["trial_end"], "trial")]),
        ]
        self.draw_axis(margin_left, margin_top + row_gap * 5 + 34, width - margin_right, total_s, scale)
        for label, idx, color, spans in rows:
            y = margin_top + row_gap * idx
            canvas.create_text(margin_left - 12, y, text=label, anchor="e")
            canvas.create_line(margin_left, y, width - margin_right, y, fill="#dddddd")
            for start, end, text in spans:
                self.draw_span(margin_left, y, scale, start, end, color, text)
        self.draw_double_arrow(margin_left, margin_top + 22, scale, timing["iti_rand_min_end"], timing["iti_rand_max_end"], "#6c757d", "rand range")
        if timing["reward_delay"] > 0:
            self.draw_double_arrow(
                margin_left,
                margin_top + row_gap * 3 + 18,
                scale,
                timing["response_start"],
                timing["reward_start"],
                "#17a589",
                "RewardDelay_s",
            )
        self.summary_var.set(
            "tAC: "
            f"left sound {self.variables['TACLeftSoundId'].get()} on {self.variables['TACLeftChannel'].get()}, "
            f"right sound {self.variables['TACRightSoundId'].get()} on {self.variables['TACRightChannel'].get()}, "
            f"choice >= {self.variables['TACMinlickcount'].get()} licks"
        )

    def draw_dmts_preview(self):
        canvas = self.canvas
        width = max(500, canvas.winfo_width())
        margin_left, margin_right, margin_top, row_gap = 132, 28, 36, 46
        iti = max(0.0, self.parse_float("DMTSITI_s", 2))
        iti_min = max(0.0, self.parse_float("DMTSITIrandMin_s", 0))
        iti_max = max(iti_min, self.parse_float("DMTSITIrandMax_s", iti_min))
        sound_duration = max(0.01, self.parse_float("DMTSSoundDuration_s", 0.2))
        delay = max(0.0, self.parse_float("DMTSDelay_s", 2))
        response_window = max(0.01, self.parse_float("DMTSResponseWindow_s", 2))
        reward_delay = max(0.0, self.parse_float("DMTSRewardDelay_s", 0))
        reward_duration = max(0.0, self.parse_float("DMTSRewardduration_ms", 40) / 1000.0)
        sample_start = 0.0
        sample_end = sample_start + sound_duration
        test_start = sample_end + delay
        test_end = test_start + sound_duration
        response_start = test_end
        response_end = response_start + response_window
        reward_delay_end = response_end + reward_delay
        reward_end = reward_delay_end + reward_duration
        iti_start = reward_end
        iti_end = iti_start + iti
        iti_rand_min_end = iti_end + iti_min
        iti_rand_max_end = iti_end + iti_max
        total_s = max(iti_rand_max_end, 1.0)
        scale = (width - margin_left - margin_right) / total_s
        iti_y = margin_top
        sample_y = margin_top + row_gap
        delay_y = margin_top + row_gap * 2
        test_y = margin_top + row_gap * 3
        response_y = margin_top + row_gap * 4
        reward_y = margin_top + row_gap * 5
        axis_y = reward_y + 42

        self.draw_axis(margin_left, axis_y, width - margin_right, total_s, scale)
        for label, y in (
            ("ITI", iti_y),
            ("Sample sound", sample_y),
            ("Delay", delay_y),
            ("Test sound", test_y),
            ("Response window", response_y),
            ("Reward", reward_y),
        ):
            canvas.create_text(margin_left - 12, y, text=label, anchor="e")
            canvas.create_line(margin_left, y, width - margin_right, y, fill="#dddddd")
        self.draw_span(margin_left, iti_y, scale, iti_start, iti_end, "#6c757d", "ITI")
        self.draw_double_arrow(margin_left, iti_y + 18, scale, iti_rand_min_end, iti_rand_max_end, "#6c757d", "rand range")
        self.draw_span(margin_left, sample_y, scale, sample_start, sample_end, "#1f77b4", "sample")
        self.draw_double_arrow(margin_left, delay_y + 18, scale, sample_end, test_start, "#6c757d", "delay")
        self.draw_span(margin_left, test_y, scale, test_start, test_end, "#ff7f0e", "test")
        self.draw_span(margin_left, response_y, scale, response_start, response_end, "#2ca02c", "response")
        self.draw_span(margin_left, reward_y, scale, reward_delay_end, reward_end, "#17a589", "reward")
        self.summary_var.set(
            "DMTS: "
            f"sample sound {self.variables['DMTSSampleSoundId'].get()}, "
            f"ITI after trial {iti:.3g}+{iti_min:.3g}-{iti_max:.3g} s, "
            f"delay {delay:.3g} s, test sound {self.variables['DMTSTestSoundId'].get()}, "
            f"match/non-match weights "
            f"{self.variables['DMTSMatchWeight'].get()}/{self.variables['DMTSNonMatchWeight'].get()}, "
            f"sound pool {self.variables['DMTSSoundIds'].get() or 'fixed IDs'}, "
            f"HIT threshold {self.variables['DMTSHITThreshold_percent'].get()}% RW"
        )

    def go_nogo_timing(self):
        iti = max(0, self.parse_float("ITI_s", 2))
        iti_min = max(0, self.parse_float("ITIrandMin_s", 0))
        iti_max = max(iti_min, self.parse_float("ITIrandMax_s", iti_min))
        trial_start = 0.0
        sound_start = trial_start + max(0, self.parse_float("Sounddelay_s", 0))
        sound_end = sound_start + max(0, self.parse_float("SoundDuration_s", 0.2))
        response_start = trial_start
        response_end = response_start + max(0, self.parse_float("ResponseWindow_s", 2))
        reward_delay = max(0, self.parse_float("RewardDelay_s", 0))
        reward_start = response_start + reward_delay
        reward_end = response_end + reward_delay
        reward_duration = max(0, self.parse_float("Rewardduration_ms", 40) / 1000)
        reward_pulse_end = reward_start + reward_duration
        latest_reward_pulse_end = reward_end + reward_duration
        timeout_end = response_end + max(0, self.parse_float("PunishNoGoFA", 1))
        trial_end = response_end
        iti_start = max(trial_end, sound_end, latest_reward_pulse_end)
        iti_end = iti_start + iti
        return {
            "iti": iti,
            "iti_start": iti_start,
            "iti_end": iti_end,
            "iti_rand_min_end": iti_end + iti_min,
            "iti_rand_max_end": iti_end + iti_max,
            "trial_start": trial_start,
            "sound_start": sound_start,
            "sound_end": sound_end,
            "response_start": response_start,
            "response_end": response_end,
            "reward_delay": reward_delay,
            "reward_start": reward_start,
            "reward_end": reward_end,
            "reward_pulse_end": reward_pulse_end,
            "latest_reward_pulse_end": latest_reward_pulse_end,
            "timeout_start": response_end,
            "timeout_end": timeout_end,
            "trial_end": trial_end,
            "cycle": max(iti_end + iti_max, timeout_end),
        }

    def tac_timing(self):
        iti = max(0, self.parse_float("TACITI_s", 2))
        iti_min = max(0, self.parse_float("TACITIrandMin_s", 0))
        iti_max = max(iti_min, self.parse_float("TACITIrandMax_s", iti_min))
        trial_start = 0.0
        sound_start = trial_start + max(0, self.parse_float("TACSounddelay_s", 0))
        sound_end = sound_start + max(0, self.parse_float("TACSoundDuration_s", 0.2))
        response_start = trial_start
        response_end = response_start + max(0, self.parse_float("TACResponseWindow_s", 2))
        reward_delay = max(0, self.parse_float("TACRewardDelay_s", 0))
        reward_start = response_start + reward_delay
        reward_end = response_end + reward_delay
        reward_duration = max(0, self.parse_float("TACRewardduration_ms", 40) / 1000)
        latest_reward_pulse_end = reward_end + reward_duration
        timeout_end = response_end + max(0, self.parse_float("TACPunishNoGoFA", 1))
        trial_end = response_end
        iti_start = max(trial_end, sound_end, latest_reward_pulse_end)
        iti_end = iti_start + iti
        return {
            "iti": iti,
            "iti_start": iti_start,
            "iti_end": iti_end,
            "iti_rand_min_end": iti_end + iti_min,
            "iti_rand_max_end": iti_end + iti_max,
            "trial_start": trial_start,
            "sound_start": sound_start,
            "sound_end": sound_end,
            "response_start": response_start,
            "response_end": response_end,
            "reward_delay": reward_delay,
            "reward_start": reward_start,
            "reward_end": reward_end,
            "timeout_start": response_end,
            "timeout_end": timeout_end,
            "trial_end": trial_end,
            "cycle": max(iti_end + iti_max, timeout_end),
        }

    def draw_axis(self, x0, y, x1, total_s, scale):
        self.canvas.create_line(x0, y, x1, y, fill="#333333")
        tick = 0
        while tick <= total_s + 1e-9:
            x = x0 + tick * scale
            self.canvas.create_line(x, y - 5, x, y + 5, fill="#333333")
            self.canvas.create_text(x, y + 18, text=f"{tick:g}", anchor="n")
            tick += max(0.5, round(total_s / 8, 1))
        self.canvas.create_text(x1, y + 34, text="time (s)", anchor="e")

    def draw_span(self, x0, y, scale, start, end, color, text):
        x1, x2 = x0 + start * scale, x0 + end * scale
        if x2 - x1 < 4:
            x2 = x1 + 4
        self.canvas.create_rectangle(x1, y - 13, x2, y + 13, fill=color, outline="")
        self.canvas.create_text((x1 + x2) / 2, y, text=text, fill="white")

    def draw_double_arrow(self, x0, y, scale, start, end, color, text):
        x1, x2 = x0 + start * scale, x0 + end * scale
        if x2 - x1 < 8:
            x2 = x1 + 8
        self.canvas.create_line(x1, y, x2, y, fill=color, width=2, arrow=tk.BOTH)
        self.canvas.create_text((x1 + x2) / 2, y + 10, text=text, anchor="n", fill=color)

    def parse_float(self, key, default):
        try:
            return float(self.variables[key].get())
        except (KeyError, TypeError, ValueError):
            return default

    def parse_int(self, key, default):
        value = self.parse_float(key, None)
        if value is None or not float(value).is_integer():
            return default
        return int(value)

    def parse_dmts_sound_ids(self):
        values = []
        text = self.variables["DMTSSoundIds"].get().strip()
        for item in text.replace(";", " ").replace(",", " ").split():
            if ":" in item or "-" in item:
                separator = ":" if ":" in item else "-"
                left, right = item.split(separator, 1)
                try:
                    start = int(float(left.strip()))
                    end = int(float(right.strip()))
                except Exception:
                    continue
                step = 1 if end >= start else -1
                values.extend(range(start, end + step, step))
                continue
            try:
                values.append(int(float(item)))
            except Exception:
                continue
        return [value for value in values if value > 0]


def read_dat(path):
    values = {}
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            line = line.strip()
            if line and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


def write_dat(path, values, parameters):
    aliases = {
        "LeverTaskType": "TaskType",
        "LeverGoSoundId": "GoSoundId",
        "LeverSoundLevel": "SoundLevel",
        "LeverRewardduration_ms": "Rewardduration_ms",
        "LeverRewardGo": "RewardGo",
        "DMTSTaskType": "TaskType",
        "DMTSMaxTrials": "MaxTrials",
        "DMTSMatchWeight": "GoWeight",
        "DMTSNonMatchWeight": "NoGoWeight",
        "DMTSSampleSoundId": "SampleSoundId",
        "DMTSTestSoundId": "TestSoundId",
        "DMTSRandomMatchTrials": "DMTSRandomMatchTrials",
        "DMTSSoundIds": "DMTSSoundIds",
        "DMTSSoundLevel": "SoundLevel",
        "DMTSRandomSeed": "RandomSeed",
        "DMTSITI_s": "ITI_s",
        "DMTSITIrandMin_s": "ITIrandMin_s",
        "DMTSITIrandMax_s": "ITIrandMax_s",
        "DMTSSoundDuration_s": "SoundDuration_s",
        "DMTSDelay_s": "Delay_s",
        "DMTSResponseWindow_s": "ResponseWindow_s",
        "DMTSRewardDelay_s": "RewardDelay_s",
        "DMTSRewardduration_ms": "Rewardduration_ms",
        "DMTSRewardProb": "RewardProb",
        "DMTSHITThreshold_percent": "HITThreshold_percent",
        "TACTaskType": "TaskType",
        "TACMaxTrials": "MaxTrials",
        "TACLeftWeight": "GoWeight",
        "TACRightWeight": "NoGoWeight",
        "TACLeftSoundId": "GoSoundId",
        "TACRightSoundId": "NoGoSoundId",
        "TACSoundLevel": "SoundLevel",
        "TACRandomSeed": "RandomSeed",
        "TACITI_s": "ITI_s",
        "TACITIrandMin_s": "ITIrandMin_s",
        "TACITIrandMax_s": "ITIrandMax_s",
        "TACSounddelay_s": "Sounddelay_s",
        "TACSoundDuration_s": "SoundDuration_s",
        "TACTrialDuration_s": "TrialDuration_s",
        "TACResponseWindow_s": "ResponseWindow_s",
        "TACRewardDelay_s": "RewardDelay_s",
        "TACRewardduration_ms": "Rewardduration_ms",
        "TACRewardGo": "RewardGo",
        "TACPunishNoGoFA": "PunishNoGoFA",
        "TACPreTaskType": "TaskType",
        "TACPreMaxTrials": "MaxTrials",
        "TACPreLeftChannel": "TACLeftChannel",
        "TACPreRightChannel": "TACRightChannel",
        "TACPreLeftThreshold": "TACLeftThreshold",
        "TACPreRightThreshold": "TACRightThreshold",
        "TACPreRewardduration_ms": "Rewardduration_ms",
        "TACPreRewardGo": "RewardGo",
    }
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for parameter in parameters:
            if parameter.key == "HITThreshold_percent" and values.get("TriggerTypeDropDown") != "IRFork":
                continue
            if parameter.key in {"Minlickcount", "Lickthreshold"} and values.get("TriggerTypeDropDown") != "Lick":
                continue
            key = aliases.get(parameter.key, parameter.key)
            value = values.get(parameter.key, parameter.default)
            if values.get("TACTaskType") == "tAC" and key == "TriggerTypeDropDown":
                value = "Lick"
            if values.get("TACPreTaskType") == "tACPretraining" and key == "TriggerTypeDropDown":
                value = "Lick"
            if key in {"NICard_filename", "Sound_filename"}:
                value = value.replace("\\", "/")
            handle.write(f"{key}={value}\n")
        if values.get("DMTSTaskType") == "DMTS":
            handle.write("GoSoundId=1\n")
            handle.write("NoGoSoundId=2\n")
        if values.get("TACPreTaskType") == "tACPretraining":
            handle.write("GoSoundId=0\n")
            handle.write("NoGoSoundId=0\n")
            handle.write("GoWeight=1\n")
            handle.write("NoGoWeight=0\n")
            handle.write("SoundLevel=0\n")
            handle.write("RandomSeed=0\n")
            handle.write("ITI_s=0\n")
            handle.write("ITIrandMin_s=0\n")
            handle.write("ITIrandMax_s=0\n")
            handle.write("Sounddelay_s=0\n")
            handle.write("SoundDuration_s=0\n")
            handle.write("TrialDuration_s=0\n")
            handle.write("ResponseWindow_s=0\n")
            handle.write("RewardDelay_s=0\n")
            handle.write("RewardProb=1\n")
            handle.write("PunishNoGoFA=0\n")
            handle.write("TACMinlickcount=1\n")
            handle.write("PlaySound=0\n")


if __name__ == "__main__":
    app = ProtocolGenerator()
    app.mainloop()
