"""
Qt Signal-based logging handler that captures Python log records
and safely directs them into the GUI log console.
"""

from __future__ import annotations

import logging
from PySide6.QtCore import QObject, Signal


class LogEmitter(QObject):
    """QObject wrapper holding the logging signal."""

    log_record_received = Signal(str, str, str)  # timestamp, level, message


class QtLogHandler(logging.Handler):
    """
    Custom logging.Handler that formats records and dispatches them via Qt signals.
    Ensures thread-safe dispatch into GUI widgets.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__()
        self.emitter = LogEmitter(parent)
        self.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            time_str = record.asctime if hasattr(record, "asctime") else ""
            level = record.levelname
            self.emitter.log_record_received.emit(time_str, level, msg)
        except RuntimeError:
            # Handles case where Qt C++ object has been disposed/deleted
            pass
        except Exception:
            self.handleError(record)
