# pyBEHAVIOR v6

`pyBEHAVIOR_v6.py` is a Python/Tkinter acquisition interface for closed-loop behavioral experiments. It runs NI-DAQ acquisition, sound playback, reward outputs, live plotting, trial logging, protocol import, and NWB export from one GUI.

The current v6 runtime supports four behavior families:

- Classic Go/No-Go
- Lever
- DMTS
- tAC
- tAC pretraining

## What It Does

- Runs live analog acquisition from a National Instruments device or simulation mode.
- Selects the active behavior signal by task and trigger type.
- Starts and scores Classic Go/No-Go, Lever, DMTS, tAC, and tAC pretraining events.
- Plays sounds from MATLAB `.mat` sound banks or waveform files.
- Sends left and right reward pulses through NI digital outputs.
- Provides manual **Left Reward**, **Right Reward**, **100 Left**, and **100 Right** controls.
- Plots live behavior signals, task-specific lick traces, ITI shading, reward pulses, trial state, and lightweight sound epoch bars.
- Writes `BehaviorSignal.bin`, `SoundCopy.bin`, `TrialState.bin`, and tAC `LeftLick.bin`/`RightLick.bin` streams when enabled.
- Logs `parameters.dat`, `Parameters.csv`, and `TrialLog.csv`.
- Saves NWB files when `pynwb` is installed.
- Provides a results figure window for online trial summaries.

## Main Files

| File | Purpose |
| --- | --- |
| `pyBEHAVIOR_v6.py` | Main acquisition GUI and runtime logic. |
| `pyBEHAVIOR_v6_parameters.md` | Compact user-facing parameter reference. |
| `protocol_generator.py` | GUI tool for creating parameter `.dat` files. |
| `docs/` | Maintainer documentation split by subsystem. |
| `protocols/` | Example/generated protocol files. |
| `run_pyBEHAVIOR_v6.bat` | Windows launcher for the main app using the local `.venv`. |
| `run_protocol_generator.bat` | Windows launcher for the protocol generator. |
| `requirements.txt` | Python dependencies. |

## Quick Start

On a Windows acquisition computer:

```bat
run_pyBEHAVIOR_v6.bat
```

Or launch directly:

```bat
.venv\Scripts\python.exe pyBEHAVIOR_v6.py
```

To create or edit a protocol file:

```bat
run_protocol_generator.bat
```

## Typical Session Workflow

1. Launch `pyBEHAVIOR_v6`.
2. Set user, mouse, project, save root, NI device, channels, acquisition rate, and output format.
3. Import a protocol `.dat` file or edit the GUI parameters.
4. Choose the NI setup script and sound file.
5. Generate or regenerate the closed-loop sequence.
6. Press **Start Live**.
7. Monitor the live traces, event overlays, logs, and results window.
8. Press **Stop** to close acquisition and file handles.
9. Use **Save NWB** if the session should be exported after acquisition.

## Hardware Defaults

The current rig convention is:

| Signal | Default channel/line | Direction | Role |
| --- | --- | --- | --- |
| Behavior IR/lever | `Dev1/ai6` | Input | IRFork and Lever behavior signal. |
| SoundCopy | `Dev1/ai5` | Input | Recorded sound-copy channel. |
| Right/tAC lick | `Dev1/ai1` | Input | tAC right lick channel by default. |
| Lick/left tAC | `Dev1/ai0` | Input | Lick-trigger signal, tAC left lick channel, and live Lever lick trace. |
| Left reward | `Dev1/port2/line6` | Output | Default/left reward valve. |
| Right reward | `Dev1/port2/line7` | Output | Right reward valve for tAC and manual right reward. |

The GUI `Device` field supplies the device name, so `Dev1` can be changed for another NI device.

## Behavior Highlights

- Classic Go/No-Go can score by IRFork time-above-threshold or lick count.
- Lever can run simple hold mode or optional press-hold-release mode.
- Lever release mode uses `LeverHoldTime_s +/- LeverReleaseWindow_s` as a bonus zone: releases inside the window send three reward pulses total, late releases still count as HIT with one pulse, and too-early releases are MISS.
- DMTS presents sample, delay, test, response window, then reward period.
- tAC starts automatically after ITI and rewards left-correct trials on `port2/line6` and right-correct trials on `port2/line7`.
- tAC pretraining has no sound and no ITI; a left lick followed by a right lick sends a left reward and logs one HIT event.

## Documentation

Detailed maintainer docs live in [docs/README.md](docs/README.md):

- acquisition and channels
- parameter import/export
- behavior rules
- plotting
- GUI layout
- saving data and NWB export

## Notes

- Keep large raw data folders out of version control unless they are deliberate examples.
- Check hardware channel names before running on a new rig.
- If the app opens but hardware controls do not work, verify the NI-DAQmx driver, the `nidaqmx` Python package, and the selected device name.
