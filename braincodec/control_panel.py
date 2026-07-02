"""Reusable Jupyter control panel for Braincodec experiments.

This module is intentionally hardware-agnostic. It only owns the notebook UI
state, button callbacks, and log display, so experiment runners can import it
without pulling in PYNQ or LED-driver dependencies.
"""

from __future__ import annotations

from collections import deque
from typing import Callable, Optional

try:
    from IPython.display import display
    import ipywidgets as widgets
except ImportError as exc:  # pragma: no cover - only hit outside notebook envs
    display = None
    widgets = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


Callback = Callable[[], None]


class FixedLogBox:
    """A fixed-height log box that keeps the newest lines visible."""

    def __init__(self, max_lines: int = 50, width: str = "600px", height: str = "130px"):
        _require_widgets()
        self.max_lines = max_lines
        self.lines = deque(maxlen=max_lines)
        self.widget = widgets.Textarea(
            value="",
            description="Log:",
            disabled=True,
            layout=widgets.Layout(width=width, height=height),
        )

    def add_line(self, text: str) -> None:
        self.lines.append(str(text))
        display_lines = list(self.lines)
        while len(display_lines) < self.max_lines:
            display_lines.insert(0, "")
        self.widget.value = "\n".join(display_lines)

    def clear(self) -> None:
        self.lines.clear()
        self.widget.value = "\n" * max(self.max_lines - 1, 0)


class BraincodecControlPanel:
    """Jupyter widget panel used to start, stop, and monitor trials."""

    def __init__(
        self,
        *,
        on_start: Optional[Callback] = None,
        on_stop: Optional[Callback] = None,
        log_lines: int = 50,
    ):
        _require_widgets()
        self._on_start = on_start
        self._on_stop = on_stop

        self.start_button = widgets.Button(
            description="Start",
            button_style="success",
            layout=widgets.Layout(width="100px"),
        )
        self.stop_button = widgets.Button(
            description="Stop",
            button_style="danger",
            layout=widgets.Layout(width="100px"),
        )
        self.indicator = widgets.HTML(
            value=self._build_indicator("gray"),
            layout=widgets.Layout(width="80px", height="50px"),
        )
        self.progress = widgets.IntProgress(
            value=0,
            min=0,
            max=100,
            description="Trial:",
            bar_style="",
            layout=widgets.Layout(width="300px"),
        )
        self.status_label = widgets.Label(value="Status: Idle")
        self.info_label = widgets.Label(value="Info: Waiting")
        self.log_box = FixedLogBox(max_lines=log_lines)

        left_box = widgets.VBox([self.start_button, self.stop_button])
        right_box = widgets.VBox([self.indicator])
        top_row = widgets.HBox([left_box, right_box])
        bottom_section = widgets.VBox(
            [self.progress, self.status_label, self.info_label, self.log_box.widget]
        )
        self.widget = widgets.VBox([top_row, bottom_section])

        self.start_button.on_click(self._handle_start)
        self.stop_button.on_click(self._handle_stop)

    @property
    def panel(self):
        """Backward-compatible alias for callers that expect `.panel`."""
        return self.widget

    @property
    def error_box(self):
        """Backward-compatible alias for the old driver panel API."""
        return self.log_box

    def set_start_callback(self, callback: Optional[Callback]) -> None:
        self._on_start = callback

    def set_stop_callback(self, callback: Optional[Callback]) -> None:
        self._on_stop = callback

    def set_indicator(self, color: str) -> None:
        self.indicator.value = self._build_indicator(color)

    def set_progress(self, value: int, maximum: Optional[int] = None) -> None:
        if maximum is not None:
            self.progress.max = maximum
        self.progress.value = value

    def set_status(self, text: str) -> None:
        self.status_label.value = f"Status: {text}"

    def set_info(self, text: str) -> None:
        self.info_label.value = f"Info: {text}"

    def add_log_line(self, text: str) -> None:
        self.log_box.add_line(text)

    def clear_log(self) -> None:
        self.log_box.clear()

    def show(self) -> None:
        if display is None:
            raise RuntimeError("IPython is required to display the Braincodec control panel.")
        display(self.widget)

    def _handle_start(self, _button) -> None:
        if self._on_start is not None:
            self._on_start()

    def _handle_stop(self, _button) -> None:
        if self._on_stop is not None:
            self._on_stop()

    @staticmethod
    def _build_indicator(color: str) -> str:
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


def _require_widgets() -> None:
    if _IMPORT_ERROR is not None:
        raise RuntimeError(
            "ipywidgets and IPython are required to use the Braincodec control panel."
        ) from _IMPORT_ERROR

