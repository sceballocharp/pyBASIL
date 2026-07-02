# pyBEHAVIOR v5 Parameters

This document describes the `parameters.dat` fields used by the current protocol workflow.

`protocol_generator.py` can generate three protocol families:

- `ClassicGoNoGo`
- `Lever`
- `DMTS`

`pyBEHAVIOR_v5.py` currently imports and runs Classic Go/No-Go, Lever, and a DMTS sample-delay-test structure. DMTS can generate match and non-match trial types, with random sample/test sounds from a sound ID list such as `1:16`.

## Common Parameters

These are shared by every protocol tab.

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `UserName` | User | User/session owner name used in the output path. |
| `MouseId` | Mouse ID | Mouse identifier, saved under `M<MouseId>`. |
| `ProjectName` | Project | Project label stored with the session metadata. |
| `NICard_filename` | NI script | Path to the NI setup script. |
| `Sound_filename` | Sound file | Path to the sound `.mat` or `.wav` file. |
| `frec` | Acquisition rate Hz | Acquisition sampling rate in Hz. |
| `bin` | Callback/bin s | Acquisition callback/read chunk duration in seconds. |
| `TriggerTypeDropDown` | Trigger | Response signal source: `IRFork`, `Lick`, or `None`. |
| `OuputformatDropDown` | Output format | Output format selector. Note the historical misspelling is preserved for compatibility. |

## Classic Go/No-Go

Saved with:

```text
TaskType=ClassicGoNoGo
```

### Task

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `TaskType` | Task type | Protocol identifier, `ClassicGoNoGo`. |
| `MaxTrials` | Max trials | Maximum number of accepted trials. `0` means no limit. |
| `GoWeight` | Go weight | Relative probability weight for GO trials. |
| `NoGoWeight` | No-go weight | Relative probability weight for no-go trials. |
| `GoSoundId` | Go sound ID | Sound ID used for GO trials. |
| `NoGoSoundId` | No-go sound ID | Sound ID used for no-go trials. |
| `SoundLevel` | Sound level | Multiplicative gain for sound playback. |
| `RandomSeed` | Random seed | Seed for reproducible sound/trial sequence generation. |

### Timing

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `ITI_s` | ITI | Base inter-trial interval measured from trial end. |
| `ITIrandMin_s` | rand min | Minimum random ITI addition. |
| `ITIrandMax_s` | rand max | Maximum random ITI addition. |
| `Sounddelay_s` | Sound delay s | Delay from trial start to sound onset. |
| `SoundDuration_s` | Sound duration s | Duration of the sound stimulus. |
| `TrialDuration_s` | Trial duration s | Computed as sound delay + sound duration + reward delay + response window. |
| `ResponseWindow_s` | Response window s | Window during which behavior is scored. |
| `RewardDelay_s` | Reward delay s | Delay before the response/reward phase. |

### Outcome

| Parameter | GUI label | Used when | Meaning |
| --- | --- | --- | --- |
| `Rewardduration_ms` | Reward duration ms | All response modes | Water valve/trigger pulse duration in ms. |
| `RewardGo` | RewardGo Prob | GO HITs | Saved reward probability key for GO HITs, from `0` to `1`. `RewardGoProb` is accepted as an import alias. |
| `PunishNoGoFA` | Timeout false alarms | no-go FA | Timeout duration after a no-go false alarm, in seconds. |
| `HITThreshold_percent` | HIT threshold % | `TriggerTypeDropDown=IRFork` | Percentage of `ResponseWindow_s` that the IR beam signal must remain above threshold to count as HIT/FA. |
| `Minlickcount` | Min lick count | `TriggerTypeDropDown=Lick` | Number of upward crossings over `Lickthreshold` required to count as HIT/FA. |
| `Lickthreshold` | Signal threshold V | `TriggerTypeDropDown=Lick` | Voltage threshold used to detect lick crossings. |

### Response Mode Distinction

For IR beam scoring:

```text
TriggerTypeDropDown=IRFork
HITThreshold_percent=<0-100>
```

`HITThreshold_percent` is converted to seconds:

```text
required_time_above_threshold = ResponseWindow_s * HITThreshold_percent / 100
```

For lick-port scoring:

```text
TriggerTypeDropDown=Lick
Lickthreshold=<volts>
Minlickcount=<count>
```

A response is scored when the signal crosses above `Lickthreshold` at least `Minlickcount` times during the response window.

Classic Go/No-Go starts trials differently depending on the trigger source. With `TriggerTypeDropDown=IRFork`, after the trial ends and the ITI has elapsed, the trigger signal must be observed below the active threshold before the next upward crossing can start a new trial. With `TriggerTypeDropDown=Lick`, the next trial starts as soon as the ITI has elapsed; licks are then counted during the response window.

## Lever

Saved with:

```text
TaskType=Lever
```

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `TaskType` | Task type | Protocol identifier, `Lever`. |
| `LeverThreshold` | Lever threshold V | Voltage threshold crossed by the lever signal to start a lever response. |
| `GoSoundId` | GO sound ID | Sound ID triggered when the lever threshold is crossed. |
| `SoundLevel` | Sound level | Multiplicative gain for sound playback. |
| `LeverHoldTime_s` | Lever hold time s | Time the lever signal must remain above threshold before reward logic is triggered. |
| `LeverStartDebounce_s` | Start debounce s | Time a new upward crossing must remain above `LeverThreshold` before the trial is accepted. Default is `0.1` s. |
| `LeverReleaseDebounce_s` | Release debounce s | Time the lever signal must remain below `LeverThreshold` before a release is accepted. Default is `0.05` s. This can be changed live during behavior. |
| `LeverRequireRelease` | Require release | Optional second-level lever behavior. `0` rewards once hold time is reached; `1` rewards when the animal releases after crossing `LeverHoldTime_s`. Releasing before `LeverHoldTime_s` is a MISS. |
| `LeverReleaseWindow_s` | Release window s | Reserved lever tolerance parameter. Currently saved/imported for compatibility but not used while release rewards are based only on `hold_s >= LeverHoldTime_s`. |
| `Rewardduration_ms` | Reward duration ms | Water valve/trigger pulse duration in ms. |
| `RewardGo` | RewardGo Prob | Probability that a successful lever response is rewarded, from `0` to `1`. |

Lever trials also require a clean reset between trials: after the trial ends and the ITI has elapsed, the lever signal must be observed below `LeverThreshold` before the next upward crossing can start a new trial. A new lever press must then remain above `LeverThreshold` for `LeverStartDebounce_s` before the trial is accepted, preventing single-sample noise from starting trials.

## DMTS

Saved with:

```text
TaskType=DMTS
```

DMTS means delayed match to sample. The protocol generator can create these parameters and preview the timing. At the beginning of a live session, the closed-loop sequence is regenerated as DMTS trial types: `1` is match and `2` is non-match. Match trials use the same sound ID for sample and test. Non-match trials use different sample and test sound IDs. If `DMTSRandomMatchTrials` is enabled, those IDs are chosen from `DMTSSoundIds`; if it is disabled, the fixed `SampleSoundId`/`TestSoundId` fields are used. Match trials score as HIT when the response criterion is met and MISS when it is not met. Non-match trials score as CR when the response criterion is not met and FA when it is met; FA adds the no-go timeout. HIT, CR, and FA are assigned only if the trial reaches the reward-period decision. For IRFork-triggered DMTS, if the fork event ends before the test sound is presented, the trial stops as a MISS.

DMTS trial starts use the same clean-reset rule as Classic Go/No-Go: after the trial ends and the ITI has elapsed, the trigger signal must be observed below threshold before a new upward crossing can start the next trial.

### Task

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `TaskType` | Task type | Protocol identifier, `DMTS`. |
| `MaxTrials` | Max trials | Maximum number of accepted trials. |
| `GoWeight` | Match weight | Relative probability for DMTS trial type `1`, match. |
| `NoGoWeight` | Non-match weight | Relative probability for DMTS trial type `2`, non-match. |
| `GoSoundId` | Match trial type | Fixed runtime value `1` for match trials. |
| `NoGoSoundId` | Non-match trial type | Fixed runtime value `2` for non-match trials. |
| `SampleSoundId` | Sample sound ID | First/sample sound stimulus. |
| `TestSoundId` | Test sound ID | Second/test sound stimulus. |
| `DMTSRandomMatchTrials` | Random DMTS sounds | `0` uses fixed `SampleSoundId`/`TestSoundId`; `1` chooses match and non-match sample/test sounds from `DMTSSoundIds`. |
| `DMTSSoundIds` | Sound IDs | Sound ID list for randomized DMTS sounds. `1:16` selects IDs from 1 through 16. Match trials use one ID twice; non-match trials use two different IDs. Comma/space lists such as `1,2,5,9` are also accepted. |
| `SoundLevel` | Sound level | Multiplicative gain for sound playback. |
| `RandomSeed` | Random seed | Seed for reproducible trial sequence generation. |

### Timing

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `ITI_s` | ITI | Base inter-trial interval measured from trial end before the next sample sound can start. |
| `ITIrandMin_s` | ITI min | Minimum random ITI addition. |
| `ITIrandMax_s` | ITI max | Maximum random ITI addition. |
| `SoundDuration_s` | Sound duration s | Duration of each sound stimulus. |
| `Delay_s` | Delay s | Delay between the end of sample sound and start of test sound. |
| `ResponseWindow_s` | Response window s | Window after the test sound during which behavior is scored. |
| `RewardDelay_s` | Reward delay s | Delay from response-window end to reward delivery. |
| `DMTSForkGrace_s` | Fork grace s | IRFork-only grace/debounce duration. The fork signal must remain below threshold for this long before the trial stops as a MISS. |

### Outcome

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `Rewardduration_ms` | Reward duration ms | Water valve/trigger pulse duration in ms. |
| `RewardProb` | Reward prob | Probability that a correct DMTS response is rewarded, from `0` to `1`. |
| `HITThreshold_percent` | Threshold of RW for HIT % | Percentage of the response window required for HIT classification. |

## Import Compatibility

`pyBEHAVIOR_v5.py` still accepts several legacy aliases:

| Legacy key | Current meaning |
| --- | --- |
| `OutputformatDropDown` | Alias for `OuputformatDropDown`. |
| `HIT`, `HIT_s`, `HITThreshold_s` | Legacy names for the HIT threshold field. |
| `RewardGoProb` | Alias for the saved `RewardGo` reward probability field. |
| `PunishInterval` | Legacy punishment field; prefer `PunishNoGoFA`. |

## Parameter Blocks

`Parameters.csv` stores one row per accepted trial. The `Block` column groups consecutive trials that used the same protocol/settings. It is intended to change only when an experiment parameter changes, not simply because a new trial starts.

Trial-specific fields such as `trial`, `timestamp`, `sound_id`, `trigger_time_s`, `trigger_sample`, and the drawn per-trial `iti_s` are ignored when assigning block labels. The ITI settings (`ITI_s`, `ITIrandMin_s`, and `ITIrandMax_s`) are still part of the block signature, so changing the protocol's ITI configuration starts a new block.

## Runtime Status

| Protocol | Generated by `protocol_generator.py` | Imported by `pyBEHAVIOR_v5.py` | Runtime behavior in `pyBEHAVIOR_v5.py` |
| --- | --- | --- | --- |
| Classic Go/No-Go | Yes | Yes | Implemented. |
| Lever | Yes | Yes | Implemented. |
| DMTS | Yes | Yes | Initial sample-delay-test structure implemented with same-ID matching and optional randomized same-ID sound lists. |
