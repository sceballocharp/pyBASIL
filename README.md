# pyBEHAVIOR v7

`pyBEHAVIOR_v7.py` is a Python/Tkinter acquisition interface for closed-loop behavioral experiments. It runs NI-DAQ acquisition, sound playback, reward outputs, live plotting, trial logging, protocol import, and NWB export from one GUI.

The current v7 runtime supports four behavior families:

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
- Provides a **Braincodec** tab for generating/uploading LED trial files and controlling the remote PYNQ runner.
- Provides manual **Left Reward**, **Right Reward**, **100 Left**, and **100 Right** controls.
- Plots live behavior signals, task-specific lick traces, ITI shading, reward pulses, trial state, and lightweight sound epoch bars.
- Writes `BehaviorSignal.bin`, `SoundCopy.bin`, `TrialState.bin`, and tAC `LeftLick.bin`/`RightLick.bin` streams when enabled.
- Logs `parameters.dat`, `Parameters.csv`, and `TrialLog.csv`.
- Saves NWB files when `pynwb` is installed.
- Provides a results figure window for online trial summaries.

## Main Files

| File | Purpose |
| --- | --- |
| `pyBEHAVIOR_v7.py` | Main acquisition GUI and runtime logic. |
| `pyBEHAVIOR_v7_parameters.md` | Compact user-facing parameter reference. |
| `protocol_generator.py` | GUI tool for creating parameter `.dat` files. |
| `braincodec/tk_panel.py` | Reusable Braincodec tab/panel used by `pyBEHAVIOR_v7.py`. |
| `braincodec/remote_runner.py` | Small HTTP runner intended to run on the PYNQ/Braincodec machine. |
| `docs/` | Maintainer documentation split by subsystem. |
| `protocols/` | Example/generated protocol files. |
| `run_pyBEHAVIOR_v7.bat` | Windows launcher for the main app using the local `.venv`. |
| `run_protocol_generator.bat` | Windows launcher for the protocol generator. |
| `requirements.txt` | Python dependencies. |

## Quick Start

On a Windows acquisition computer:

```bat
run_pyBEHAVIOR_v7.bat
```

Or launch directly:

```bat
.venv\Scripts\python.exe pyBEHAVIOR_v7.py
```

To create or edit a protocol file:

```bat
run_protocol_generator.bat
```

## Typical Session Workflow

1. Launch `pyBEHAVIOR_v7`.
2. Set user, mouse, project, save root, NI device, channels, acquisition rate, and output format.
3. Import a protocol `.dat` file or edit the GUI parameters.
4. Choose the NI setup script and sound file.
5. Generate or regenerate the closed-loop sequence.
6. Press **Start Live**.
7. Monitor the live traces, event overlays, logs, and results window.
8. Press **Stop** to close acquisition and file handles.
9. Use **Save NWB** if the session should be exported after acquisition.

## Braincodec Classic Go/No-Go Workflow

This workflow runs a classic Go/No-Go behavioral session while the Braincodec/PYNQ board controls the LED array.

### 1. Start The PYNQ Remote Runner

Connect the PYNQ board by Ethernet/USB. In a terminal on the board, start the Braincodec runner:

```bash
cd /home/xilinx/jupyter_notebooks/sc_remote
python remote_runner.py --host 0.0.0.0 --port 8000 --workdir .
```

Leave this terminal running during the experiment.

### 2. Open pyBEHAVIOR

On the Windows acquisition computer:

```bat
cd C:\Users\Behaviour_2\Documents\GitHub\pyBEHAVIOR
.venv\Scripts\python.exe pyBEHAVIOR_v7.py
```

The GUI has two top-level tabs:

- **Behavior**
- **Braincodec**

The **Braincodec** tab handles LED-array trial generation, file upload, remote start/stop/status, and optional remote log download. The **Behavior** tab handles NI acquisition, sound, rewards, plotting, and behavioral scoring.

### 3. Configure Braincodec

Open the **Braincodec** tab.

For a classic Go/No-Go structure, select:

```text
Simple patterns
```

Choose the YAML config file, for example:

```text
config_M332_H2-190_simple-patterns.yaml
```

Then press:

```text
Detect From Config
Validate Config
```

The preview should show which LEDs are used for GO and NO-GO based on the config file.

### 4. Generate The Trials `.dat`

In **Generate Trials .dat**, set the trial sequence parameters.

Example:

```text
Trials: 800
GO %: 70
Blank %: 0
Seed: optional
```

For simple patterns, the generated trial codes are:

| Code | Meaning |
| --- | --- |
| `1` | GO |
| `2` | NO-GO |
| `0` | BLANK |

The remaining percentage after `GO %` and `Blank %` becomes NO-GO.

Press:

```text
Generate .dat
```

This creates a local two-column trials file and automatically selects it in the Braincodec tab:

```text
LightCode    SoundId
```

For now, generated trials keep the light codes as before and set `SoundId` to `0` for every trial. That means the Braincodec/PYNQ board receives light trial codes, while pyBEHAVIOR plays no sound unless a trial has a positive `SoundId`.

Behavioral trial type is defined from `LightCode`: `1` is GO, `0` is BLANK, and any other nonzero light code is treated as no-go for scoring.

### 5. Set Braincodec Run Options

Usually:

```text
Extension cables used: checked
```

Use:

```text
Wait for trigger: unchecked
```

if Braincodec should start after the remote command.

Use:

```text
Wait for trigger: checked
```

if the board should wait for an external hardware trigger before presenting LEDs.

### 6. Upload Files To The Board

Check that the PYNQ runner URL is:

```text
http://192.168.2.99:8000
```

Then press:

```text
Upload Files
```

This uploads the YAML config and generated trials `.dat` to the board.

### 7. Start Braincodec

Press:

```text
Remote Start
```

Then press:

```text
Remote Status
```

Expected states include:

```text
starting
loading
running
```

### 8. Run The Behavior Session

Return to the **Behavior** tab.

Set the normal pyBEHAVIOR parameters for the classic Go/No-Go session, then press:

```text
Start Live
```

At this stage, the Braincodec tab controls LED stimulation and the Behavior tab controls behavioral acquisition and saving.

### Recommended First Test

Before a full session, test with a short sequence:

```text
Trials: 20
GO %: 50
Blank %: 0
Wait for trigger: unchecked
```

Verify that:

- `Remote Start` works.
- The LEDs light correctly.
- `Remote Status` updates.
- pyBEHAVIOR records normally.

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
- tAC pretraining has no sound and no ITI; left-then-right sends a left reward, and right-then-left sends a right reward.

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
