import numpy as np
import os
import re
import pandas as pd
from matplotlib import pyplot as plt
import csv
import yaml
from time import sleep
import ipywidgets as widgets
import asyncio
from datetime import datetime

import led_driver

from pynq.lib import MicroblazeRPC
from pynq import allocate

DAC_REFS = {0 : 3.125,
1 : 6.25,
2 : 12.5,
3 : 25,
4 : 50,
5 : 100,
6 : 200,
7 : 300}

DAC_REF = 4

LED_LABELS = [f'P{p}N{n}' for p, n in zip(np.tile(np.linspace(1,10,10).astype(int),10), np.repeat(np.linspace(1,10,10).astype(int),10))]

VOLTAGE_DIV = 0.026

def experiment_setup(ol):
    """Programmes the microblaze with the LED driver capable of any pattern/LED brightness.
        'ol' is base overlay instance
    """
    switch_max_current = 130
    device_max_current = 2500
    
    lib_path = os.path.dirname(os.path.realpath(__file__))
    driver_src_path = os.path.join(lib_path, 'driver/driver.c')

    with open(driver_src_path, 'r') as f:
        led_driver_source = f.read()
    
    led_driver_programme = MicroblazeRPC(ol.iop_arduino, led_driver_source)
       
    # Hard-coded 50 mA limit per channel
    led_driver_programme.leds_configure(DAC_REF, switch_max_current, device_max_current) 
    
    return led_driver_programme
    
def quad_regression(led_irradiance, a, b, c):
    if led_irradiance == 0:
        return 0
    else:
        return a*led_irradiance**2 + b*led_irradiance + c
    
def get_frames_counts(frames, device_id, ext_cables_used=True):
    """Returns 3D array of size number of frames x 10 x 10 based on input data.
        Output is calibrated based on irradiance to currents regression file and provides a 'counts' value for led driver programme
        Output is also re-orientated to correctly match indexing of LEDs
    """
    calibration_file = pd.read_csv(f'./Device calibration files/irr_to_current-{device_id}.dat', header=None)
    
    # These files contain coefficients in order: P10N10, P9N10, ... P10N9, P9N9, ...
    # Reverse so order is P1N1, P2N1, ... P1N2, P2N2, ... 
    calibration_data = np.array(calibration_file[::-1])
    
    frames = np.swapaxes(np.swapaxes(frames,0,2),1,2)
    
    # calibrate frames so correct current applied for each LED at each timestep - irr. already multiplied by 10 - AND CAP LED_COUNTS AT 20mA
    frames_currents = np.array([np.array([quad_regression(led_irradiance, *params) for led_irradiance, params in zip(led_irradiances.reshape(-1), calibration_data)]).reshape(10,10) for led_irradiances in frames])
    frames_currents[frames_currents > 20] = 20
    frames_counts = (frames_currents / DAC_REFS[DAC_REF] * 65535).astype(np.uint16)
    
    # alternate rows and columns if extension cables are used
    if ext_cables_used:
        frames_counts_temp = np.copy(frames_counts[:,::2,:])
        frames_counts[:,::2,:] = frames_counts[:,1::2,:]
        frames_counts[:,1::2,:] = frames_counts_temp
        frames_counts_temp = np.copy(frames_counts[:,:,::2])
        frames_counts[:,:,::2] = frames_counts[:,:,1::2]
        frames_counts[:,:,1::2] = frames_counts_temp
    
    return frames_counts
   
################################################################
### Class for continuous driver for simple pattern operation ###
################################################################
from collections import deque

class FixedErrorBox:
    def __init__(self, max_lines=8):
        self.max_lines = max_lines
        self.lines = deque(maxlen=max_lines)

        self.log_box = widgets.Textarea(
            value="",
            description="Log:",
            disabled=True,
            layout=widgets.Layout(width="600px", height="130px")
        )

    def add_line(self, text):
        """
        Add new log line at the bottom visually,
        while older lines shift upward.
        """
        self.lines.append(text)

        # Reverse so newest appears at bottom
        display_lines = list(self.lines)

        # Pad with blanks at the top if fewer than max_lines
        while len(display_lines) < self.max_lines:
            display_lines.insert(0, "")

        self.log_box.value = "\n".join(display_lines)

    def clear(self):
        self.lines.clear()
        self.log_box.value = "\n" * (self.max_lines - 1)

class ControlPanel:
    def __init__(self):        
        # --- Buttons ---
        self.start_button = widgets.Button(
            description="Start",
            button_style="success",
            layout=widgets.Layout(width="100px")
        )

        self.stop_button = widgets.Button(
            description="Stop",
            button_style="danger",
            layout=widgets.Layout(width="100px")
        )

        # --- Indicator ---
        self.indicator = widgets.HTML(
            value=self._build_indicator("gray"),
            layout=widgets.Layout(width="80px", height="50px")
        )

        # --- Progress Bar ---
        self.progress = widgets.IntProgress(
            value=0,
            min=0,
            max=100,
            description="Trial:",
            bar_style="",
            layout=widgets.Layout(width="300px")
        )

        # --- Labels ---
        self.status_label = widgets.Label(value="Status: Idle")
        self.info_label = widgets.Label(value="Info: Waiting")
        
        self.error_box = FixedErrorBox(max_lines=50)

        # --- Layout ---
        left_box = widgets.VBox([
            self.start_button,
            self.stop_button
        ])

        right_box = widgets.VBox([
            self.indicator
        ])

        top_row = widgets.HBox([
            left_box,
            right_box
        ])

        bottom_section = widgets.VBox([
            self.progress,
            self.status_label,
            self.info_label,
            self.error_box.log_box
        ])

        self.panel = widgets.VBox([
            top_row,
            bottom_section
        ])

    # -------------------------
    # Helper for indicator
    # -------------------------
    def _build_indicator(self, color):
        return f"""
        <div style="
            width:40px;
            height:40px;
            border-radius:50%;
            background:{color};
            border:2px solid black;
            margin:auto;">
        </div>
        """

    # -------------------------
    # Public update methods
    # -------------------------
    def set_indicator(self, color):
        self.indicator.value = self._build_indicator(color)

    def set_progress(self, value):
        self.progress.value = value

    def set_status(self, text):
        self.status_label.value = f"Status: {text}"

    def set_info(self, text):
        self.info_label.value = f"Info: {text}"

    # -------------------------
    # Display method
    # -------------------------
    def show(self):
        display(self.panel)
        
def create_log_file(folder="logs"):
    """
    Creates a CSV log file named with today's date.
    If a file with the same date exists, appends _1, _2, etc.

    Returns:
        filepath (str): full path to created file
    """
    # Make sure folder exists
    os.makedirs(folder, exist_ok=True)

    # Base filename with current date
    date_str = datetime.now().strftime("%Y-%m-%d")
    base_filename = f"{date_str}.csv"
    filepath = os.path.join(folder, base_filename)

    # Check for duplicates and add suffix
    counter = 1
    while os.path.exists(filepath):
        filepath = os.path.join(folder, f"{date_str}_{counter}.csv")
        counter += 1

    # Create file and write headers
    with open(filepath, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(['=== Log ==='])

    return filepath

def append_to_log(filepath, data_row):
    """
    Appends a row of data to the CSV log file.
    """
    with open(filepath, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(data_row)
        
CHANNEL_LABELS = [f'P{p}' for p in range(1,11,1)]

# function to decode fault register and return a message
def get_fault_code_err_msg(fault_reg, error_message = f""):
    bits = [int(b) for b in format(fault_reg, '08b')]
    if np.sum(bits):
        error_message += f"o/c "
        for idx, bit in enumerate(bits[-1:-6:-1]):
            if bit:
                error_message += f"ch: {idx} | "
    return error_message

# function to return message for measured voltages - based on LEDs being tested
def get_voltages_err_msg(measured_voltages, current_dac_counts, error_message = f""):
    for idx, (current_dac_count, measured_voltage) in enumerate(zip(current_dac_counts[:10], measured_voltages[:10])):
        if current_dac_count > 0:
            if measured_voltage > 7.3:
                # open - put message later, should be captured by fault code anyway
                error_message += f"open: {CHANNEL_LABELS[idx]} | "
            elif measured_voltage < 2.5:
                # short
                error_message += f"short: {CHANNEL_LABELS[idx]} | "
    return error_message

class ExpSimplePatterns():
    def __init__(self, ol, config_file, trials_file, wait_for_trigger=True, ext_cables_used=True):
        self.config_file = config_file
        self.trials_file = trials_file
        self.wait_for_trigger = wait_for_trigger
        self.ext_cables_used = ext_cables_used
        
        self.stop = allocate(shape=(1,), dtype=np.uint16)
        self.current_dac_counts_buffer = allocate(shape=(20,), dtype=np.uint16)
        self.switches_buffer = allocate(shape=(1,), dtype=np.uint32)
        self.trig = allocate(shape=(1,), dtype=np.uint16)
        self.trig_in = allocate(shape=(1,), dtype=np.uint16)
        self.fault_reg_a_buffer = allocate(shape=(1,), dtype=np.uint8)
        self.fault_reg_b_buffer = allocate(shape=(1,), dtype=np.uint8)
        self.voltages_buffer = allocate(shape=(20,), dtype=np.uint16)
        
        self.led_driver_programme = experiment_setup(ol)
        
        self.control_panel = ControlPanel()
        # Attach callbacks
        self.control_panel.start_button.on_click(self.on_start_clicked)
        self.control_panel.stop_button.on_click(self.on_stop_clicked)
        self.control = self.control_panel.panel
        
        self._initialised = False
        
        # --- Internal async control ---
        self._running_task = None
        self._stop_requested = False
        
        self.stop[0] = 0
        self.control_panel.set_status("Initialising...")
        self.led_driver_programme.leds_start_cont(self.current_dac_counts_buffer, 
                                                  self.switches_buffer, 
                                                  self.trig_in, 
                                                  self.trig, 
                                                  self.stop, 
                                                  self.fault_reg_a_buffer,
                                                  self.fault_reg_b_buffer,
                                                  self.voltages_buffer)
        self._initialised = True
        self._stop_requested = False
        self.control_panel.set_status("Initialised")
                
    def initialise(self):
        """Call before 'run()' for the first time or if 'stop()' called.
        """
        self.stop[0] = 0
        self.control_panel.set_status("Initialising...")
        self.led_driver_programme.leds_start_cont(self.current_dac_counts_buffer, 
                                                  self.switches_buffer, 
                                                  self.trig_in, 
                                                  self.trig, 
                                                  self.stop,
                                                  self.fault_reg_a_buffer,
                                                  self.fault_reg_b_buffer,
                                                  self.voltages_buffer)
        
        self._initialised = True
        self._stop_requested = False
        
    async def run(self):
        self._stop_requested = False
        self.control_panel.progress.bar_style = 'info'
        self.control_panel.progress.value = 0
        self.control_panel.set_indicator("gray")
        self.control_panel.set_info("")
        self.control_panel.error_box.clear()
        if self._initialised == False:
            self.initialise()
        self.control_panel.set_status("Initialised")
        
        with open(f"./Configurations/{self.config_file}", "r") as f:
            config = yaml.safe_load(f)
            
        self.log_file = create_log_file()
        self.control_panel.set_status(f"Initialised. Saving log in {self.log_file}")
        append_to_log(self.log_file, [f"Log file for mouse ID: {config['mouse_id']}"])
        append_to_log(self.log_file, [f"Device ID: {config['device_id']}"])        
        append_to_log(self.log_file, [f"Date: {datetime.now().strftime('%Y-%m-%d')}"])
        append_to_log(self.log_file, [f"Time: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}"])
        append_to_log(self.log_file, [f"Note: date/time will not be correct unless wifi connected."])
    
        trials = np.loadtxt(self.trials_file)
        
        append_to_log(self.log_file, [f""])
        append_to_log(self.log_file, [f"Trials list:"])
        append_to_log(self.log_file, trials)
        append_to_log(self.log_file, [f""])
        
        append_to_log(self.log_file, [f"GO pattern: ", config['GO']])
        append_to_log(self.log_file, [f"GO irradiance: ", config['GO irradiance (mW/mm2)']])
        append_to_log(self.log_file, [f"NO-GO pattern: ", config['NOGO']])
        append_to_log(self.log_file, [f"NO-GO irradiance: ", config['NOGO irradiance (mW/mm2)']])
        # TODO save intermediate patterns later
        
        append_to_log(self.log_file, [f"Pulse duration (ms): ", config['Pulse duration (ms)']])
        append_to_log(self.log_file, [f"Pulse frequency (Hz): ", config['Pulse frequency (Hz)']])
        append_to_log(self.log_file, [f"Number of pulses: ", config['Number of pulses']])
        
        go_pattern = np.zeros((10,10), dtype=float)
        for led_matrix_location in [np.where(np.array(LED_LABELS).reshape(10,10) == led_label) for led_label in config['GO'].split(' ')]:
            go_pattern[led_matrix_location[0][0], led_matrix_location[1][0]] = config['GO irradiance (mW/mm2)']

        nogo_pattern = np.zeros((10,10), dtype=float)
        for led_matrix_location in [np.where(np.array(LED_LABELS).reshape(10,10) == led_label) for led_label in config['NOGO'].split(' ')]:
            nogo_pattern[led_matrix_location[0][0], led_matrix_location[1][0]] = config['NOGO irradiance (mW/mm2)']
            
        # TODO store intermediate patterns if applicable
            
        pulse_on_secs = config['Pulse duration (ms)']/1000
        pulse_off_secs = 1/config['Pulse frequency (Hz)'] - pulse_on_secs
        
        self.control_panel.set_status("Running")
        
        self.control_panel.progress.max = len(trials)
        
        # Run experimental protocol:
        for trial_idx, trial in enumerate(trials):
            #print(f'trial {"%03d" % (trial_idx,)}', end='\r')
            self.control_panel.progress.value = trial_idx+1
            append_to_log(self.log_file, [f"Trial: ", trial_idx+1])
            append_to_log(self.log_file, [f"Timestamp: ", datetime.now().strftime("%H:%M:%S.%f")[:-3]])
            
            self.control_panel.error_box.add_line(f"\nTrial {trial_idx+1}")
            if trial == 1:
                pattern = go_pattern
                self.control_panel.set_info(f"Trial {trial_idx+1} of {len(trials)} (GO)")
                self.control_panel.set_indicator("green")
                append_to_log(self.log_file, [f"Trial type: GO"])
            elif trial == 2:
                pattern = nogo_pattern
                self.control_panel.set_info(f"Trial {trial_idx+1} of {len(trials)} (NO-GO)")
                self.control_panel.set_indicator("red")
                append_to_log(self.log_file, [f"Trial type: NO-GO"])
            elif trial == 0:
                pattern = np.zeros((10,10), dtype=float) # blank
                self.control_panel.set_info(f"Trial {trial_idx+1} of {len(trials)} (BLANK)")
                self.control_panel.set_indicator("lightgrey")
                append_to_log(self.log_file, [f"Trial type: BLANK"])
            else:
                pass
                # intermediate pattern - implement later if needed

            # convert counts to current matrix 
            # for each column, pass the sum of the required current divided by the number of active rows
            led_counts_cont = np.zeros((20,20), dtype=np.uint16)
            led_counts_cont[19:9:-1,:10] = get_frames_counts(pattern[:,:,np.newaxis], config['device_id'], ext_cables_used=self.ext_cables_used)[0]

            switches = [int(any(row)) for row in led_counts_cont]
            switches_value = np.sum([val*2**bit for bit,val in enumerate(switches)]).astype(np.uint32)

            current_dac_counts = np.sum(led_counts_cont, axis=0)

            # Exceeding maximum current, limiting to 50 mA per channel
            if np.count_nonzero(current_dac_counts > 65535):
                current_dac_counts[current_dac_counts > 65535] = 65535
                # TODO log warning
            current_dac_counts = current_dac_counts.astype(np.uint16)

            # wait for trigger then start pattern sequence - this proceeds when nothing is connected because the pin is floating
            self.control_panel.set_status("Waiting for trigger")
            self.control_panel.progress.bar_style = 'info'

            append_to_log(self.log_file, [f"Waiting for trigger...", datetime.now().strftime("%H:%M:%S.%f")[:-3]])
            
            if(self.wait_for_trigger):
                while(self.trig[0] == 0):
                    await asyncio.sleep(0.1)
                    if self._stop_requested:
                        self.stop_()
                        self.control_panel.set_status("Stopped")
                        return
            else:
                for _ in range(30):
                    await asyncio.sleep(0.1)
                    if self._stop_requested:
                        self.stop_()
                        self.control_panel.set_status("Stopped")
                        return
                    
            self.control_panel.set_status("Running")
            self.control_panel.progress.bar_style = 'info'

            append_to_log(self.log_file, [f"Trigger detected, starting stimulus", datetime.now().strftime("%H:%M:%S.%f")[:-3]])
            
            fault_reg_a = 0
            fault_reg_b = 0
            measured_voltage_counts = np.zeros(shape=(20,), dtype=np.uint16)
            
            for pulse in range(config['Number of pulses']):
                self.current_dac_counts_buffer[:] = current_dac_counts
                self.switches_buffer[0] = switches_value
                self.trig_in[0] = 1
                sleep(0.001)
                self.trig_in[0] = 0
                sleep(pulse_on_secs)
                
                fault_reg_a = self.fault_reg_a_buffer[0]
                fault_reg_b = self.fault_reg_b_buffer[0]
                measured_voltage_counts[:] = self.voltages_buffer[:]

                self.current_dac_counts_buffer.fill(0)
                self.switches_buffer[0] = 0
                self.trig_in[0] = 1
                sleep(0.001)
                self.trig_in[0] = 0
                sleep(pulse_off_secs)

            self.trig_in[0] = 0
            
            # At this point we can save the final set of measured voltages and fault codes
            append_to_log(self.log_file, [f"Fault codes:"])
            append_to_log(self.log_file, [f"Fault reg A: ", fault_reg_a])
            append_to_log(self.log_file, [f"Fault reg B: ", fault_reg_b])
            append_to_log(self.log_file, [f"Measured voltages (V):"])
            append_to_log(self.log_file, measured_voltage_counts / 65535 * 3.33 / VOLTAGE_DIV)
            append_to_log(self.log_file, [f""])
            
            # Flag warnings to user if there are faults
            fault_code_err_msg_a = get_fault_code_err_msg(fault_reg_a, "")
            fault_code_err_msg_b = get_fault_code_err_msg(fault_reg_b, "")
            if fault_code_err_msg_a != "" or fault_code_err_msg_b != "":
                self.control_panel.error_box.add_line(f"[WARNING] o/c fault {'DAC A: ' + fault_code_err_msg_a if fault_code_err_msg_a != '' else ''} {'DAC B: ' + fault_code_err_msg_b if fault_code_err_msg_b != '' else ''}")
            
            voltages_err_msg = get_voltages_err_msg(measured_voltage_counts / 65535 * 3.33 / VOLTAGE_DIV, current_dac_counts)
            if voltages_err_msg != "":
                self.control_panel.error_box.add_line(f"[WARNING] {voltages_err_msg}")
            
        self.control_panel.set_status("Task finished sucessfully!")
        append_to_log(self.log_file, [f""])
        append_to_log(self.log_file, [f"PROTOCOL FINISHED SUCCESSFULLY"])
        
        self.stop_()
        
    def stop_(self):
        self.stop[0] = 1
        self._initialised = False
            
    # -------------------------
    # Button callbacks
    # -------------------------
    def on_start_clicked(self, b):
        if self._running_task is None or self._running_task.done():
            self._running_task = asyncio.create_task(self.run())

    def on_stop_clicked(self, b):
        self._stop_requested = True

### Braincodec patterns driver ###
class ExpBraincodecPatterns():
    def __init__(self, ol, config_file, trials_file, wait_for_trigger=True, ext_cables_used=True):
        self.config_file = config_file
        self.trials_file = trials_file
        self.wait_for_trigger = wait_for_trigger
        self.ext_cables_used = ext_cables_used
        
        self.led_counts = allocate(shape=(20,20), dtype=np.uint16)
        self.trig = allocate(shape=(1,), dtype=np.uint16)
        self.stop = allocate(shape=(1,), dtype=np.uint16)
        self.stop[0] = 0
        self.led_counts.fill(0)
        
        self.led_driver_programme = experiment_setup(ol)
        
        self.control_panel = ControlPanel()
        # Attach callbacks
        self.control_panel.start_button.on_click(self.on_start_clicked)
        self.control_panel.stop_button.on_click(self.on_stop_clicked)
        self.control = self.control_panel.panel
        
        self._initialised = False
        
        # --- Internal async control ---
        self._running_task = None
        self._stop_requested = False
        
        self.stop[0] = 0
        self.control_panel.set_status("Initialising...")        
        
        self.led_driver_programme.leds_start(self.led_counts, 
                                             self.trig, 
                                             self.stop)
        
        self._initialised = True
        self._stop_requested = False
        self.control_panel.set_status("Initialised")
        
    def initialise(self):
        """Call before 'run()' for the first time or if 'stop()' called.
        """
        self.stop[0] = 0
        self.control_panel.set_status("Initialising...")
        self.led_driver_programme.leds_start(self.led_counts, 
                                             self.trig, 
                                             self.stop)
        self._initialised = True
        self._stop_requested = False
        
    async def run(self):
        self._stop_requested = False
        self.control_panel.progress.bar_style = 'info'
        self.control_panel.progress.value = 0
        self.control_panel.set_indicator("gray")
        self.control_panel.set_info("")
        self.control_panel.error_box.clear()
        if self._initialised == False:
            self.initialise()
        self.control_panel.set_status("Initialised")
        
        with open(f"./Configurations/{self.config_file}", "r") as f:
            config = yaml.safe_load(f)
            
        self.log_file = create_log_file()
        self.control_panel.set_status(f"Initialised. Saving log in {self.log_file}")
        append_to_log(self.log_file, [f"Log file for mouse ID: {config['mouse_id']}"])
        append_to_log(self.log_file, [f"Device ID: {config['device_id']}"])
        append_to_log(self.log_file, [f"Date: {datetime.now().strftime('%Y-%m-%d')}"])
        append_to_log(self.log_file, [f"Time: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}"])
        append_to_log(self.log_file, [f"Note: date/time will not be correct unless wifi connected."])
            
        trials = np.loadtxt(self.trials_file)
        append_to_log(self.log_file, [f""])
        append_to_log(self.log_file, [f"Trials list:"])
        append_to_log(self.log_file, trials)
        append_to_log(self.log_file, [f""])
        
        append_to_log(self.log_file, [f"Patterns file: ", config['patterns_file']])
        append_to_log(self.log_file, [f"Patterns maximum: ", config['patterns_max']])
        append_to_log(self.log_file, [f"Use catch trials: ", config['catch_trials']])
        
        self.control_panel.set_status("Running")
        
        self.control_panel.progress.max = len(trials)
        
        patterns_load = np.load(config['patterns_file'])
        patterns_load = patterns_load / config['patterns_max'] * 10
        
        patterns = {}
        patterns['GO_PATTERN'] = patterns_load[0]
        patterns['NOGO_PATTERN'] = patterns_load[15]
        for i in range(1, 15):
            patterns[f'CATCH{i}_PATTERN'] = patterns_load[i]
        
        for trial_idx, trial in enumerate(trials):
            #print(f'TRIAL: {str(trial_idx+1).zfill(3)}', end='\r')
            self.control_panel.progress.value = trial_idx+1
            append_to_log(self.log_file, [f"Trial: ", trial_idx+1])
            append_to_log(self.log_file, [f"Timestamp: ", datetime.now().strftime("%H:%M:%S.%f")[:-3]])

            self.control_panel.error_box.add_line(f"\nTrial {trial_idx+1}")
            if not config['catch_trials'] and (2 <= trial <= 15):
                pattern = np.zeros((10,10,20), np.float32)
                self.control_panel.set_info(f"Trial {trial_idx+1} of {len(trials)} (BLANK)")
                self.control_panel.set_indicator("lightgrey")
                append_to_log(self.log_file, [f"Trial type: BLANK"])
            elif trial == 1:
                pattern = patterns['GO_PATTERN']
                self.control_panel.set_info(f"Trial {trial_idx+1} of {len(trials)} (GO)")
                self.control_panel.set_indicator("green")
                append_to_log(self.log_file, [f"Trial type: GO"])
            elif 2 <= trial <= 15:
                pattern = patterns[f'CATCH{int(trial-1)}_PATTERN']
                self.control_panel.set_info(f"Trial {trial_idx+1} of {len(trials)} (CATCH {int(trial-1)})")
                self.control_panel.set_indicator("orange")
                append_to_log(self.log_file, [f"Trial type: CATCH {int(trial-1)}"])
            else:
                pattern = patterns['NOGO_PATTERN']
                self.control_panel.set_info(f"Trial {trial_idx+1} of {len(trials)} (NO-GO)")
                self.control_panel.set_indicator("red")
                append_to_log(self.log_file, [f"Trial type: NO-GO"])
            
            frames_counts = get_frames_counts(pattern, 
                                              config['device_id'], 
                                              ext_cables_used=self.ext_cables_used)
            
            self.control_panel.set_status("Waiting for trigger")
            self.control_panel.progress.bar_style = 'info'

            append_to_log(self.log_file, [f"Waiting for trigger...", datetime.now().strftime("%H:%M:%S.%f")[:-3]])

            # wait for trigger then start pattern sequence
            if(self.wait_for_trigger):
                while(self.trig[0] == 0):
                    await asyncio.sleep(0.1)
                    if self._stop_requested:
                        self.stop_()
                        self.control_panel.set_status("Stopped")
                        return
            else:
                for _ in range(30):
                    await asyncio.sleep(0.1)
                    if self._stop_requested:
                        self.stop_()
                        self.control_panel.set_status("Stopped")
                        return
            
            self.control_panel.set_status("Running")
            self.control_panel.progress.bar_style = 'info'

            append_to_log(self.log_file, [f"Trigger detected, starting stimulus", datetime.now().strftime("%H:%M:%S.%f")[:-3]])

            # Run through frame sequence
            for frame_counts in frames_counts:
                self.led_counts[:10,:10] = frame_counts
                sleep(0.025)  # wait for 25 ms
            self.led_counts[:10,:10] = 0
            
        self.control_panel.set_status("Task finished sucessfully!")
        append_to_log(self.log_file, [f""])
        append_to_log(self.log_file, [f"PROTOCOL FINISHED SUCCESSFULLY"])
        
        self.stop_()
        
    def stop_(self):
        self.stop[0] = 1
        self._initialised = False
            
    # -------------------------
    # Button callbacks
    # -------------------------
    def on_start_clicked(self, b):
        if self._running_task is None or self._running_task.done():
            self._running_task = asyncio.create_task(self.run())

    def on_stop_clicked(self, b):
        self._stop_requested = True
    
###############################    
### Device health scan code ###
###############################
def get_currents_switches_cont_pattern(led_counts_cont_in):
    """Returns array of 20 current count values and switch positions based on 'led_counts'.
       'led_counts' should be pre-determined from LED currents. 
    """
    led_counts_cont = np.zeros((20,20), dtype=np.uint16)
    led_counts_cont[19:9:-1,:10] = led_counts_cont_in
    switches = [int(any(row)) for row in led_counts_cont]
    switches_value = np.sum([val*2**bit for bit,val in enumerate(switches)]).astype(np.uint32)

    current_dac_counts = np.sum(led_counts_cont, axis=0)
    
    return current_dac_counts, switches_value
    
LED_LABELS = [f'P{p}N{n}' for p, n in zip(np.tile(np.linspace(1,10,10).astype(int),10), np.repeat(np.linspace(1,10,10).astype(int),10))]
LED_LABELS_FLIPPED = [f'P{p}N{n}' for p, n in zip(np.tile(np.array([2,1,4,3,6,5,8,7,10,9]),10), np.repeat(np.array([2,1,4,3,6,5,8,7,10,9]),10))]
# VOLTAGE_DIV = 0.1
VOLTAGE_DIV = 0.026 # Due to hardware issue with electronics at ADC input
CURRENTS_MA = np.linspace(0.01,7,50)
VOLTAGE_MIN_5MA = 2.5
VOLTAGE_MAX_5MA = 6.5
    
def measure_voltage(led_driver_programme, channel):
    led_driver_programme.monitor_mux(channel)
    voltages_measurements = allocate(shape=(4,), dtype=np.uint16)
    led_driver_programme.read_adc(voltages_measurements)
    
    return (voltages_measurements[np.r_[2,0,3,1]] / 65535 * 3.33 / VOLTAGE_DIV)
    
def device_health_scan(led_driver_programme, folder_name, ext_cables_used=False):
    """Top level function to run voltage measurements under a sweep of currents across whole device. Assumes the extension cables are being used.
    """
    voltage_measurements_all = []
    
    if ext_cables_used:
        led_labels_iterate = LED_LABELS_FLIPPED
        channel_list = [1,0,3,2,0,4,2,1,4,3]
        dac_list = [0,0,0,0,1,0,1,1,1,1]
    else:
        led_labels_iterate = LED_LABELS
        channel_list = [0,1,2,3,4,0,1,2,3,4]
        dac_list = [0,0,0,0,0,1,1,1,1,1]
        
    for led_idx, led_label in enumerate(led_labels_iterate):
        voltage_measurements = []
        channel = channel_list[led_idx%10]

        for current in CURRENTS_MA:
            led_counts_cont = ((np.array(LED_LABELS).reshape(10,-1) == led_label) * np.uint16(current/DAC_REFS[DAC_REF]*65535)).astype(np.uint16)
            led_driver_programme.leds_start_cont_2(*get_currents_switches_cont_pattern(led_counts_cont))
            # sleep(0.001)
            # voltage_measurements.append(measure_voltage(led_driver_programme,channel)[int((led_idx%10)/5)])
            voltage_measurements.append(measure_voltage(led_driver_programme,channel)[dac_list[led_idx%10]])
        #channel = (channel+1)%5

        voltage_measurements_all.append(voltage_measurements)

        print(f'LED {led_label} ({led_idx+1}/100)...', end='\r')

    led_driver_programme.leds_off()

    # plot map of voltage where current == 5 mA
    voltage_measurements_all_array = np.array(voltage_measurements_all).reshape(100,-1)

    voltage_at_approx_5mA = np.zeros((100),)
    for led_idx, led_label in enumerate(LED_LABELS):
        voltage_at_approx_5mA[led_idx] = voltage_measurements_all_array[led_idx][np.argmin(np.abs(CURRENTS_MA-5))]

    # characterise performance
    led_performance_map = []
    for led_idx, led_label in enumerate(LED_LABELS):
        if voltage_measurements_all_array[led_idx][np.argmin(np.abs(CURRENTS_MA-5))] < VOLTAGE_MIN_5MA:
            led_performance_map.append([0,0,255]) # short
        elif voltage_measurements_all_array[led_idx][np.argmin(np.abs(CURRENTS_MA-5))] > 8:
            led_performance_map.append([255,0,0]) # open
        elif (voltage_measurements_all_array[led_idx][np.argmin(np.abs(CURRENTS_MA-5))] > VOLTAGE_MIN_5MA) & (voltage_measurements_all_array[led_idx][np.argmin(np.abs(CURRENTS_MA-5))] < VOLTAGE_MAX_5MA):
            led_performance_map.append([0,255,0]) # good            
        else:
            led_performance_map.append([255,128,128]) #bad
    
    newpath = f'./health_scans/{folder_name}' 
    if not os.path.exists(newpath):
        os.makedirs(newpath)
    
    # save both maps
    fig, ax = plt.subplots()
    print('LED performance')
    im = ax.imshow(np.array(led_performance_map).astype(np.uint8).reshape(10,10,3))
    ax.set_xticks([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])                     # positions
    ax.set_xticklabels(['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10'])      # labels
    ax.set_yticks([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    ax.set_yticklabels(['N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7', 'N8', 'N9', 'N10'])
    # plt.imshow(np.array(led_performance_map).astype(np.uint8).reshape(10,10,3))
    plt.savefig(f'./health_scans/{folder_name}/led_performance_map.png')
    
    fig, ax = plt.subplots()
    print('LED voltage at 5 mA')
    # plt.imshow((np.array(voltage_at_approx_5mA)).astype(np.uint8).reshape(10,10), vmin=0, vmax=12)
    im = ax.imshow((np.array(voltage_at_approx_5mA)).astype(np.uint8).reshape(10,10), vmin=0, vmax=12)
    ax.set_xticks([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])                     # positions
    ax.set_xticklabels(['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10'])      # labels
    ax.set_yticks([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    ax.set_yticklabels(['N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7', 'N8', 'N9', 'N10'])
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Measured voltage (V)")
    # plt.colorbar()
    plt.savefig(f'./health_scans/{folder_name}/voltage_at_5mA.png')
    
    # save voltage measurements as CSV
    with open(f'./health_scans/{folder_name}/voltage_measurements.csv', 'w', newline='\n') as f:
        csv_writer = csv.writer(f, delimiter=',')
        csv_writer.writerow(['Current (mA)'])
        csv_writer.writerow(CURRENTS_MA)
        csv_writer.writerow(['Voltage (V)'])
        for led_idx, (led_label, voltage_measurements) in enumerate(zip(LED_LABELS, voltage_measurements_all)):
            csv_writer.writerow([led_label])
            csv_writer.writerow(voltage_measurements_all[led_idx])
    