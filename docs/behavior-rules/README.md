# Behavior Rules

This document describes trial start, scoring, and reward logic in `pyBEHAVIOR_v6.py`.

## Shared Concepts

Trials are created by `create_trial()` and stored in `self.trial_rows`. The currently active trial is tracked by:

- `active_trial_index`
- `active_trial_start_s`
- `active_trial_end_s`
- `active_high_start_s`
- `active_crossing_total_s`
- `active_lick_count`
- `active_reward_decided`
- `active_reward_sent`
- `active_trial_base_iti_s`
- `active_trial_extra_timeout_s`

Task state is reset by `clear_active_trial()`.

`check_trigger()` is the central dispatcher for non-lever tasks. Lever has a dedicated `check_lever_trigger_sample()` path.

## Trial Outcome Fields

Each `TrialLog.csv` row has:

- `HIT`
- `MISS`
- `CR`
- `FA`
- `ResultType`

Use these fields for behavioral outcome. Reward delivery is related but not identical, especially with `Pavlov`.

## Classic Go/No-Go

Task identifier:

```text
TaskType=ClassicGoNoGo
```

### Trial Start

Classic trial creation uses `start_classic_trial()`.

For `TriggerTypeDropDown=IRFork`:

- Trial starts on an upward threshold crossing.
- After a trial and ITI, the signal must be seen below threshold before the next upward crossing can start a new trial.

For `TriggerTypeDropDown=Lick`:

- Trial starts when the ITI has elapsed.
- Lick threshold crossings are counted during the active response window.
- A lick that starts during ITI is not meant to be the required trial-start event.

For classic Go/No-Go, `ResponseWindow_s` starts at trial start. The sound is played inside that window, so the protocol preview should not draw the response/reward window as starting after sound offset. `RewardDelay_s` delays the response-contingent GO reward from the HIT time; it does not delay or move the scoring window.

### IRFork Scoring

Functions:

- `evaluate_active_trial(sample_time_s)`
- `finish_active_trial(trial_end_s)`
- `add_active_high_interval(crossing_end_s)`
- `get_active_crossing_total(sample_time_s)`
- `get_hit_threshold_s()`

For GO trials, HIT requires total time above threshold to reach:

```text
ResponseWindow_s * HITThreshold_percent / 100
```

For no-go trials, reaching that same threshold is FA; otherwise CR.

### Lick Scoring

Functions:

- `add_active_lick()`
- `evaluate_active_lick_trial(row)`
- `finish_active_lick_trial(row, trial_end_s)`

For GO trials, HIT requires:

```text
active_lick_count >= Minlickcount
```

For no-go trials, reaching `Minlickcount` is FA; otherwise CR.

### Reward Rules

`maybe_send_go_reward()` sends response-contingent rewards for GO HITs using `RewardGo`.

`maybe_send_pavlov_reward()` can reward GO trials independently of behavior using `Pavlov`.

Current contract:

- `RewardGo` applies after a GO HIT.
- In classic Go/No-Go, `RewardDelay_s` sends that GO HIT reward at `HIT_time + RewardDelay_s`.
- `Pavlov` applies to GO trials regardless of HIT/MISS.
- `Pavlov=1` rewards every GO trial.
- HIT/MISS scoring remains behavioral even when Pavlov reward is delivered.
- No-go trials are not Pavlov rewarded.

## Lever

Task identifier:

```text
TaskType=Lever
```

Main functions:

- `check_lever_trigger_sample(sample_time_s, value, threshold)`
- `start_active_lever_trial(trigger_time_s, iti_s)`
- `evaluate_active_lever_trial(sample_time_s)`
- `finish_active_lever_trial(trial_end_s, success, hold_end_s=None)`
- `is_lever_release_success(release_time_s)`

### Trial Start

Lever trials require:

1. ITI has elapsed.
2. Lever signal has been observed below `LeverThreshold`.
3. New upward crossing occurs.
4. Signal remains above threshold for `LeverStartDebounce_s`.

The trial trigger time remains the original upward crossing time, not the later debounce-confirmation sample.

### Simple Hold Mode

When:

```text
LeverRequireRelease=0
```

Reward logic is triggered once the signal has remained above threshold for `LeverHoldTime_s`.

### Press-Hold-Release Mode

When:

```text
LeverRequireRelease=1
```

The animal must release after a valid hold. Release is accepted after the signal has stayed below threshold for `LeverReleaseDebounce_s`.

The current success check in `is_lever_release_success()` uses:

```text
LeverHoldTime_s - LeverReleaseWindow_s <= hold_s <= LeverHoldTime_s + LeverReleaseWindow_s
```

The default release window is `0.25` s.

### Lever Sound Playback

`play_next_lever_sound()` plays the configured lever sound and can repeat during a held lever state using `lever_sound_gap_s`.

## DMTS

Task identifier:

```text
TaskType=DMTS
```

Main functions:

- `start_active_dmts_trial()`
- `update_active_dmts_trial()`
- `finish_active_dmts_response()`
- `finish_active_dmts_reward_period()`
- `finish_active_dmts_miss()`
- `finish_active_dmts_timeline()`
- `choose_dmts_trial_sound_ids()`

### Trial Structure

DMTS timing is:

```text
sample sound
delay
test sound
response window
reward delay
reward period / final scoring
```

Match trials use the same sample and test sound ID. Non-match trials use different IDs. When `DMTSRandomMatchTrials=1`, IDs are chosen from `DMTSSoundIds`.

### Response Modes

DMTS can use either:

- IRFork time-above-threshold percentage.
- Lick count.

The response window starts after the test sound. For IRFork DMTS, if the fork event ends before the test sound, the trial stops as MISS after `DMTSForkGrace_s`.

### DMTS Outcomes

At the reward-period decision:

| Trial relation | Response met | Outcome |
| --- | --- | --- |
| sample == test | yes | HIT |
| sample == test | no | MISS |
| sample != test | no | CR |
| sample != test | yes | FA |

Only HIT sends reward through `maybe_send_go_reward()`. FA can add the no-go timeout.

## Reward Output

`send_output_pulse()` controls the reward/trigger digital output. It also records pulses for plotting and export through `record_trigger_pulse()`.

`trigger_output_on_crossing` must be enabled for behavioral rewards to physically send pulses.

## Extension Notes

- Do not update GUI widgets directly from behavior logic running in the acquisition thread; use `plot_queue`.
- Keep trial creation in `create_trial()` so CSV and parameter rows remain synchronized.
- If adding a new outcome or reward path, decide separately whether it changes behavior scoring, reward delivery, or both.
- For any new task, implement explicit start, update, finish, and clear behavior rather than spreading state changes across unrelated functions.


