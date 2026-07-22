import nidaqmx
from nidaqmx.constants import AcquisitionType

with nidaqmx.Task() as task:
    ch = task.co_channels.add_co_pulse_chan_freq(
        counter="Dev1/ctr0",
        freq=1.0,          # 1 pulse/second
        duty_cycle=0.1     # 100 ms HIGH, 900 ms LOW
    )

    ch.co_pulse_term = "/Dev1/PFI14"

    task.timing.cfg_implicit_timing(
        sample_mode=AcquisitionType.CONTINUOUS
    )

    task.start()
    input("Pulsing on USER2/PFI14. Press Enter to stop...")