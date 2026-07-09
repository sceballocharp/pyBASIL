# -*- coding: utf-8 -*-

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


DEFAULT_NPY_FILE = Path(
    r"Y:\User_folders\Sebastian\Braincodec\codes_4904be24_500-to-2000_clamped-0-10_left-rot90.npy"
)


class NpyVoltageGridViewer:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("NPY Voltage Grid Viewer")
        self.root.geometry("1000x720")
        self.root.minsize(850, 560)

        self.file_path_var = tk.StringVar(value=str(DEFAULT_NPY_FILE))
        self.status_var = tk.StringVar(value="Load a .npy file to begin.")
        self.trial_index_var = tk.StringVar(value="0")
        self.time_index_var = tk.StringVar(value="0")
        self.trial_count_var = tk.StringVar(value="Trial 0/0")
        self.time_count_var = tk.StringVar(value="Time 0/0")
        self.array: np.ndarray | None = None
        self.frame_colorbar = None
        self.mean_colorbar = None
        self.trial_index = 0
        self.time_index = 0
        self.is_playing = False
        self.play_after_id = None
        self.nav_buttons: list[ttk.Button] = []

        self._build_layout()
        if DEFAULT_NPY_FILE.exists():
            self._load_file(DEFAULT_NPY_FILE)
        else:
            self._draw_empty_grid()

    def _build_layout(self) -> None:
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill="both", expand=True)

        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill="x")

        ttk.Button(file_frame, text="Browse NPY", command=self._browse_npy).pack(
            side="left"
        )
        ttk.Entry(file_frame, textvariable=self.file_path_var).pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Button(file_frame, text="Load", command=self._load_current_path).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(file_frame, text="Quit", command=self.root.destroy).pack(side="left")

        nav_frame = ttk.Frame(main_frame)
        nav_frame.pack(fill="x", pady=(10, 0))

        ttk.Label(nav_frame, text="Stim/trial").pack(side="left")
        self.prev_trial_button = ttk.Button(
            nav_frame, text="Previous", command=self._previous_trial, state="disabled"
        )
        self.prev_trial_button.pack(side="left", padx=(8, 4))
        self.next_trial_button = ttk.Button(
            nav_frame, text="Next", command=self._next_trial, state="disabled"
        )
        self.next_trial_button.pack(side="left", padx=(0, 8))
        ttk.Entry(nav_frame, textvariable=self.trial_index_var, width=6).pack(side="left")
        ttk.Button(nav_frame, text="Go", command=self._go_to_trial).pack(
            side="left", padx=(4, 8)
        )
        ttk.Label(nav_frame, textvariable=self.trial_count_var).pack(side="left")

        ttk.Separator(nav_frame, orient="vertical").pack(
            side="left", fill="y", padx=18
        )

        ttk.Label(nav_frame, text="Time").pack(side="left")
        self.prev_time_button = ttk.Button(
            nav_frame, text="Previous", command=self._previous_time, state="disabled"
        )
        self.prev_time_button.pack(side="left", padx=(8, 4))
        self.next_time_button = ttk.Button(
            nav_frame, text="Next", command=self._next_time, state="disabled"
        )
        self.next_time_button.pack(side="left", padx=(0, 8))
        ttk.Entry(nav_frame, textvariable=self.time_index_var, width=6).pack(side="left")
        ttk.Button(nav_frame, text="Go", command=self._go_to_time).pack(
            side="left", padx=(4, 8)
        )
        ttk.Label(nav_frame, textvariable=self.time_count_var).pack(side="left")
        self.play_button = ttk.Button(
            nav_frame, text="Play", command=self._toggle_playback, state="disabled"
        )
        self.play_button.pack(side="left", padx=(18, 0))

        self.nav_buttons = [
            self.prev_trial_button,
            self.next_trial_button,
            self.prev_time_button,
            self.next_time_button,
            self.play_button,
        ]

        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.frame_ax = self.figure.add_subplot(1, 2, 1)
        self.mean_ax = self.figure.add_subplot(1, 2, 2)
        self.canvas = FigureCanvasTkAgg(self.figure, master=main_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, pady=(12, 8))

        ttk.Label(main_frame, textvariable=self.status_var).pack(fill="x")

    def _browse_npy(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select NPY file",
            filetypes=(("NumPy arrays", "*.npy"), ("All files", "*.*")),
        )
        if selected:
            self.file_path_var.set(selected)
            self._load_file(Path(selected))

    def _load_current_path(self) -> None:
        path_text = self.file_path_var.get().strip()
        if not path_text:
            messagebox.showwarning("No file", "Choose a .npy file first.")
            return
        self._load_file(Path(path_text))

    def _load_file(self, path: Path) -> None:
        try:
            array = np.load(path, allow_pickle=False)
        except Exception as error:
            messagebox.showerror("Could not load .npy file", str(error))
            return

        self.array = np.asarray(array)
        self.trial_index = 0
        self.time_index = 0
        self._stop_playback()
        self.file_path_var.set(str(path))
        self._sync_navigation_labels()
        self._set_navigation_enabled(self._has_trial_time_grid())
        self._update_plot()

    def _grid_from_array(self) -> tuple[np.ndarray, str] | tuple[None, str]:
        if self.array is None:
            return None, ""

        squeezed = np.squeeze(self.array)
        if self._has_trial_time_grid():
            trial = min(self.trial_index, self.array.shape[0] - 1)
            time = min(self.time_index, self.array.shape[3] - 1)
            grid = self.array[trial, :, :, time]
            return np.asarray(grid, dtype=float), f"trial {trial}, time {time}"

        if squeezed.shape == (10, 10):
            return np.asarray(squeezed, dtype=float), "full array"

        if squeezed.ndim > 2 and squeezed.shape[-2:] == (10, 10):
            return np.asarray(squeezed.reshape(-1, 10, 10)[0], dtype=float), "first trailing 10 x 10 slice"

        for axis in range(squeezed.ndim - 1):
            if squeezed.shape[axis : axis + 2] != (10, 10):
                continue
            selector = [0] * squeezed.ndim
            selector[axis] = slice(None)
            selector[axis + 1] = slice(None)
            grid = squeezed[tuple(selector)]
            return np.asarray(grid, dtype=float), f"first slice across axes {axis} and {axis + 1}"

        return None, ""

    def _mean_grid_for_current_trial(self) -> np.ndarray | None:
        if not self._has_trial_time_grid():
            return None
        trial = min(self.trial_index, self.array.shape[0] - 1)
        return np.asarray(np.nanmean(self.array[trial, :, :, :], axis=2), dtype=float)

    def _has_trial_time_grid(self) -> bool:
        return self.array is not None and self.array.ndim == 4 and self.array.shape[1:3] == (10, 10)

    def _set_navigation_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for button in self.nav_buttons:
            button.configure(state=state)

    def _sync_navigation_labels(self) -> None:
        self.trial_index_var.set(str(self.trial_index))
        self.time_index_var.set(str(self.time_index))

        if self._has_trial_time_grid():
            self.trial_count_var.set(
                f"Trial {self.trial_index + 1}/{self.array.shape[0]}"
            )
            self.time_count_var.set(f"Time {self.time_index + 1}/{self.array.shape[3]}")
        else:
            self.trial_count_var.set("Trial 0/0")
            self.time_count_var.set("Time 0/0")

    def _previous_trial(self) -> None:
        if not self._has_trial_time_grid():
            return
        self.trial_index = max(0, self.trial_index - 1)
        self._sync_navigation_labels()
        self._update_plot()

    def _next_trial(self) -> None:
        if not self._has_trial_time_grid():
            return
        self.trial_index = min(self.array.shape[0] - 1, self.trial_index + 1)
        self._sync_navigation_labels()
        self._update_plot()

    def _previous_time(self) -> None:
        if not self._has_trial_time_grid():
            return
        self.time_index = max(0, self.time_index - 1)
        self._sync_navigation_labels()
        self._update_plot()

    def _next_time(self) -> None:
        if not self._has_trial_time_grid():
            return
        self.time_index = min(self.array.shape[3] - 1, self.time_index + 1)
        self._sync_navigation_labels()
        self._update_plot()

    def _advance_time_for_playback(self) -> None:
        if not self.is_playing or not self._has_trial_time_grid():
            self._stop_playback()
            return

        self.time_index = (self.time_index + 1) % self.array.shape[3]
        self._sync_navigation_labels()
        self._update_plot()
        self.play_after_id = self.root.after(500, self._advance_time_for_playback)

    def _toggle_playback(self) -> None:
        if self.is_playing:
            self._stop_playback()
            return

        if not self._has_trial_time_grid():
            return
        self.is_playing = True
        self.play_button.configure(text="Pause")
        self.play_after_id = self.root.after(500, self._advance_time_for_playback)

    def _stop_playback(self) -> None:
        self.is_playing = False
        if self.play_after_id is not None:
            try:
                self.root.after_cancel(self.play_after_id)
            except ValueError:
                pass
            self.play_after_id = None
        if hasattr(self, "play_button"):
            self.play_button.configure(text="Play")

    def _go_to_trial(self) -> None:
        if not self._has_trial_time_grid():
            return
        try:
            trial_index = int(self.trial_index_var.get())
        except ValueError:
            messagebox.showwarning("Invalid trial", "Enter a numeric trial index.")
            self._sync_navigation_labels()
            return
        self.trial_index = min(max(0, trial_index), self.array.shape[0] - 1)
        self._sync_navigation_labels()
        self._update_plot()

    def _go_to_time(self) -> None:
        if not self._has_trial_time_grid():
            return
        try:
            time_index = int(self.time_index_var.get())
        except ValueError:
            messagebox.showwarning("Invalid time", "Enter a numeric time index.")
            self._sync_navigation_labels()
            return
        self.time_index = min(max(0, time_index), self.array.shape[3] - 1)
        self._sync_navigation_labels()
        self._update_plot()

    def _draw_empty_grid(self) -> None:
        for ax, title in (
            (self.frame_ax, "Current trial voltage grid placeholder"),
            (self.mean_ax, "Mean across time placeholder"),
        ):
            ax.clear()
            ax.set_title(title)
            ax.set_xlabel("P channel")
            ax.set_ylabel("N channel")
            ax.set_xticks(np.arange(10), labels=[f"P{i}" for i in range(1, 11)])
            ax.set_yticks(np.arange(10), labels=[f"N{i}" for i in range(1, 11)])
            ax.grid(True, color="#d0d0d0", linewidth=0.8)
            ax.set_xlim(-0.5, 9.5)
            ax.set_ylim(9.5, -0.5)
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _update_plot(self) -> None:
        grid, slice_description = self._grid_from_array()
        if grid is None:
            self._draw_empty_grid()
            self.status_var.set(
                f"Loaded array with shape {self.array.shape}; no 10 x 10 grid plotted yet."
            )
            return

        self.frame_ax.clear()
        image = self.frame_ax.imshow(
            grid, cmap="Greys", interpolation="nearest", vmin=0, vmax=9
        )
        self.frame_ax.set_title("Current trial voltage grid")
        self.frame_ax.set_xlabel("P channel")
        self.frame_ax.set_ylabel("N channel")
        self.frame_ax.set_xticks(np.arange(10), labels=[f"P{i}" for i in range(1, 11)])
        self.frame_ax.set_yticks(np.arange(10), labels=[f"N{i}" for i in range(1, 11)])
        self.frame_ax.tick_params(axis="x", rotation=45)

        if self.frame_colorbar is None:
            self.frame_colorbar = self.figure.colorbar(
                image,
                ax=self.frame_ax,
                fraction=0.035,
                pad=0.025,
                shrink=0.82,
            )
            self.frame_colorbar.set_label("Measured voltage (V)")
        else:
            self.frame_colorbar.update_normal(image)

        mean_grid = self._mean_grid_for_current_trial()
        self.mean_ax.clear()
        if mean_grid is None:
            self.mean_ax.set_title("Mean across time unavailable")
            self.mean_ax.text(0.5, 0.5, "No trial x grid x time array", ha="center", va="center")
            self.mean_ax.axis("off")
        else:
            mean_image = self.mean_ax.imshow(
                mean_grid, cmap="Greys", interpolation="nearest", vmin=0, vmax=9
            )
            self.mean_ax.set_title(f"Trial {self.trial_index} mean across time")
            self.mean_ax.set_xlabel("P channel")
            self.mean_ax.set_ylabel("N channel")
            self.mean_ax.set_xticks(np.arange(10), labels=[f"P{i}" for i in range(1, 11)])
            self.mean_ax.set_yticks(np.arange(10), labels=[f"N{i}" for i in range(1, 11)])
            self.mean_ax.tick_params(axis="x", rotation=45)

            if self.mean_colorbar is None:
                self.mean_colorbar = self.figure.colorbar(
                    mean_image,
                    ax=self.mean_ax,
                    fraction=0.035,
                    pad=0.025,
                    shrink=0.82,
                )
                self.mean_colorbar.set_label("Mean voltage (V)")
            else:
                self.mean_colorbar.update_normal(mean_image)

        self.figure.tight_layout()
        self.canvas.draw_idle()
        self.status_var.set(
            f"Loaded {self.array.shape}; showing {slice_description} from {self.file_path_var.get()}"
        )
        self._sync_navigation_labels()


def main() -> None:
    root = tk.Tk()
    NpyVoltageGridViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
