# GUI

This document describes how the main `pyBEHAVIOR_v6.py` Tkinter GUI is built and how to change the visual structure without changing acquisition, task rules, or saved-data behavior.

## Core Principle

`_build_ui()` should be treated as layout and widget wiring. It creates Tk variables, frames, entries, buttons, checkboxes, and canvases. The behavior of the experiment lives in other functions such as `start_live()`, `check_trigger()`, `evaluate_active_trial()`, `finish_active_trial()`, `save_nwb()`, and the task-specific DMTS/lever functions.

Safe GUI-only changes usually include:

- Moving a widget to another frame, row, or column.
- Renaming a visible label while keeping the same Tk variable.
- Changing widget widths or padding.
- Grouping related controls differently.
- Showing or hiding existing controls for a task type.

Risky changes include:

- Renaming a Tk variable attribute such as `self.reward_go`.
- Changing a button command.
- Changing values in a combobox without checking downstream logic.
- Removing a widget whose variable is used by parameter import/export.
- Moving task logic into `_build_ui()`.

## Main GUI Builder

The main GUI is built in:

```python
def _build_ui(self):
```

Current top-level sections:

| Section | Frame title | Main responsibility |
| --- | --- | --- |
| Left column, top | `Control And Files` | Start/stop, import parameters, NWB save, `.bin` viewer, simulation, file selectors, reward train, stim generator. |
| Left column | `Session` | User, mouse, project, output format, save root. |
| Left column | `Acquisition` | NI device, channel list, acquisition rate, plotting window, callback size, and scaling. Terminal configuration is kept internal. |
| Left column | `Trigger And Sound` | Trigger source, binary writing, output pulse, sound playback, threshold, pulse duration, sound ID/level, task-specific checkboxes. |
| Left column, center | `Live Acquisition` | Live plot canvas. For Lever, this draws the `ai6` lever/IR fork signal plus the `ai0` lick trace. For tAC, this draws separate left/right lick traces from `TACLeftChannel` and `TACRightChannel`. |
| Left column, bottom | `Output` | Text log. |
| Right parameter column, top | `Closed Loop Sequence` | Sequence length, values, weights, seed, max trials, sequence status. |
| Right parameter column, bottom | `Trial Structure` | Task timing, response criteria, reward settings, task-specific fields. |

The root frame is split into two main columns. `parameter_column` is placed at root column `1` and spans rows `0` through `5`, so the parameter panels occupy the full GUI height on the right. The operational controls, live plot, and log are placed in root column `0`. Parameter panels are arranged as two label-entry groups per row, using grid columns `0/1` and `2/3`.

`Trigger And Sound` also includes read-only status text for the selected behavior channel and active task rule. These labels are backed by `behavior_channel_var` and `behavior_rule_var`, and are refreshed by `update_behavior_readouts()`.

## Layout System

The GUI uses Tkinter `ttk` widgets with the `grid()` geometry manager for most controls.

Important patterns:

- Parent frames are usually `ttk.LabelFrame`.
- The live plot and log text use `pack()` inside their local frames.
- Most labeled entries are created by `_entry()`.
- File selector rows are created by `_file_row()`.
- Dynamic task controls are shown/hidden by `update_task_parameter_visibility()`.

Avoid mixing `pack()` and `grid()` inside the same parent frame.

## Helper Methods

### `_entry(parent, col, label, var, width=10, row=0, state="normal")`

Creates a label and entry pair, places them with `grid()`, and returns:

```python
(label_widget, entry_widget)
```

Use this helper for normal parameter fields. If the field needs to be hidden for some task types, save the returned pair:

```python
self.example_widgets = self._entry(trial, 0, "Example", self.example_var, row=4)
```

Then control it in `update_task_parameter_visibility()`.

### `_file_row(parent, row, label, var, command)`

Creates one row with:

- Label
- Entry
- Browse button

Use this only for file/path fields.

### `set_widget_pair_visible(widgets, visible, row, col)`

Shows or hides a label/entry pair created by `_entry()`. It calls `grid()` or `grid_remove()` without destroying the widgets.

This is the preferred way to conditionally show task-specific parameter fields.

### `update_task_parameter_visibility()`

Central visibility controller for fields that differ across:

- Classic Go/No-Go
- Lever
- DMTS
- Lick trigger
- IRFork trigger

If a GUI control should appear only for one task type, put that rule here instead of scattering `grid_remove()` calls elsewhere.

## Tk Variables

Most GUI state is stored in Tk variables:

- `tk.StringVar`
- `tk.BooleanVar`

These variables are not just visual. Many are used by:

- Parameter import in `apply_imported_parameters()`.
- Runtime parameter snapshot in `get_current_parameters()`.
- Trial logging in `create_trial()`.
- Behavior logic such as `check_trigger()` and scoring functions.
- Plotting and saving.

Because of that, visible labels can change freely, but variable attribute names should be treated as API.

Examples:

| Attribute | Used for |
| --- | --- |
| `self.trigger_type` | Trigger source: `IRFork`, `Lick`, `None`. |
| `self.task_type` | Runtime protocol family. |
| `self.reward_go` | Response-contingent GO reward probability. |
| `self.pavlov` | GO reward probability independent of response. |
| `self.threshold_v` | Threshold for IRFork/lever-style signals. |
| `self.lick_threshold` | Lick threshold when trigger is lick. |
| `self.lever_require_release` | Optional press-hold-release lever mode. |

## Button Commands

Buttons connect UI actions to runtime functions. Changing a button command changes behavior.

Examples:

| Button | Command |
| --- | --- |
| Start Live | `self.start_live` |
| Stop | `self.stop_live` |
| Clear | `self.clear_plot` |
| Import parameters | `self.import_parameters_file` |
| Save NWB | `self.save_nwb_placeholder` |
| Open `.bin` | `self.open_bin` |
| Results Figure | `self.open_results_window` |
| Trigger Output | `self.send_output_pulse` |
| Test Sound | `self.play_loaded_sound(use_sequence=False)` |
| ReGenerate Sequence | `self.generate_sequence` |

For layout-only edits, keep these command bindings unchanged.

## Current Dynamic Visibility Rules

`update_task_parameter_visibility()` currently handles:

- `Sound delay s` visible for non-lever, non-DMTS tasks.
- `Delay s` visible for DMTS.
- `Min licks` hidden for lever and tAC.
- `Lick thresh` visible for non-lever, non-tAC lick trigger.
- `Resp. hold %` visible for non-lever, non-tAC non-lick trigger.
- Lever hold/start debounce/release fields visible for lever.
- `Require release` checkbox visible for lever.
- `Random DMTS sounds` checkbox visible for DMTS.
- Sample/test/fork grace/sound IDs visible for DMTS.
- tAC left/right channel, threshold, and choice-lick fields visible for `TaskType=tAC`.

When adding a task-specific control, add it to this visibility function.

## Trace Callbacks

Some variables trigger UI updates when edited:

```python
var.trace_add("write", lambda *_: self.update_trial_duration())
self.task_type.trace_add("write", lambda *_: (self.update_task_parameter_visibility(), self.update_trial_duration()))
self.trigger_type.trace_add("write", lambda *_: self.update_task_parameter_visibility())
```

Trace callbacks are GUI refresh logic. Keep them lightweight. Do not run acquisition, hardware, file writes, or behavioral scoring from a trace callback.

## Safe Examples

### Move A Field To A New Row

This changes layout only:

```python
self._entry(trial, 6, "Pavlov", self.pavlov, width=6, row=1)
```

The behavior stays the same because the same `self.pavlov` variable is used.

### Rename A Label

This changes only visible text:

```python
self._entry(trial, 6, "Pavlov prob", self.pavlov, width=6, row=0)
```

Do not rename `self.pavlov` unless every import/export/runtime reference is updated.

### Move A Checkbox Between Frames

This is safe if the same variable and command are preserved:

```python
ttk.Checkbutton(new_parent, text="Require release", variable=self.lever_require_release)
```

If the checkbox is task-specific, update `update_task_parameter_visibility()` so it appears/disappears correctly.

## Adding A New GUI Parameter

If the new field is purely visual and does not affect behavior or saving:

1. Create a Tk variable.
2. Add a widget in `_build_ui()`.
3. Add visibility rules if needed.

If the new field affects runtime or should be saved, follow the full parameter checklist in [Parameters](../parameters/README.md):

1. GUI variable and widget.
2. Import mapping.
3. `get_current_parameters()`.
4. `write_parameters_dat()`.
5. Trial parameter row.
6. NWB metadata.
7. `protocol_generator.py`.
8. Example protocol `.dat`.
9. Documentation.

## GUI-Only Change Checklist

Before finishing a GUI restructuring change:

1. Confirm no behavior function was edited unless intentionally requested.
2. Confirm existing Tk variable names are unchanged.
3. Confirm button `command=` bindings are unchanged.
4. Confirm task-specific visibility still works for Classic Go/No-Go, Lever, and DMTS.
5. Run:

```powershell
.venv\Scripts\python.exe -m py_compile pyBEHAVIOR_v6.py
```

6. If possible on the rig computer, open the GUI and switch/import all three protocol families to check layout.

## Common Pitfalls

- Creating a second Tk variable for an existing parameter breaks import/export unless the rest of the code is updated.
- Forgetting to store the return value from `_entry()` makes it harder to hide/show a task-specific field.
- Changing combobox option text can break logic that compares exact strings, such as `self.trigger_type.get().strip().lower() == "lick"`.
- Destroying widgets instead of using `grid_remove()` can break later visibility toggles.
- Running hardware or file operations from `_build_ui()` makes the GUI hard to open safely.


