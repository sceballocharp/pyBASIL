# Plotting

This document describes live plotting and result visualization in `pyBEHAVIOR_v6.py`.

## Responsibilities

Plotting provides:

- Live signal display for the primary behavior signal.
- Extra task-specific signal traces, such as Lever licks on `ai0` and tAC left/right licks.
- Separate overlay traces for trigger/reward output, sound output, and trial state.
- ITI shading after trial end.
- A results window with recent trial outcomes, rates, conditions, and crossing durations.
- A simple `.bin` viewer through `open_bin()`.

## Threading Contract

Plotting happens on the Tkinter main thread. Acquisition code queues drawing work:

```python
self.plot_queue.put(("plot", (times, values)))
self.plot_queue.put(("results", None))
self.plot_queue.put(("log", message))
```

`_drain_plot_queue()` consumes those messages and calls drawing functions.

## Live Plot Data Sources

| Data | State or function |
| --- | --- |
| Primary behavior trace | `time_buffer`, `data_buffer` |
| Lever lick trace | `lever_lick_buffer`, sampled from `ai0` for live plotting |
| tAC lick traces | `tac_left_buffer`, `tac_right_buffer` |
| Trigger/reward pulses | `trigger_pulses`, `record_trigger_pulse()` |
| Sound output | `sound_outputs`, `record_sound_output()` |
| Trial state | `trial_state_intervals`, `get_trial_state_values()` |
| ITI shading | `last_trial_end_time_s`, `next_trial_allowed_time_s` |

## Live Plot Functions

| Function | Role |
| --- | --- |
| `draw_plot(times, values)` | Clears and redraws the live acquisition canvas. |
| `draw_iti_shading(...)` | Shades the current ITI interval. |
| `draw_trial_state_trace(...)` | Draws trial-state overlay. |
| `draw_trigger_trace(...)` | Draws reward/trigger pulse overlay. |
| `draw_sound_trace(...)` | Draws sound output overlay. |
| `draw_since_last_trial_timer(...)` | Shows elapsed time since last trial when idle. |
| `_draw_polyline(...)` | Helper for polyline traces. |

## Axis Model

The live plot uses:

- The left axis for the primary behavior signal.
- The right-side scale for overlay traces.

Relevant GUI fields:

- `Window s`
- `Ymin1`
- `Ymax1`
- `Ymin2`
- `Ymax2`

Overlay traces are rendered into the second y-axis range. This keeps digital-style event traces visually separate from the analog behavior signal.

## ITI Shading

`draw_iti_shading()` uses:

```text
last_trial_end_time_s -> next_trial_allowed_time_s
```

The shaded region marks ITI, not the active trial. It appears only after a trial has ended and while `next_trial_allowed_time_s` is later than `last_trial_end_time_s`.

## Results Window

Functions:

- `open_results_window()`
- `close_results_window()`
- `redraw_results_window()`
- `_draw_recent_trial_strip()`
- `_draw_recent_trial_column()`
- `_draw_condition_panel()`
- `_draw_crossing_duration_panel()`
- `_draw_rate_panel()`

The results window reads `trial_rows` and `dict_across_trials`. It should not mutate behavioral state.

## Event Recording For Plotting

Reward/trigger pulses are recorded by:

```python
record_trigger_pulse(pulse_s, start_s=None)
```

Sound outputs are recorded by:

```python
record_sound_output(signal, fs, sound_id=None, start_s=None)
```

Both keep full-session lists for export and windowed lists for plotting.

## `.bin` Viewer

`open_bin()` lets the user choose a binary file and plot it using the acquisition rate from the neighboring `parameters.dat`. It is a viewer path, not part of live acquisition.

## Extension Notes

- Keep all canvas drawing in main-thread functions.
- If adding a new overlay, add both live state recording and rendering.
- If adding a new plot axis or trace class, update legend text and y-axis tick labels together.
- Avoid expensive per-sample work inside `draw_plot()`; it runs repeatedly during acquisition.


