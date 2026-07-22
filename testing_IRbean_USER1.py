import nidaqmx
import time

with nidaqmx.Task() as task:
    task.di_channels.add_di_chan("Dev1/PFI1")

    while True:
        signal = task.read()
        print(signal)
        time.sleep(0.01)