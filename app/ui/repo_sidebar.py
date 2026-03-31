"""RepoSidebar — 좌측 저장소 목록 패널."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.controller.workflow_controller import WorkflowController
from app.domain.models import BranchStatus


# 상태별 색상
_STATUS_STYLE = {
    BranchStatus.CLEAN:    ("#22c55e", "CLEAN"),
    BranchStatus.DIRTY:    ("#f59e0b", "DIRTY"),
    BranchStatus.AHEAD:    ("#60a5fa", "AHEAD"),
    BranchStatus.BEHIND:   ("#f87171", "BEHIND"),
    BranchStatus.DIVERGED: ("#c084fc", "DIVERG"),
}


class RepoSidebar(QWidget):
    """모든 등록 저장소를 리스트로 표시. 클릭 시 저장소 전환."""

    repo_selected = pyqtSignal(str)   # path

    def __init__(self, controller: WorkflowController, parent=None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._status_cache: dict[str, BranchStatus] = {}
        self._setup_ui()
        self._load()

    def _setup_ui(self) -> None:
        self.setFixedWidth(190)
        self.setStyleSheet("background-color:#12121f; border-right:1px solid #2d2d4a;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 헤더
        header = QLabel("  REPOSITORIES")
        header.setFixedHeight(36)
        header.setStyleSheet(
            "color:#475569; font-size:10px; font-weight:700; letter-spacing:1.2px;"
            "background:#0f0f17; border-bottom:1px solid #1e1e38; padding-left:12px;"
        )
        layout.addWidget(header)

        # 저장소 리스트
        self._list = QListWidget()
        self._list.setFrameShape(QListWidget.Shape.NoFrame)
        self._list.setStyleSheet("""
            QListWidget {
                background: #12121f;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-bottom: 1px solid #1a1a2e;
                color: #94a3b8;
                font-size: 13px;
            }
            QListWidget::item:hover {
                background: #1a1a2e;
                color: #e2e8f0;
            }
            QListWidget::item:selected {
                background: #1e1e38;
                color: #a5b4fc;
                border-left: 3px solid #6366f1;
            }
        """)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self._list, stretch=1)

        # 관리 버튼
        manage_btn = QPushButton("＋  저장소 관리")
        manage_btn.setFixedHeight(36)
        manage_btn.setStyleSheet(
            "QPushButton { background:#1a1a2e; color:#6366f1; border:none;"
            "border-top:1px solid #2d2d4a; font-size:12px; text-align:left; padding-left:14px; }"
            "QPushButton:hover { background:#1e1e38; color:#818cf8; }"
        )
        manage_btn.clicked.connect(self._open_manager)
        layout.addWidget(manage_btn)

    def _load(self) -> None:
        self._list.clear()
        active = self._controller.get_active_repo()
        for repo in self._controller.get_repositories():
            item = QListWidgetItem()
            status = self._status_cache.get(repo.path)
            dot, color = self._status_dot(status)
            item.setText(f"{dot}  {repo.name}")
            item.setData(Qt.ItemDataRole.UserRole, repo.path)
            item.setToolTip(repo.path)
            self._list.addItem(item)
            if active and repo.path == active.path:
                self._list.setCurrentItem(item)

    def _status_dot(self, status: BranchStatus | None) -> tuple[str, str]:
        if status is None:
            return "○", "#475569"
        color, _ = _STATUS_STYLE.get(status, ("#475569", ""))
        return "●", color

    def update_repo_status(self, path: str, status: BranchStatus) -> None:
        """외부에서 저장소 상태를 업데이트하면 리스트 아이콘 갱신."""
        self._status_cache[path] = status
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == path:
                for r in self._controller.get_repositories():
                    if r.path == path:
                        dot, color = self._status_dot(status)
                        item.setText(f"{dot}  {r.name}")
                        break
                break

    def refresh(self) -> None:
        self._load()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.repo_selected.emit(path)

    def _on_context_menu(self, pos) -> None:
        """우클릭 컨텍스트 메뉴."""
        item = self._list.itemAt(pos)
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background:#1a1a2e; border:1px solid #2d2d4a; color:#d4d4d4; }
            QMenu::item { padding:6px 20px; }
            QMenu::item:selected { background:#252550; color:#a5b4fc; }
        """)
        rename_action = menu.addAction("✎  이름 변경")
        menu.addSeparator()
        remove_action = menu.addAction("✕  삭제")

        action = menu.exec(self._list.mapToGlobal(pos))
        if action == rename_action:
            self._rename_repo(path)
        elif action == remove_action:
            self._remove_repo(path)

    def _rename_repo(self, path: str) -> None:
        """저장소 이름 변경."""
        # 현재 이름 조회
        current_name = path.split("/")[-1]
        for repo in self._controller.get_repositories():
            if repo.path == path:
                current_name = repo.name
                break

        new_name, ok = QInputDialog.getText(
            self, "저장소 이름 변경", "새 이름:", text=current_name
        )
        if ok and new_name.strip():
            self._controller.rename_repository(path, new_name.strip())
            self.refresh()

    def _remove_repo(self, path: str) -> None:
        """저장소 삭제."""
        name = path.split("/")[-1]
        reply = QMessageBox.question(
            self, "삭제 확인",
            f"'{name}' 저장소를 목록에서 제거하시겠습니까?\n(로컬 파일은 삭제되지 않습니다)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._controller.remove_repository(path)
            self.refresh()

    def _open_manager(self) -> None:
        from app.ui.repo_manager_dialog import RepoManagerDialog
        dialog = RepoManagerDialog(self._controller, self)
        dialog.repos_changed.connect(self.refresh)
        dialog.exec()
