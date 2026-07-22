import time

import nidaqmx
from nidaqmx.constants import TerminalConfiguration

with nidaqmx.Task() as task:
    task.ai_channels.add_ai_voltage_chan(
        "Dev1/ai6",
        terminal_config=TerminalConfiguration.RSE,
        min_val=-10.0,
        max_val=10.0,
    )

    try:
        while True:
            voltage = task.read()
            print(f"{voltage:.4f} V")
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("Stopped")