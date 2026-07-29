import time
import nidaqmx
from nidaqmx.constants import TerminalConfiguration

with nidaqmx.Task() as task:
    task.ai_channels.add_ai_voltage_chan(
        "Dev1/ai0",
        terminal_config=TerminalConfiguration.RSE,
        min_val=0,
        max_val=5
    )
    task.ai_channels.add_ai_voltage_chan(
        "Dev1/ai1",
        terminal_config=TerminalConfiguration.RSE,
        min_val=0,
        max_val=5
    )

    while True:
        ai0, ai1 = task.read()
        print(f"AI0: {ai0:.3f} V | AI1: {ai1:.3f} V")
        time.sleep(0.1)