"""RepoManagerDialog — 저장소 추가/삭제/전환 관리 다이얼로그."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.controller.workflow_controller import WorkflowController
from app.domain.models import RepoConfig


class RepoManagerDialog(QDialog):
    """저장소 추가/삭제/활성화 관리 다이얼로그.

    변경 사항이 있으면 repos_changed 시그널 방출.
    """

    repos_changed = pyqtSignal()

    def __init__(self, controller: WorkflowController, parent=None) -> None:
        super().__init__(parent)
        self._controller = controller
        self.setWindowTitle("저장소 관리")
        self.setMinimumWidth(560)
        self.setMinimumHeight(400)
        self._setup_ui()
        self._load_repos()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── 저장소 목록 ────────────────────────────────────────────────
        list_label = QLabel("등록된 저장소")
        list_label.setStyleSheet("font-weight:600; color:#94a3b8; font-size:11px; letter-spacing:0.8px;")
        layout.addWidget(list_label)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.itemDoubleClicked.connect(self._on_activate)
        layout.addWidget(self._list, stretch=1)

        # 목록 하단 버튼
        list_btns = QHBoxLayout()
        self._activate_btn = QPushButton("✓ 활성화")
        self._activate_btn.setToolTip("선택한 저장소를 활성 저장소로 전환")
        self._activate_btn.clicked.connect(self._on_activate)
        self._remove_btn = QPushButton("✕ 삭제")
        self._remove_btn.setToolTip("선택한 저장소를 목록에서 제거")
        self._remove_btn.setStyleSheet(
            "background-color:#7f1d1d; color:#fca5a5;"
            "border-radius:6px; padding:6px 14px;"
        )
        self._remove_btn.clicked.connect(self._on_remove)
        list_btns.addWidget(self._activate_btn)
        list_btns.addWidget(self._remove_btn)
        list_btns.addStretch()
        layout.addLayout(list_btns)

        # ── 구분선 ─────────────────────────────────────────────────────
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color:#2d2d4a;")
        layout.addWidget(separator)

        # ── 새 저장소 추가 ─────────────────────────────────────────────
        add_label = QLabel("새 저장소 추가")
        add_label.setStyleSheet("font-weight:600; color:#94a3b8; font-size:11px; letter-spacing:0.8px;")
        layout.addWidget(add_label)

        # 경로 입력 행
        path_row = QHBoxLayout()
        self._path_input = QLineEdit()
        self._path_input.setPlaceholderText("/Users/jypark/dev/my-project")
        self._path_input.setMinimumHeight(34)
        path_row.addWidget(self._path_input, stretch=1)

        browse_btn = QPushButton("폴더 선택")
        browse_btn.setFixedWidth(90)
        browse_btn.setStyleSheet(
            "background-color:#252540; color:#a5b4fc;"
            "border:1px solid #3d3d6b; border-radius:6px; padding:6px 10px;"
        )
        browse_btn.clicked.connect(self._on_browse)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        # 이름 입력 행
        name_row = QHBoxLayout()
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("저장소 이름 (비워두면 폴더명 자동 사용)")
        self._name_input.setMinimumHeight(34)
        name_row.addWidget(self._name_input)
        layout.addLayout(name_row)

        add_btn = QPushButton("＋ 저장소 추가")
        add_btn.setFixedHeight(36)
        add_btn.clicked.connect(self._on_add)
        layout.addWidget(add_btn)

        # ── 닫기 버튼 ─────────────────────────────────────────────────
        close_btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn.rejected.connect(self.reject)
        layout.addWidget(close_btn)

    def _load_repos(self) -> None:
        self._list.clear()
        for repo in self._controller._config.get_repositories():
            item = QListWidgetItem()
            active_mark = "  ●" if repo.is_active else "   "
            item.setText(f"{active_mark}  {repo.name}   —   {repo.path}")
            item.setData(Qt.ItemDataRole.UserRole, repo.path)
            if repo.is_active:
                item.setForeground(Qt.GlobalColor.cyan)
            self._list.addItem(item)

    def _on_browse(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Git 저장소 선택", str(Path.home())
        )
        if path:
            self._path_input.setText(path)
            # 이름 자동 채우기
            if not self._name_input.text():
                self._name_input.setText(Path(path).name)

    def _on_add(self) -> None:
        path = self._path_input.text().strip()
        name = self._name_input.text().strip() or Path(path).name if path else ""

        if not path:
            QMessageBox.warning(self, "입력 오류", "저장소 경로를 입력해주세요.")
            return

        ok = self._controller.add_repository(path, name)
        if ok:
            self._path_input.clear()
            self._name_input.clear()
            self._load_repos()
            self.repos_changed.emit()
        else:
            QMessageBox.critical(self, "추가 실패", f"유효한 Git 저장소가 아닙니다:\n{path}")

    def _on_activate(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        self._controller.switch_repository(path)
        self._load_repos()
        self.repos_changed.emit()

    def _on_remove(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        name = path.split("/")[-1]
        reply = QMessageBox.question(
            self, "삭제 확인",
            f"'{name}' 저장소를 목록에서 제거하시겠습니까?\n(로컬 파일은 삭제되지 않습니다)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._controller.remove_repository(path)
            self._load_repos()
            self.repos_changed.emit()
