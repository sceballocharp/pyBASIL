# Saving Data

This document describes files written by `pyBEHAVIOR_v6.py` and the export contract used for downstream analysis.

## Session Folder

`prepare_session_folder()` creates the session path:

```text
<SaveRoot>/<UserName>/behavior_data/M<MouseId>/<YYYYMMDD>/<HHMMSS>_Data
```

It also writes `parameters.dat` and initializes:

- `trial_log_path`
- `parameters_log_path`

## Files Written During A Session

| File | Writer | Description |
| --- | --- | --- |
| `parameters.dat` | `write_parameters_dat()` | Session-level parameter snapshot written at session start. |
| `TrialLog.csv` | `write_trial_log()` | Trial-by-trial behavioral outcomes and timing. |
| `Parameters.csv` | `write_parameters_csv()` | Trial-by-trial parameter rows and block labels. |
| `BehaviorSignal.bin` | `handle_data()` | Continuous selected behavior signal as binary doubles. Older sessions may contain the legacy name `IRFork.bin`. |
| `SoundCopy.bin` | `handle_data()` | Continuous recorded sound-copy channel as binary doubles. |
| `TrialState.bin` | `handle_data()` | Continuous 0/1 trial-state trace as binary doubles. |
| `*.nwb` | `save_nwb()` | NWB export with acquisition, stimulus, trial, and compatibility datasets. |

## CSV Writing

`write_csv(path, rows)` is the shared CSV helper.

It is used by:

- `write_trial_log()`
- `write_parameters_csv()`

The helper writes nothing if `path` or `rows` is empty. Field names come from the first row, so all rows in a given CSV should use a stable schema.

## TrialLog.csv

Trial rows are created by `create_trial()` and finalized by task-specific finish functions.

Important fields:

- `trial`
- `timestamp`
- `trigger_time_s`
- `trial_end_s`
- `trigger_sample`
- `crossing_duration_s`
- `TrialType`
- `HIT`
- `MISS`
- `CR`
- `FA`
- `ResultType`
- `sound_id`
- `sample_sound_id`
- `test_sound_id`
- `lick_count`

## Parameters.csv

Parameter rows are created inside `create_trial()`. They capture the active protocol settings at trial creation time and include a `Block` label from `get_parameter_block_label()`.

`Block` is intended to group trials by stable protocol settings, not by trial number.

## Binary Stream Contract

Binary files are written as little-endian double values using `struct.pack("<d", value)`.

Readers should use the acquisition rate from `parameters.dat` to reconstruct sample times.

Current binary streams:

- `BehaviorSignal.bin`: selected behavior signal used for trial detection and scoring.
- `SoundCopy.bin`: sound-copy signal, or zeros when the column is unavailable.
- `TrialState.bin`: synthetic trial-state trace.

## Sound And Reward Event State

These in-memory lists support plotting and export:

- `full_trigger_pulses`
- `full_sound_outputs`
- `trigger_pulses`
- `sound_outputs`

`full_*` lists are session-wide. Non-full lists are windowed for live plotting.

## NWB Export

Main functions:

- `save_nwb(silent=False)`
- `write_nwb_contract_hdf5(path, rate, trial_rows)`
- `build_nwb_contract_parameters(rate, exported_trial_count=None)`
- `validate_nwb_contract_hdf5(path)`
- `get_nwb_contract_trial_rows(sample_count, rate, sound_epochs)`
- `build_contract_sound_epochs(sample_count, rate)`
- `build_contract_sound_traces(sample_count, rate, sound_epochs)`
- `build_contract_trial_type_trace(ir_sample_count, ir_rate, trial_rows, sound_epochs)`

`save_nwb()` first writes an NWB file through PyNWB, then adds GUI-compatible HDF5 datasets and validates them.

## NWB/HDF5 Compatibility Paths

`validate_nwb_contract_hdf5()` expects paths such as:

- `/acquisition/IRFork/data`
- `/acquisition/BehaviorSignal/data`
- `/stimulus/presentation/SoundCopy/data`
- `/acquisition/Parameters/key`
- `/acquisition/Parameters/value`

The NWB export keeps `/acquisition/IRFork/data` as a compatibility trace but also writes `/acquisition/BehaviorSignal/data` as the current descriptive name. If new datasets are required by downstream tools, add them in `write_nwb_contract_hdf5()` and update validation.

## Trial Anchors In NWB

The export code tries to align trial rows to sound epochs when available. `NWBTrialAnchor` is currently documented as:

```text
sound_epoch_start_or_trigger_time
```

Rows outside the continuous recording can be skipped during export, and the exported-trial count is stored in NWB parameters.

## Data-Saving Pitfalls

- If a new parameter affects analysis, include it in `parameters.dat`, `Parameters.csv`, and NWB metadata.
- If a new trial outcome is added, update CSV rows and NWB trial-type conversion helpers.
- If a new continuous stream is added, write it, close it, export it, and validate it.
- Avoid changing existing field names unless downstream analysis is updated at the same time.


