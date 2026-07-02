"""Braincodec helpers for pyBEHAVIOR."""

try:
    from .control_panel import BraincodecControlPanel, FixedLogBox
except ImportError:
    BraincodecControlPanel = None
    FixedLogBox = None

from .tk_panel import BraincodecStandaloneApp, BraincodecTkPanel

__all__ = [
    "BraincodecControlPanel",
    "FixedLogBox",
    "BraincodecStandaloneApp",
    "BraincodecTkPanel",
]
