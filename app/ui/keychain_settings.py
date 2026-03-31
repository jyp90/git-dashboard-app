"""KeychainSettingsPanel — macOS Keychain 자격증명 관리 UI."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
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

if TYPE_CHECKING:
    from app.infrastructure.keychain_service import KeychainService


_STYLE = """
QWidget { background-color: #1e1e1e; color: #d4d4d4; }
QGroupBox { border: 1px solid #3c3c3c; border-radius: 4px; margin-top: 8px; padding-top: 8px; }
QGroupBox::title { color: #888; font-size: 11px; }
QListWidget { background: #252526; border: 1px solid #3c3c3c; }
QListWidget::item:selected { background: #264f78; }
QLineEdit { background: #3c3c3c; color: #d4d4d4; border: 1px solid #555; padding: 4px; }
QPushButton { background: #3c3c3c; color: #d4d4d4; border: 1px solid #555; padding: 4px 12px; }
QPushButton:hover { background: #4a4a4a; }
QPushButton:disabled { background: #2a2a2a; color: #555; }
"""

_BTN_DANGER = "QPushButton { background: #c0392b; color: #fff; border: none; padding: 4px 12px; } QPushButton:hover { background: #e74c3c; }"
_BTN_PRIMARY = "QPushButton { background: #2980b9; color: #fff; border: none; padding: 4px 12px; } QPushButton:hover { background: #3498db; }"


class _AddCredentialDialog(QDialog):
    """자격증명 추가 다이얼로그."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Git 자격증명 추가")
        self.setMinimumWidth(400)
        self.setStyleSheet(_STYLE)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("예: https://git-codecommit.ap-northeast-2.amazonaws.com")
        form.addRow("Remote URL:", self._url_edit)

        self._user_edit = QLineEdit()
        self._user_edit.setPlaceholderText("예: jypark")
        form.addRow("Username:", self._user_edit)

        self._token_edit = QLineEdit()
        self._token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._token_edit.setPlaceholderText("Access token 또는 비밀번호")
        form.addRow("Token:", self._token_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate_and_accept(self) -> None:
        if not self._url_edit.text().strip():
            QMessageBox.warning(self, "입력 오류", "Remote URL을 입력하세요.")
            return
        if not self._token_edit.text().strip():
            QMessageBox.warning(self, "입력 오류", "Token을 입력하세요.")
            return
        self.accept()

    def get_values(self) -> tuple[str, str, str]:
        return (
            self._url_edit.text().strip(),
            self._user_edit.text().strip(),
            self._token_edit.text().strip(),
        )


class KeychainSettingsPanel(QWidget):
    """macOS Keychain에 저장된 Git 자격증명 관리 패널.

    기능:
    - 저장된 자격증명 목록 표시 (token 마스킹)
    - 자격증명 추가 / 삭제
    - Keychain 가용성 상태 표시
    """

    credential_changed = pyqtSignal()  # 자격증명 추가/삭제 시

    def __init__(self, keychain_service: "KeychainService", parent=None) -> None:
        super().__init__(parent)
        self._svc = keychain_service
        self._setup_ui()
        self.refresh()

    # ─── UI 구성 ────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setStyleSheet(_STYLE)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 상태 표시
        status_group = QGroupBox("Keychain 상태")
        status_layout = QHBoxLayout(status_group)

        self._status_label = QLabel()
        self._status_label.setFont(QFont("Menlo", 12))
        status_layout.addWidget(self._status_label)
        status_layout.addStretch()
        layout.addWidget(status_group)

        # 자격증명 목록
        cred_group = QGroupBox("저장된 Git 자격증명")
        cred_layout = QVBoxLayout(cred_group)

        self._cred_list = QListWidget()
        self._cred_list.setFont(QFont("Menlo", 11))
        self._cred_list.currentRowChanged.connect(self._on_selection_changed)
        cred_layout.addWidget(self._cred_list)

        # 버튼 행
        btn_row = QHBoxLayout()
        self._add_btn = QPushButton("+ 추가")
        self._add_btn.setStyleSheet(_BTN_PRIMARY)
        self._add_btn.clicked.connect(self._on_add)

        self._del_btn = QPushButton("- 삭제")
        self._del_btn.setStyleSheet(_BTN_DANGER)
        self._del_btn.setEnabled(False)
        self._del_btn.clicked.connect(self._on_delete)

        refresh_btn = QPushButton("↻ 새로고침")
        refresh_btn.clicked.connect(self.refresh)

        btn_row.addWidget(self._add_btn)
        btn_row.addWidget(self._del_btn)
        btn_row.addStretch()
        btn_row.addWidget(refresh_btn)
        cred_layout.addLayout(btn_row)
        layout.addWidget(cred_group)

        # 앱 설정 섹션
        settings_group = QGroupBox("앱 설정 (Keychain 저장)")
        settings_layout = QVBoxLayout(settings_group)

        cleanup_btn = QPushButton("🗑  앱 관련 모든 Keychain 항목 삭제")
        cleanup_btn.setStyleSheet(_BTN_DANGER)
        cleanup_btn.clicked.connect(self._on_cleanup_all)
        settings_layout.addWidget(cleanup_btn)
        layout.addWidget(settings_group)

    # ─── 공개 API ────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Keychain 상태 및 자격증명 목록 새로고침."""
        available = self._svc.is_available()
        if available:
            self._status_label.setText("✅ macOS Keychain 사용 가능")
            self._status_label.setStyleSheet("color: #2ecc71;")
        else:
            self._status_label.setText("❌ Keychain 사용 불가 (macOS 전용)")
            self._status_label.setStyleSheet("color: #e74c3c;")

        self._add_btn.setEnabled(available)
        self._cred_list.clear()

        if not available:
            return

        creds = self._svc.list_git_credentials()
        for cred in creds:
            service = cred.get("service", "")
            username = cred.get("username", "(unknown)")
            token = cred.get("token_masked", cred.get("token", ""))
            masked = token if token else "(없음)"
            item = QListWidgetItem(f"{service}  |  {username}  |  {masked}")
            item.setData(Qt.ItemDataRole.UserRole, cred)
            self._cred_list.addItem(item)

        if self._cred_list.count() == 0:
            self._cred_list.addItem(QListWidgetItem("(저장된 자격증명 없음)"))

    # ─── 이벤트 ─────────────────────────────────────────────────────────────

    def _on_selection_changed(self, row: int) -> None:
        item = self._cred_list.item(row)
        has_data = item is not None and item.data(Qt.ItemDataRole.UserRole) is not None
        self._del_btn.setEnabled(has_data)

    def _on_add(self) -> None:
        dialog = _AddCredentialDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        url, username, token = dialog.get_values()
        ok = self._svc.store_git_credential(url, username, token)
        if ok:
            QMessageBox.information(self, "저장 완료", f"{url} 자격증명이 Keychain에 저장되었습니다.")
            self.refresh()
            self.credential_changed.emit()
        else:
            QMessageBox.critical(self, "저장 실패", "Keychain 저장에 실패했습니다.\n권한을 확인하세요.")

    def _on_delete(self) -> None:
        item = self._cred_list.currentItem()
        if item is None:
            return
        cred = item.data(Qt.ItemDataRole.UserRole)
        if cred is None:
            return

        service = cred.get("service", "")
        reply = QMessageBox.question(
            self,
            "자격증명 삭제",
            f"다음 자격증명을 삭제할까요?\n\n{service}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # service name에서 URL 역산 (com.git-dashboard.git-credential.{host})
        parts = service.split(".")
        if len(parts) >= 4:
            host = ".".join(parts[3:])
            ok = self._svc.delete_git_credential(f"https://{host}")
        else:
            ok = False

        if ok:
            self.refresh()
            self.credential_changed.emit()
        else:
            QMessageBox.critical(self, "삭제 실패", "Keychain 항목 삭제에 실패했습니다.")

    def _on_cleanup_all(self) -> None:
        reply = QMessageBox.warning(
            self,
            "전체 삭제",
            "Git Dashboard 관련 모든 Keychain 항목을 삭제합니다.\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        count = self._svc.cleanup_all()
        QMessageBox.information(self, "삭제 완료", f"{count}개 항목이 삭제되었습니다.")
        self.refresh()
        self.credential_changed.emit()
