# Acquisition

This document describes the live acquisition path in `pyBEHAVIOR_v5.py`.

## Responsibilities

The acquisition subsystem:

- Opens NI-DAQ tasks or simulation mode.
- Reads analog samples in chunks.
- Converts raw NI reads into per-channel sample rows.
- Builds absolute sample times from acquisition rate and sample index.
- Writes continuous binary streams when enabled.
- Sends each chunk to behavior logic and plotting.
- Keeps hardware I/O out of the Tkinter main thread.

## Key Entry Points

| Function | Role |
| --- | --- |
| `start_live()` | Resets runtime state, prepares session folder, opens binary files, initializes NI or simulation mode, loads sounds, starts acquisition thread. |
| `stop_live()` | Finishes active trial when possible, closes tasks/files, optionally saves NWB. |
| `setup_tasks()` | Creates NI analog input and digital reward output tasks. |
| `close_tasks()` | Closes NI tasks defensively. |
| `acquisition_loop()` | Worker-thread loop that reads NI or simulated samples. |
| `normalize_read(raw, count)` | Normalizes NI output into rows of channel values. |
| `simulate_data(count, rate)` | Generates synthetic signal chunks for testing without hardware. |
| `handle_data(times, rows)` | Appends buffers, writes binary streams, invokes trigger logic, queues plot updates. |

## Runtime Flow

```text
Start Live button
  -> start_live()
      -> clear_buffers()
      -> prepare_session_folder()
      -> open_irfork_file()
      -> setup_tasks() or simulation mode
      -> load_sound_file() when sound playback is enabled
      -> acquisition_loop() in a worker thread

acquisition_loop()
  -> read NI chunk or simulate chunk
  -> normalize_read()
  -> handle_data()
      -> write continuous binary streams
      -> check_trigger()
      -> queue live plot update
```

## Timing Model

`acq_sample_index` is the source of acquisition time. For a chunk of `count` samples at `rate`, sample times are derived from:

```text
sample_time_s = (acq_sample_index + sample_offset) / rate
```

This makes timing independent of GUI refresh rate and mostly independent of Python scheduling jitter. Behavior rules should use these sample times, not `time.time()` or `perf_counter()`, when deciding trial timing.

## Channels

The GUI `Channels` field is parsed by `parse_channels()`. The default channel string follows the rig convention:

```text
ai6,ai5,ai1
```

The current code treats:

- Column 0 as the primary behavior signal, historically IRFork but also used for lever and lick voltage.
- Column 1 as `SoundCopy` when available.
- Additional channels may be present but are not central to current behavior scoring.

If adding a new channel-dependent feature, keep `normalize_read()`, `handle_data()`, binary writing, live plotting, and NWB export aligned.

## Threading Contract

The acquisition loop runs outside the Tk main thread. It should not directly update widgets or draw canvases. It communicates through:

```python
self.plot_queue.put((kind, payload))
```

Then `_drain_plot_queue()` handles messages on the main thread.

Common queue message kinds:

- `"plot"`: redraw live signal.
- `"log"`: append text to output log.
- `"status"`: set status indicator color.
- `"results"`: redraw results window.

## Binary Writing During Acquisition

When `Write IRFork.bin` is enabled, `open_irfork_file()` opens:

- `IRFork.bin`
- `SoundCopy.bin`
- `TrialState.bin`

`handle_data()` writes continuous double-precision samples to those files. `TrialState.bin` is generated from `trial_state_intervals`, not acquired from hardware.

## Extension Notes

- Add new live signal streams in `handle_data()` and close them in `close_irfork_file()`.
- If a new signal needs plotting, also update the plotting scale and legend.
- If a new signal needs NWB export, update `save_nwb()`, `write_nwb_contract_hdf5()`, and validation.
- Keep acquisition-time decisions based on sample time, not wall-clock GUI time.

