# pyBEHAVIOR v6 Documentation

This folder documents the current `pyBEHAVIOR_v6.py` runtime and its protocol-generation workflow. It is written for future maintainers and coding agents that need to extend the code without rediscovering the acquisition loop, task rules, parameter contracts, plotting overlays, or saved-data format.

## Code Map

| Area | Main file | Documentation |
| --- | --- | --- |
| Live acquisition and hardware loop | `pyBEHAVIOR_v6.py` | [Acquisition](acquisition/README.md) |
| Protocol fields, `.dat` import/export, generator GUI | `pyBEHAVIOR_v6.py`, `protocol_generator.py`, `protocols/*.dat` | [Parameters](parameters/README.md) |
| Main Tkinter GUI structure and safe layout edits | `pyBEHAVIOR_v6.py` | [GUI](gui/README.md) |
| Classic Go/No-Go, Lever, DMTS scoring and reward rules | `pyBEHAVIOR_v6.py` | [Behavior Rules](behavior-rules/README.md) |
| Live trace, ITI shading, event overlays, results window | `pyBEHAVIOR_v6.py` | [Plotting](plotting/README.md) |
| Binary streams, CSV logs, NWB export contract | `pyBEHAVIOR_v6.py` | [Saving Data](saving-data/README.md) |

## Main Runtime

`BehaviorAcquisitionApp` in `pyBEHAVIOR_v6.py` owns the full GUI and runtime state. It is a single Tkinter application with a worker acquisition thread and a main-thread plot/log queue.

Important conventions:

- GUI variables are mostly `tk.StringVar` or `tk.BooleanVar` created in `_build_ui()`.
- Hardware and simulation samples flow through `acquisition_loop() -> handle_data() -> check_trigger()`.
- All GUI drawing and logging should happen through `plot_queue`, then `_drain_plot_queue()` on the Tk main thread.
- Trial rows are appended by `create_trial()` and finalized by task-specific finish functions.
- Session files are created under `save_root/UserName/behavior_data/M<MouseId>/<YYYYMMDD>/<HHMMSS>_Data`.
- `parameters.dat`, `Parameters.csv`, `TrialLog.csv`, binary streams, and NWB export must stay mutually consistent.

## Current Protocol Families

`protocol_generator.py` and `pyBEHAVIOR_v6.py` currently support:

- `ClassicGoNoGo`
- `Lever`
- `DMTS`
- `tAC`
- `tACPretraining`

The parameter reference in `pyBEHAVIOR_v6_parameters.md` is still the compact user-facing parameter table. The files in this folder describe the implementation contracts around those parameters.

## Recommended Workflow For Future Changes

1. Read the relevant subsystem README before editing.
2. Search for the function names listed in that README.
3. Keep behavioral changes in one task path at a time.
4. Update `get_current_parameters()`, `write_parameters_dat()`, `create_trial()` parameter rows, `build_nwb_contract_parameters()`, and `protocol_generator.py` whenever a new saved parameter is added.
5. Compile after Python edits:

```powershell
.venv\Scripts\python.exe -m py_compile pyBEHAVIOR_v6.py
.venv\Scripts\python.exe -m py_compile protocol_generator.py
```

6. Copy changed runtime/protocol/documentation files to the GitHub mirror when requested by the lab workflow.

