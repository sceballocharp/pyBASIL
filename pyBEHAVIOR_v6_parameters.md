# pyBEHAVIOR v6 Parameters

This document describes the `parameters.dat` fields used by the current protocol workflow.

`protocol_generator.py` can generate four protocol families:

- `ClassicGoNoGo`
- `Lever`
- `DMTS`
- `tAC`
- `tACPretraining`

`pyBEHAVIOR_v6.py` currently imports and runs Classic Go/No-Go, Lever, DMTS, tAC, and tAC pretraining. DMTS can generate match and non-match trial types, with random sample/test sounds from a sound ID list such as `1:16`. tAC is a two-alternative choice task with one sound followed by left/right lick choice. tAC pretraining is a shaping mode with no sound and no ITI, where left-then-right triggers a left reward and right-then-left triggers a right reward.

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

The GUI `Channels` field should include `ai6,ai5,ai1,ai0` for the current rig layout. Runtime behavior signal selection is trigger-dependent: IRFork and Lever use `ai6`; Lick uses `ai0`; tAC defaults to left `ai0` and right `ai1`; SoundCopy uses `ai5`. During Lever tasks, `ai0` is also shown as a live lick trace, but lever trial start/reward logic still uses `ai6`. The selected behavior signal is written to `BehaviorSignal.bin` and recorded as `BehaviorSignalChannel` in session metadata.

Reward outputs use two digital lines. Left/default rewards use `Device/port2/line6`; right rewards use `Device/port2/line7`. The GUI has manual **Left Reward** and **Right Reward** buttons for single pulses, plus **100 Left** and **100 Right** buttons for reward-train testing.

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
| `TrialDuration_s` | Trial duration s | Saved compatibility value from the generator; computed as the longer of sound end or latest possible delayed reward end. Classic runtime scoring uses `ResponseWindow_s` from trial start. |
| `ResponseWindow_s` | Response window s | Classic Go/No-Go scoring window. It starts at trial start, not after the sound. |
| `RewardDelay_s` | Reward delay s | For classic GO HITs, delay from the moment the HIT criterion is reached to the reward pulse. DMTS uses it as the delay from response-window end to reward delivery. |

### Outcome

| Parameter | GUI label | Used when | Meaning |
| --- | --- | --- | --- |
| `Rewardduration_ms` | Reward duration ms | All response modes | Water valve/trigger pulse duration in ms. |
| `RewardGo` | RewardGo Prob | GO HITs | Saved reward probability key for GO HITs, from `0` to `1`. `RewardGoProb` is accepted as an import alias. |
| `Pavlov` | Pavlov | GO trials | Probability that a GO trial receives reward independent of lick count or IR crossing. `0` disables Pavlov reward; `1` rewards every GO trial. HIT/MISS scoring still reflects the animal response. |
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

A response is scored when the signal crosses above `Lickthreshold` at least `Minlickcount` times during the response window. In classic Go/No-Go, that response window starts at trial start, so the sound is shown inside the scoring window when the protocol preview is drawn. If `RewardDelay_s` is greater than zero, a GO HIT is scored immediately but the output reward pulse is sent at `HIT_time + RewardDelay_s`.

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
| `LeverRequireRelease` | Require release | Optional second-level lever behavior. `0` rewards once hold time is reached; `1` rewards when the animal releases. The release timing determines MISS, bonus HIT, or normal HIT. |
| `LeverReleaseWindow_s` | Release window s | Timing window around `LeverHoldTime_s`. With Require release enabled, releases before `LeverHoldTime_s - LeverReleaseWindow_s` are MISS. Releases within `LeverHoldTime_s +/- LeverReleaseWindow_s` are HIT and send three reward pulses total. Releases later than this window still count as HIT and send the normal single reward pulse. |
| `Rewardduration_ms` | Reward duration ms | Water valve/trigger pulse duration in ms. |
| `RewardGo` | RewardGo Prob | Probability that a successful lever response is rewarded, from `0` to `1`. |

Lever trials also require a clean reset between trials: after the trial ends and the ITI has elapsed, the lever signal must be observed below `LeverThreshold` before the next upward crossing can start a new trial. A new lever press must then remain above `LeverThreshold` for `LeverStartDebounce_s` before the trial is accepted, preventing single-sample noise from starting trials. The live plot shows both the lever/IR fork signal from `ai6` and licks from `ai0`; only `ai6` controls the lever behavior.

With Require release enabled, `LeverReleaseWindow_s` controls the timing zone around the target hold time. For example, with `LeverHoldTime_s=1.0` and `LeverReleaseWindow_s=0.25`, releasing before `0.75` s is MISS, releasing from `0.75` to `1.25` s is HIT with three reward pulses total, and releasing after `1.25` s remains a HIT but sends only one reward pulse.

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

## tAC

Saved with:

```text
TaskType=tAC
```

tAC means two-alternative choice. Trials start automatically when the ITI has elapsed, like lick-triggered Classic Go/No-Go. There is no IRFork/fork-entry requirement for this task. The closed-loop sequence defines which sound is presented: the first sequence value is the left-correct sound and the second sequence value is the right-correct sound.

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `GoSoundId` | Left sound ID | Sound ID for left-correct trials. |
| `NoGoSoundId` | Right sound ID | Sound ID for right-correct trials. |
| `GoWeight` | Left weight | Relative probability of left-correct trials. |
| `NoGoWeight` | Right weight | Relative probability of right-correct trials. |
| `TACLeftChannel` | Left chan | AI channel used for left licks. Default `ai0`. |
| `TACRightChannel` | Right chan | AI channel used for right licks. Default `ai1`. |
| `TACLeftThreshold` | Left thresh | Voltage threshold for left lick crossings. |
| `TACRightThreshold` | Right thresh | Voltage threshold for right lick crossings. |
| `TACMinlickcount` | Choice licks | Number of crossings required for a side choice. |
| `TACLeftBinary` | saved metadata | Continuous left lick file, `LeftLick.bin`, written for tAC sessions. |
| `TACRightBinary` | saved metadata | Continuous right lick file, `RightLick.bin`, written for tAC sessions. |

tAC outcomes:

| Event | Outcome |
| --- | --- |
| Correct side reaches `TACMinlickcount` first | HIT |
| Wrong side reaches `TACMinlickcount` first | FA |
| No side reaches the criterion before response-window end | MISS |

Correct choices use `RewardGo` and `RewardDelay_s`. Wrong choices use `PunishNoGoFA` as the timeout.

tAC reward outputs:

| Correct side | Digital output |
| --- | --- |
| left | `Dev1/port2/line6` |
| right | `Dev1/port2/line7` |

The actual device name comes from the GUI `Device` field, so `Dev1` changes if that field changes. Session metadata stores `LeftRewardLine=port2/line6` and `RightRewardLine=port2/line7`.

## tAC Pretraining

Saved with:

```text
TaskType=tACPretraining
```

tAC pretraining is an exploration/shaping mode for tAC. It uses the same left/right lick channels and thresholds as tAC, but does not play sounds, does not use ITI, and does not use a response window.

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `TACLeftChannel` | Left lick channel | Channel for the first lick in the required sequence. Default `ai0`. |
| `TACRightChannel` | Right lick channel | Channel for the second lick in the required sequence. Default `ai1`. |
| `TACLeftThreshold` | Left threshold V | Voltage threshold for detecting left upward crossings. |
| `TACRightThreshold` | Right threshold V | Voltage threshold for detecting right upward crossings. |
| `Rewardduration_ms` | Reward duration ms | Duration of the left reward pulse. |
| `RewardGo` | RewardGo Prob | Reward probability for completed alternating lick sequences. Default `1`. |
| `MaxTrials` | Max rewards | Maximum number of rewarded alternating lick events. `0` means unlimited. |

Runtime rule:

```text
left lick -> right lick -> left reward on Device/port2/line6
right lick -> left lick -> right reward on Device/port2/line7
```

Each completed alternating sequence is logged as a `tAC-pretraining` HIT event in `TrialLog.csv`.

## Import Compatibility

`pyBEHAVIOR_v6.py` still accepts several legacy aliases:

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

| Protocol | Generated by `protocol_generator.py` | Imported by `pyBEHAVIOR_v6.py` | Runtime behavior in `pyBEHAVIOR_v6.py` |
| --- | --- | --- | --- |
| Classic Go/No-Go | Yes | Yes | Implemented. |
| Lever | Yes | Yes | Implemented. |
| DMTS | Yes | Yes | Initial sample-delay-test structure implemented with same-ID matching and optional randomized same-ID sound lists. |
| tAC | Yes | Yes | Implemented as automatic-start left/right lick choice with no fork/IR requirement. |
| tACPretraining | Yes | Yes | Implemented as alternating lick shaping with no sound and no ITI. |
