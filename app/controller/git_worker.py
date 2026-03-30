"""GitWorker — Git 작업을 QThread에서 실행해 UI 블로킹 방지."""
from __future__ import annotations

from typing import Callable, Any

from PyQt6.QtCore import QThread, pyqtSignal


class GitWorker(QThread):
    """범용 QThread 래퍼. 호출 가능한 task를 백그라운드에서 실행한다.

    Usage:
        worker = GitWorker(lambda: branch_manager.sync_develop())
        worker.result_ready.connect(on_result)
        worker.error_occurred.connect(on_error)
        worker.start()
    """

    result_ready: pyqtSignal = pyqtSignal(object)
    error_occurred: pyqtSignal = pyqtSignal(str)
    progress: pyqtSignal = pyqtSignal(str)

    def __init__(self, task: Callable[[], Any], parent=None) -> None:
        super().__init__(parent)
        self._task = task

    def run(self) -> None:
        try:
            result = self._task()
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))
