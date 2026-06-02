from pathlib import Path
import csv
import pickle
from tkinter import Tk, StringVar, filedialog, messagebox
from tkinter import ttk

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


DEFAULT_LOG_FILE = Path(
    r"C:\Users\Behaviour_2\Documents\New project\data\2023-04-06_3.csv"
)

# This channel order comes from 2026-06-01_analyse_log_files.ipynb.
# The log has 20 voltage values, but the notebook plots the first 10.
VOLTAGE_CHANNEL_ORDER = [1, 0, 3, 2, 5, 4, 7, 6, 9, 8]


def value_after_comma(line):
    row = next(csv.reader([line]))
    if len(row) < 2:
        raise ValueError(f"Expected a comma-separated value in line: {line}")
    return row[1].strip()


def value_after_colon(line):
    return line.split(":", maxsplit=1)[1].strip()


def parse_log_file(path):
    lines = path.read_text().splitlines()
    metadata = {"go_pattern": [], "no_go_pattern": []}
    trials = []
    incomplete_trials = []

    for line in lines:
        if line.startswith("GO pattern:"):
            metadata["go_pattern"] = value_after_comma(line).split()
        elif line.startswith("NO-GO pattern:"):
            metadata["no_go_pattern"] = value_after_comma(line).split()

    trial_starts = [
        line_number for line_number, line in enumerate(lines) if line.startswith("Trial: ,")
    ]

    for start_index, start_line in enumerate(trial_starts):
        end_line = (
            trial_starts[start_index + 1]
            if start_index + 1 < len(trial_starts)
            else len(lines)
        )
        block = lines[start_line:end_line]
        trial = parse_trial_block(block, line_number=start_line + 1)
        if trial is None:
            incomplete_trials.append(int(value_after_comma(block[0])))
        else:
            trials.append(trial)

    return metadata, trials, incomplete_trials


def parse_trial_block(block, line_number):
    required_prefixes = (
        "Timestamp:",
        "Trial type:",
        "Waiting for trigger",
        '"Trigger detected, starting stimulus"',
        "Fault reg A:",
        "Fault reg B:",
        "Measured voltages",
    )
    if not all(any(line.startswith(prefix) for line in block) for prefix in required_prefixes):
        print(f"Skipping incomplete trial block starting on line {line_number}.")
        return None

    voltage_header_index = next(
        index for index, line in enumerate(block) if line.startswith("Measured voltages")
    )
    voltages = [
        float(value)
        for value in block[voltage_header_index + 1].split(",")
        if value.strip()
    ]

    return {
        "trial": int(value_after_comma(block[0])),
        "timestamp": value_after_comma(
            next(line for line in block if line.startswith("Timestamp:"))
        ),
        "trial_type": value_after_colon(
            next(line for line in block if line.startswith("Trial type:"))
        ),
        "waiting_time": value_after_comma(
            next(line for line in block if line.startswith("Waiting for trigger"))
        ),
        "trigger_time": value_after_comma(
            next(
                line
                for line in block
                if line.startswith('"Trigger detected, starting stimulus"')
            )
        ),
        "fault_reg_a": int(
            value_after_comma(next(line for line in block if line.startswith("Fault reg A:")))
        ),
        "fault_reg_b": int(
            value_after_comma(next(line for line in block if line.startswith("Fault reg B:")))
        ),
        "voltages": voltages,
    }


def time_to_seconds(time_text):
    hours, minutes, seconds = time_text.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def led_labels_grid(shape=(10, 10)):
    labels = np.empty(shape, dtype=object)
    for n_number in range(1, shape[0] + 1):
        for p_number in range(1, shape[1] + 1):
            labels[n_number - 1, p_number - 1] = f"P{p_number}N{n_number}"
    return labels


def parse_position(position):
    p_text, n_text = position.upper().split("N", maxsplit=1)
    p_number = int(p_text.replace("P", ""))
    n_number = int(n_text)
    return n_number - 1, p_number - 1


def pattern_indices(pattern):
    return [parse_position(position) for position in pattern]


def voltages_to_pattern_grid(voltages, pattern):
    if len(voltages) < 10:
        raise ValueError(f"Expected at least 10 voltage values, found {len(voltages)}.")

    reordered_voltages = np.array(voltages[:10], dtype=float)[VOLTAGE_CHANNEL_ORDER]
    voltage_grid = np.tile(reordered_voltages, 10).reshape(10, 10)

    labels = led_labels_grid()
    pattern_mask = np.isin(labels, pattern)
    voltage_grid[~pattern_mask] = np.nan
    return voltage_grid


def select_pattern(metadata, trial):
    trial_type = trial["trial_type"].upper()
    if trial_type == "GO":
        return "GO", metadata["go_pattern"]
    if trial_type == "NO-GO":
        return "NO-GO", metadata["no_go_pattern"]
    raise ValueError(f"Unknown trial type: {trial['trial_type']}")


class TrialVoltageViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Log Trial Voltage Viewer")
        self.metadata = {}
        self.trials = []
        self.incomplete_trials = []
        self.current_index = 0
        self.colorbar = None

        self.file_path = StringVar(value=str(DEFAULT_LOG_FILE))
        self.trial_entry = StringVar(value="")
        self.status = StringVar(value="No file loaded")
        self.summary = StringVar(value="")

        self.build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        if DEFAULT_LOG_FILE.exists():
            self.load_file(DEFAULT_LOG_FILE)

    def build_layout(self):
        root_frame = ttk.Frame(self.root, padding=10)
        root_frame.pack(fill="both", expand=True)

        file_frame = ttk.Frame(root_frame)
        file_frame.pack(fill="x")

        ttk.Button(file_frame, text="Browse file", command=self.browse_file).pack(side="left")
        ttk.Entry(file_frame, textvariable=self.file_path).pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Button(file_frame, text="Save summary", command=self.save_summary).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(file_frame, text="Quit", command=self.close).pack(side="left")

        control_frame = ttk.Frame(root_frame)
        control_frame.pack(fill="x", pady=(8, 4))

        self.prev_button = ttk.Button(
            control_frame, text="Previous", command=self.previous_trial, state="disabled"
        )
        self.prev_button.pack(side="left")

        self.next_button = ttk.Button(
            control_frame, text="Next", command=self.next_trial, state="disabled"
        )
        self.next_button.pack(side="left", padx=(6, 14))

        ttk.Label(control_frame, text="Trial").pack(side="left")
        trial_entry = ttk.Entry(control_frame, textvariable=self.trial_entry, width=8)
        trial_entry.pack(side="left", padx=6)
        trial_entry.bind("<Return>", lambda _event: self.go_to_trial())
        ttk.Button(control_frame, text="GO", command=self.go_to_trial).pack(side="left")

        ttk.Label(control_frame, textvariable=self.summary).pack(side="left", padx=18)

        self.figure = plt.figure(figsize=(12, 6))
        axes_grid = self.figure.add_gridspec(
            2,
            2,
            width_ratios=[1.15, 1],
            height_ratios=[1, 1],
            left=0.06,
            right=0.88,
            bottom=0.10,
            top=0.90,
            wspace=0.32,
            hspace=0.42,
        )
        self.current_grid_ax = self.figure.add_subplot(axes_grid[:, 0])
        self.go_summary_ax = self.figure.add_subplot(axes_grid[0, 1])
        self.nogo_summary_ax = self.figure.add_subplot(axes_grid[1, 1])
        self.canvas = FigureCanvasTkAgg(self.figure, master=root_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, pady=(8, 4))

        ttk.Label(root_frame, textvariable=self.status).pack(fill="x")

    def browse_file(self):
        selected = filedialog.askopenfilename(
            initialdir=str(Path(self.file_path.get()).parent),
            title="Select log CSV file",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if selected:
            self.load_file(Path(selected))

    def save_summary(self):
        if not self.trials:
            messagebox.showwarning("No data", "Load a log file before saving a summary.")
            return

        default_name = f"{Path(self.file_path.get()).stem}_voltage_summary.pkl"
        selected = filedialog.asksaveasfilename(
            initialdir=str(Path(self.file_path.get()).parent),
            initialfile=default_name,
            title="Save voltage summary",
            defaultextension=".pkl",
            filetypes=(("Pickle files", "*.pkl"), ("All files", "*.*")),
        )
        if not selected:
            return

        summary_data = self.build_summary_dictionary()
        try:
            with open(selected, "wb") as output_file:
                pickle.dump(summary_data, output_file)
        except Exception as error:
            messagebox.showerror("Could not save summary", str(error))
            return

        self.status.set(f"Saved voltage summary: {selected}")

    def close(self):
        plt.close(self.figure)
        self.root.quit()
        self.root.destroy()

    def load_file(self, path):
        try:
            metadata, trials, incomplete_trials = parse_log_file(path)
            if not trials:
                raise ValueError("No complete trials were found.")
            if not metadata["go_pattern"] or not metadata["no_go_pattern"]:
                raise ValueError("GO and NO-GO patterns were not found.")
        except Exception as error:
            messagebox.showerror("Could not load file", str(error))
            return

        self.metadata = metadata
        self.trials = trials
        self.incomplete_trials = incomplete_trials
        self.current_index = 0
        self.file_path.set(str(path))
        self.set_controls_enabled(True)
        self.update_plot()

    def set_controls_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.prev_button.configure(state=state)
        self.next_button.configure(state=state)

    def previous_trial(self):
        if not self.trials:
            return
        self.current_index = max(0, self.current_index - 1)
        self.update_plot()

    def next_trial(self):
        if not self.trials:
            return
        self.current_index = min(len(self.trials) - 1, self.current_index + 1)
        self.update_plot()

    def go_to_trial(self):
        try:
            trial_number = int(self.trial_entry.get())
        except ValueError:
            messagebox.showwarning("Invalid trial", "Enter a numeric trial number.")
            return

        for index, trial in enumerate(self.trials):
            if trial["trial"] == trial_number:
                self.current_index = index
                self.update_plot()
                return

        messagebox.showwarning(
            "Trial not found",
            f"Trial {trial_number} was not found as a complete trial.",
        )

    def update_plot(self):
        trial = self.trials[self.current_index]
        pattern_name, pattern = select_pattern(self.metadata, trial)
        voltage_grid = voltages_to_pattern_grid(trial["voltages"], pattern)

        current_image = self.draw_voltage_grid(
            self.current_grid_ax,
            voltage_grid,
            title=(
                f"Trial {trial['trial']} | {trial['trial_type']} | {pattern_name} pattern\n"
                f"fault A={trial['fault_reg_a']}, B={trial['fault_reg_b']}"
            ),
            annotate=True,
        )
        self.draw_trial_type_scatter(
            self.go_summary_ax,
            "GO",
            title=f"GO trials (n={self.count_trials('GO')})",
        )
        self.draw_trial_type_scatter(
            self.nogo_summary_ax,
            "NO-GO",
            title=f"NO-GO trials (n={self.count_trials('NO-GO')})",
        )

        if self.colorbar is None:
            self.colorbar = self.figure.colorbar(
                current_image,
                ax=self.current_grid_ax,
            )
            self.colorbar.set_label("Measured voltage (V)")
        else:
            self.colorbar.update_normal(current_image)

        self.trial_entry.set(str(trial["trial"]))
        self.summary.set(
            f"{self.current_index + 1}/{len(self.trials)} complete trials"
            f" | GO {self.count_trials('GO')}"
            f" | NO-GO {self.count_trials('NO-GO')}"
        )
        if self.incomplete_trials:
            incomplete = ", ".join(str(trial_id) for trial_id in self.incomplete_trials)
            self.status.set(f"Skipped incomplete trial(s): {incomplete}")
        else:
            self.status.set("All trial blocks are complete.")

        self.canvas.draw_idle()

    def count_trials(self, trial_type):
        return sum(trial["trial_type"].upper() == trial_type for trial in self.trials)

    def build_summary_dictionary(self):
        return {
            "source_file": self.file_path.get(),
            "incomplete_trials": self.incomplete_trials,
            "go": self.summary_for_trial_type("GO"),
            "nogo": self.summary_for_trial_type("NO-GO"),
        }

    def summary_for_trial_type(self, trial_type):
        values, pattern_labels = self.pattern_values_for_trial_type(trial_type)
        if values.size == 0:
            means = np.array([])
            stds = np.array([])
            trial_numbers = []
        else:
            means = np.nanmean(values, axis=0)
            stds = np.nanstd(values, axis=0)
            trial_numbers = [
                trial["trial"]
                for trial in self.trials
                if trial["trial_type"].upper() == trial_type
            ]

        return {
            "trial_type": trial_type,
            "pattern": pattern_labels,
            "trial_numbers": trial_numbers,
            "n_trials": len(trial_numbers),
            "values": values,
            "mean": means,
            "std": stds,
        }

    def pattern_values_for_trial_type(self, trial_type):
        values = []
        pattern_labels = None
        for trial in self.trials:
            if trial["trial_type"].upper() != trial_type:
                continue
            _pattern_name, pattern = select_pattern(self.metadata, trial)
            grid = voltages_to_pattern_grid(trial["voltages"], pattern)
            pattern_labels = pattern
            values.append([grid[row, col] for row, col in pattern_indices(pattern)])

        if not values:
            return np.empty((0, 0)), []
        return np.array(values, dtype=float), pattern_labels

    def draw_trial_type_scatter(self, ax, trial_type, title):
        ax.clear()
        values, pattern_labels = self.pattern_values_for_trial_type(trial_type)
        ax.set_title(title)
        ax.set_ylabel("Measured voltage (V)")
        ax.set_ylim(0, 9)
        ax.grid(True, axis="y", alpha=0.25)

        if values.size == 0:
            ax.text(0.5, 0.5, "No complete trials", ha="center", va="center")
            return

        x_positions = np.arange(values.shape[1])
        for position_index, x_position in enumerate(x_positions):
            y_values = values[:, position_index]
            jitter = np.linspace(-0.18, 0.18, len(y_values))
            ax.scatter(
                x_position + jitter,
                y_values,
                color="tab:blue" if trial_type == "GO" else "tab:orange",
                alpha=0.35,
                s=16,
                edgecolors="none",
            )

        means = np.nanmean(values, axis=0)
        stds = np.nanstd(values, axis=0)
        ax.errorbar(
            x_positions,
            means,
            yerr=stds,
            fmt="o",
            linestyle="None",
            color="black",
            capsize=4,
            markersize=5,
            label="mean +/- std",
        )

        ax.set_xticks(x_positions, labels=pattern_labels, rotation=45, ha="right")
        ax.legend(loc="upper right", fontsize=8)

    def draw_voltage_grid(self, ax, voltage_grid, title, annotate):
        ax.clear()

        masked_voltages = np.ma.masked_invalid(voltage_grid)
        cmap = plt.colormaps["viridis"].copy()
        cmap.set_bad(color="lightgray")
        heatmap_image = ax.imshow(
            masked_voltages, cmap=cmap, interpolation="nearest", vmin=0, vmax=9
        )

        ax.set_title(title)
        ax.set_xlabel("P channel")
        ax.set_ylabel("N channel")
        ax.set_xticks(np.arange(10), labels=[f"P{i}" for i in range(1, 11)])
        ax.set_yticks(np.arange(10), labels=[f"N{i}" for i in range(1, 11)])
        ax.tick_params(axis="x", rotation=45)

        if annotate:
            for row in range(voltage_grid.shape[0]):
                for col in range(voltage_grid.shape[1]):
                    if np.isnan(voltage_grid[row, col]):
                        continue
                    ax.text(
                        col,
                        row,
                        f"{voltage_grid[row, col]:.2f}",
                        ha="center",
                        va="center",
                        color="white" if voltage_grid[row, col] < 5 else "black",
                        fontsize=8,
                    )
        return heatmap_image


def main():
    root = Tk()
    TrialVoltageViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
