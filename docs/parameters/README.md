# Parameters

This document describes how parameters are represented, imported, saved, and mirrored into trial/session metadata.

## Sources Of Parameters

Parameters can come from:

- GUI defaults in `_build_ui()` in `pyBEHAVIOR_v7.py`.
- Imported `.dat` files through `import_parameters_file()`.
- Generated protocol files from `protocol_generator.py`.
- Live GUI edits made before or during acquisition.

The compact user-facing parameter table is in `pyBEHAVIOR_v7_parameters.md`.

## Runtime Parameter Pipeline

| Function | Role |
| --- | --- |
| `read_parameters_file(path)` | Parses `key=value`, tab-separated, or whitespace-separated parameter files. |
| `apply_imported_parameters(params)` | Maps imported keys and aliases onto Tk variables. |
| `get_current_parameters()` | Collects the current GUI/runtime parameter state into a dictionary. |
| `write_parameters_dat()` | Writes the session-level `parameters.dat` file at session start. |
| `create_trial()` | Captures trial and parameter rows for `TrialLog.csv` and `Parameters.csv`. |
| `build_nwb_contract_parameters()` | Adds parameters to NWB/HDF5 export metadata. |

## Protocol Generator Pipeline

`protocol_generator.py` owns the `.dat` authoring GUI.

| Object or function | Role |
| --- | --- |
| `Parameter` | Dataclass describing one GUI field. |
| `PARAMETERS` | Full field registry for Classic Go/No-Go, Lever, DMTS, tAC, and shared session fields. |
| `BEHAVIOR_TABS` | Which sections appear for each protocol family. |
| `load_dat()` | Imports an existing `.dat` into generator variables, including behavior-specific aliases. |
| `validate()` | Checks numeric types and probability/range constraints. |
| `write_dat()` | Writes canonical runtime keys to disk, translating generator-specific keys. |

## Important Compatibility Rules

Some names are historical and should not be casually renamed:

- `OuputformatDropDown` is misspelled but preserved for compatibility.
- `RewardGoProb` is accepted as an alias for runtime `RewardGo`.
- `RewardProb` is used by DMTS but runtime currently maps it to the same GUI field as `RewardGo`.
- `HIT`, `HIT_s`, and `HITThreshold_s` are accepted as aliases for the HIT threshold field.
- `PunishInterval` is retained but `PunishNoGoFA` is the active false-alarm timeout.

## Adding A New Parameter

When adding a new saved parameter, update all relevant places:

1. Add the Tk variable and GUI entry in `_build_ui()`.
2. Add import mapping in `apply_imported_parameters()`.
3. Add the value to `get_current_parameters()`.
4. Add the key to `write_parameters_dat()` if it should appear in `parameters.dat`.
5. Add the value to `create_trial()` `parameter_row` if it should appear in `Parameters.csv`.
6. Add it to `build_nwb_contract_parameters()` if it should appear in NWB metadata.
7. Add it to `protocol_generator.py` `PARAMETERS` and `validate()` if protocol files should generate it.
8. Add or update example files under `protocols/`.
9. Update `pyBEHAVIOR_v7_parameters.md` and this documentation if behavior changes.

The recent `Pavlov` parameter follows this pattern.

## Parameter Blocks

`Parameters.csv` contains one row per accepted trial. The `Block` field groups consecutive trials with the same settings.

`get_parameter_block_label()` builds the block signature from `parameter_row`, ignoring trial-specific values:

- `Block`
- `trial`
- `timestamp`
- `sound_id`
- `trigger_time_s`
- `trigger_sample`
- `iti_s`

This means a newly drawn random ITI does not create a new block, but changing ITI settings such as `ITI_s`, `ITIrandMin_s`, or `ITIrandMax_s` does.

## Protocol Families

Runtime `TaskType` determines which behavior path is active:

- `ClassicGoNoGo`
- `Lever`
- `DMTS`
- `tAC`
- `tACPretraining`

The protocol generator uses behavior-specific UI keys such as `LeverRewardGo`, `DMTSRewardProb`, and `TACPreRewardGo`, then writes canonical runtime keys such as `RewardGo` and `RewardProb`.

## Pitfalls

- A parameter shown in the GUI but not added to `get_current_parameters()` will not be saved.
- A parameter saved in `parameters.dat` but not added to `apply_imported_parameters()` will not reload.
- A parameter used by analysis should be present in `Parameters.csv` and NWB metadata, not only in `parameters.dat`.
- Protocol generator validation must match runtime expectations. For probabilities, validate `0 <= value <= 1`.


