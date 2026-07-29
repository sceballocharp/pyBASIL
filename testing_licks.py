import time

import nidaqmx
from nidaqmx.constants import TerminalConfiguration

THRESHOLD = 2.0  # volts

with nidaqmx.Task() as task:
    task.ai_channels.add_ai_voltage_chan(
        "Dev1/ai0",
        name_to_assign_to_channel="left",
        terminal_config=TerminalConfiguration.RSE,
        min_val=0.0,
        max_val=5.0,
    )

    task.ai_channels.add_ai_voltage_chan(
        "Dev1/ai1",
        name_to_assign_to_channel="right",
        terminal_config=TerminalConfiguration.RSE,
        min_val=0.0,
        max_val=5.0,
    )

    while True:
        left_voltage, right_voltage = task.read()

        left_lick = left_voltage > THRESHOLD
        right_lick = right_voltage > THRESHOLD

        print(
            f"Left: {left_voltage:.2f} V"
            f" {'LICK' if left_lick else '----'} | "
            f"Right: {right_voltage:.2f} V"
            f" {'LICK' if right_lick else '----'}"
        )

        time.sleep(0.1)