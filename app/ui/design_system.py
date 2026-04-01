"""Design System — Git Dashboard PyQt6 Design Tokens.

phase-5-design-system 스킬 기반으로 생성된 중앙 집중식 디자인 토큰.
모든 UI 컴포넌트는 여기서 색상·폰트·간격·스타일을 가져올 것.
"""
from __future__ import annotations


# ── Color Palette ───────────────────────────────────────────────────────────

class C:
    """Color tokens."""

    # Background layers
    BG_DEEP    = "#060612"   # 가장 깊은 배경 (윈도우 외곽)
    BG_BASE    = "#0f0f1a"   # 메인 배경
    BG_SURFACE = "#14142a"   # 패널/카드 배경
    BG_RAISED  = "#1a1a2e"   # 툴바·탭 배경
    BG_HOVER   = "#20203a"   # hover 상태
    BG_ACTIVE  = "#252545"   # 선택/활성 상태
    BG_PRESSED = "#2d2d55"   # pressed 상태

    # Borders
    BORDER_FAINT   = "#16162c"  # 구분선 (barely visible)
    BORDER_SUBTLE  = "#1e1e38"  # 기본 구분선
    BORDER_DEFAULT = "#2d2d4a"  # 일반 테두리
    BORDER_STRONG  = "#3d3d6b"  # 강조 테두리
    BORDER_ACCENT  = "#4f4fa8"  # 액센트 테두리

    # Text
    TEXT_BRIGHT    = "#f1f5f9"   # 제목·강조
    TEXT_PRIMARY   = "#e2e8f0"   # 본문
    TEXT_SECONDARY = "#94a3b8"   # 부제목·레이블
    TEXT_MUTED     = "#64748b"   # 비활성·placeholder
    TEXT_DISABLED  = "#3d4f66"   # 완전 비활성

    # Accent (Sky Blue)
    ACCENT        = "#0ea5e9"   # Primary accent — sky-500
    ACCENT_HOVER  = "#38bdf8"   # Hover — sky-400
    ACCENT_LIGHT  = "#7dd3fc"   # Active/selected text — sky-300
    ACCENT_SUBTLE = "#0c4a6e"   # Selected background
    ACCENT_DIM    = "#082f49"   # Very subtle accent bg

    # Status colors
    STATUS_ADDED    = "#4ade80"   # Added / success
    STATUS_MODIFIED = "#fbbf24"   # Modified / warning
    STATUS_DELETED  = "#f87171"   # Deleted / danger
    STATUS_RENAMED  = "#60a5fa"   # Renamed / info
    STATUS_UNTRACK  = "#a78bfa"   # Untracked

    STATUS_OK_BG    = "#0d2a1a"   # Success background
    STATUS_OK_BDR   = "#166534"   # Success border
    STATUS_ERR_BG   = "#2d1010"   # Error background
    STATUS_ERR_BDR  = "#7f1d1d"   # Error border
    STATUS_WARN_BG  = "#2a1d0a"   # Warning background
    STATUS_WARN_BDR = "#78350f"   # Warning border


# ── Typography ──────────────────────────────────────────────────────────────

class T:
    """Typography tokens."""

    FAMILY_SANS = "'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
    FAMILY_SANS_CSS = "\"SF Pro Display\", \"Helvetica Neue\", Arial, sans-serif"
    FAMILY_MONO = "'Menlo', 'Monaco', 'Fira Code', monospace"

    SIZE_XS   = "10px"
    SIZE_SM   = "11px"
    SIZE_BASE = "12px"
    SIZE_MD   = "13px"
    SIZE_LG   = "14px"
    SIZE_XL   = "15px"
    SIZE_2XL  = "17px"

    WEIGHT_NORMAL = "400"
    WEIGHT_MEDIUM = "500"
    WEIGHT_SEMI   = "600"
    WEIGHT_BOLD   = "700"


# ── Spacing ─────────────────────────────────────────────────────────────────

class S:
    """Spacing tokens (px)."""

    XS  = 4
    SM  = 6
    MD  = 8
    LG  = 12
    XL  = 16
    XXL = 24


# ── Component QSS Builders ──────────────────────────────────────────────────

class QSS:
    """Reusable QSS string builders for common components."""

    @staticmethod
    def button(
        bg: str = C.BG_RAISED,
        fg: str = C.TEXT_SECONDARY,
        border: str = C.BORDER_DEFAULT,
        bg_hover: str = C.BG_HOVER,
        fg_hover: str = C.ACCENT_LIGHT,
        border_hover: str = C.BORDER_STRONG,
        radius: int = 5,
        font_size: str = T.SIZE_BASE,
    ) -> str:
        return (
            f"QPushButton{{background:{bg};color:{fg};"
            f"border:1px solid {border};border-radius:{radius}px;"
            f"font-size:{font_size};padding:4px 10px;}}"
            f"QPushButton:hover{{background:{bg_hover};color:{fg_hover};"
            f"border-color:{border_hover};}}"
            f"QPushButton:disabled{{color:{C.TEXT_DISABLED};"
            f"border-color:{C.BORDER_SUBTLE};}}"
        )

    @staticmethod
    def button_primary(font_size: str = T.SIZE_BASE) -> str:
        return (
            f"QPushButton{{background:{C.ACCENT_DIM};color:{C.ACCENT_LIGHT};"
            f"border:1px solid {C.ACCENT};border-radius:5px;"
            f"font-size:{font_size};font-weight:{T.WEIGHT_SEMI};padding:4px 12px;}}"
            f"QPushButton:hover{{background:{C.ACCENT_SUBTLE};border-color:{C.ACCENT_HOVER};}}"
            f"QPushButton:disabled{{color:{C.TEXT_DISABLED};border-color:{C.BORDER_SUBTLE};}}"
        )

    @staticmethod
    def button_success(font_size: str = T.SIZE_BASE) -> str:
        return (
            f"QPushButton{{background:{C.STATUS_OK_BG};color:{C.STATUS_ADDED};"
            f"border:1px solid {C.STATUS_OK_BDR};border-radius:4px;"
            f"font-size:{font_size};font-weight:{T.WEIGHT_SEMI};padding:2px 14px;}}"
            f"QPushButton:hover{{background:#1a4535;}}"
            f"QPushButton:disabled{{color:#2d4a3a;border-color:{C.STATUS_OK_BG};}}"
        )

    @staticmethod
    def button_danger(font_size: str = T.SIZE_BASE) -> str:
        return (
            f"QPushButton{{background:{C.STATUS_ERR_BG};color:{C.STATUS_DELETED};"
            f"border:1px solid {C.STATUS_ERR_BDR};border-radius:4px;"
            f"font-size:{font_size};padding:2px 10px;}}"
            f"QPushButton:hover{{background:#3a1515;}}"
        )

    @staticmethod
    def toolbar() -> str:
        return (
            f"QToolBar{{background:{C.BG_DEEP};border-bottom:1px solid {C.BORDER_FAINT};"
            f"spacing:4px;padding:0 8px;}}"
        )

    @staticmethod
    def tabs() -> str:
        return (
            f"QTabWidget::pane{{border:none;background:{C.BG_BASE};}}"
            f"QTabBar::tab{{background:{C.BG_RAISED};color:{C.TEXT_MUTED};"
            f"padding:8px 20px;border:none;border-bottom:2px solid transparent;"
            f"font-size:11px;min-width:0px;}}"
            f"QTabBar::tab:selected{{background:{C.BG_ACTIVE};color:{C.ACCENT_LIGHT};"
            f"border-bottom:2px solid {C.ACCENT};}}"
            f"QTabBar::tab:hover:!selected{{background:{C.BG_HOVER};"
            f"color:{C.TEXT_SECONDARY};}}"
        )

    @staticmethod
    def list_widget() -> str:
        return (
            f"QListWidget{{background:{C.BG_BASE};outline:none;border:none;}}"
            f"QListWidget::item{{padding:5px 8px;color:{C.TEXT_SECONDARY};"
            f"font-size:{T.SIZE_SM};font-family:{T.FAMILY_MONO};"
            f"border-bottom:1px solid {C.BORDER_FAINT};}}"
            f"QListWidget::item:hover{{background:{C.BG_HOVER};color:{C.TEXT_PRIMARY};}}"
            f"QListWidget::item:selected{{background:{C.ACCENT_SUBTLE};"
            f"color:{C.ACCENT_LIGHT};}}"
        )

    @staticmethod
    def scrollbar() -> str:
        return (
            f"QScrollBar:vertical{{background:{C.BG_BASE};width:8px;margin:0;}}"
            f"QScrollBar::handle:vertical{{background:{C.BORDER_STRONG};"
            f"border-radius:4px;min-height:24px;}}"
            f"QScrollBar::handle:vertical:hover{{background:{C.ACCENT};}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}"
            f"QScrollBar:horizontal{{background:{C.BG_BASE};height:8px;margin:0;}}"
            f"QScrollBar::handle:horizontal{{background:{C.BORDER_STRONG};"
            f"border-radius:4px;min-width:24px;}}"
            f"QScrollBar::handle:horizontal:hover{{background:{C.ACCENT};}}"
            f"QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal{{width:0;}}"
        )

    @staticmethod
    def status_bar() -> str:
        return (
            f"QStatusBar{{background:{C.BG_DEEP};color:{C.TEXT_MUTED};"
            f"font-size:{T.SIZE_SM};border-top:1px solid {C.BORDER_FAINT};}}"
        )

    @staticmethod
    def context_menu() -> str:
        return (
            f"QMenu{{background:{C.BG_RAISED};color:{C.TEXT_PRIMARY};"
            f"border:1px solid {C.BORDER_STRONG};padding:4px 0;}}"
            f"QMenu::item{{padding:5px 20px;font-size:{T.SIZE_BASE};}}"
            f"QMenu::item:selected{{background:{C.ACCENT_SUBTLE};color:{C.ACCENT_LIGHT};}}"
            f"QMenu::separator{{height:1px;background:{C.BORDER_SUBTLE};margin:3px 0;}}"
        )

    @staticmethod
    def splitter() -> str:
        return f"QSplitter::handle{{background:{C.BORDER_SUBTLE};}}"

    @staticmethod
    def sidebar() -> str:
        return (
            f"QWidget#sidebar{{background:{C.BG_DEEP};}}"
        )

    @staticmethod
    def global_app() -> str:
        """앱 전체 기본 스타일 (QApplication.setStyleSheet에 사용)."""
        return (
            f"QMainWindow{{background:{C.BG_DEEP};}}"
            f"QWidget{{color:{C.TEXT_PRIMARY};}}"
            + QSS.scrollbar()
            + QSS.status_bar()
        )
