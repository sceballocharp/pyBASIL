# pyBEHAVIOR v4 Parameters

This document describes the `parameters.dat` fields used by the current protocol workflow.

`protocol_generator.py` can generate three protocol families:

- `ClassicGoNoGo`
- `Lever`
- `DMTS`

`pyBEHAVIOR_v4.py` currently imports and runs Classic Go/No-Go, Lever, and an initial DMTS sample-delay-test structure. DMTS match/non-match trial classes are not yet implemented.

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
| `ITI_s` | ITI | Base inter-trial interval. |
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

## Lever

Saved with:

```text
TaskType=Lever
```

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `TaskType` | Task type | Protocol identifier, `Lever`. |
| `LeverThreshold` | Lever threshold V | Voltage threshold crossed by the lever signal to start a lever response. |
| `LeverReadyThreshold` | Ready low V | Voltage threshold used only for lever reset/arming. After ITI, the signal must stay below this value for `LeverReadyLow_s` before a new lever trial can start. |
| `GoSoundId` | GO sound ID | Sound ID triggered when the lever threshold is crossed. |
| `SoundLevel` | Sound level | Multiplicative gain for sound playback. |
| `LeverHoldTime_s` | Lever hold time s | Time the lever signal must remain above threshold before reward logic is triggered. |
| `LeverRequireRelease` | Require release | Optional second-level lever behavior. `0` rewards once hold time is reached; `1` requires release within `LeverHoldTime_s +/- 0.25 s`. Release before or after that range is a MISS. |
| `LeverReadyLow_s` | Ready low s | Stable low duration required after ITI before a new lever press can start a trial. This prevents held-during-ITI or noisy release transitions from starting false trials. |
| `Rewardduration_ms` | Reward duration ms | Water valve/trigger pulse duration in ms. |
| `RewardGo` | RewardGo Prob | Probability that a successful lever response is rewarded, from `0` to `1`. |

## DMTS

Saved with:

```text
TaskType=DMTS
```

DMTS means delayed match to sample. The protocol generator can create these parameters and preview the timing. `pyBEHAVIOR_v4.py` now has an initial runtime structure for one sample/test pair: sample sound, delay, test sound, response window, and HIT/MISS scoring from either lick count or IR beam crossing duration. The current DMTS HIT rule is for matching sample/test sounds: if `SampleSoundId` and `TestSoundId` are the same, the response criterion is met, and the animal remains in the IR fork until the reward period, the trial is logged as a HIT. For IRFork-triggered DMTS, if the fork event ends before the reward-period decision, the trial stops immediately and is logged as a MISS.

### Task

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `TaskType` | Task type | Protocol identifier, `DMTS`. |
| `MaxTrials` | Max trials | Maximum number of accepted trials. |
| `SampleSoundId` | Sample sound ID | First/sample sound stimulus. |
| `TestSoundId` | Test sound ID | Second/test sound stimulus. |
| `SoundLevel` | Sound level | Multiplicative gain for sound playback. |
| `RandomSeed` | Random seed | Seed for reproducible trial sequence generation. |

### Timing

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `ITI_s` | ITI | Base inter-trial interval before the sample sound. |
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

`pyBEHAVIOR_v4.py` still accepts several legacy aliases:

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

| Protocol | Generated by `protocol_generator.py` | Imported by `pyBEHAVIOR_v4.py` | Runtime behavior in `pyBEHAVIOR_v4.py` |
| --- | --- | --- | --- |
| Classic Go/No-Go | Yes | Yes | Implemented. |
| Lever | Yes | Yes | Implemented. |
| DMTS | Yes | Yes | Initial sample-delay-test structure implemented; match/non-match trial classes are not yet implemented. |
