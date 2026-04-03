# -*- mode: python ; coding: utf-8 -*-
# git_dashboard.spec — PyInstaller 빌드 스펙 (F-12)
# Usage: pyinstaller git_dashboard.spec

import sys
from pathlib import Path

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # QSS 스타일 시트
        (str(ROOT / "resources" / "styles" / "dark_theme.qss"),
         "resources/styles"),
        # icons 폴더 (현재 비어있어도 포함)
        (str(ROOT / "resources" / "icons"),
         "resources/icons"),
    ],
    hiddenimports=[
        # PyQt6 플러그인
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.sip",
        # GitPython 내부 모듈
        "git",
        "git.repo",
        "git.remote",
        "git.index",
        "git.objects",
        # 앱 도메인 모듈
        "app.domain.models",
        "app.domain.branch_manager",
        "app.domain.pr_checker",
        "app.infrastructure.git_repository",
        "app.infrastructure.config_store",
        "app.infrastructure.script_runner",
        "app.controller.git_worker",
        "app.controller.workflow_controller",
        "app.controller.diff_controller",
        "app.controller.merge_controller",
        "app.controller.rebase_controller",
        "app.domain.commit_graph_builder",
        "app.domain.conflict_resolver",
        "app.domain.diff_parser",
        "app.domain.rebase_orchestrator",
        "app.domain.stash_manager",
        "app.infrastructure.keychain_service",
        "app.infrastructure.ide_integration_service",
        "app.infrastructure.file_watcher_service",
        "app.ui.commit_graph_view",
        "app.ui.commit_panel",
        "app.ui.design_system",
        "app.ui.diff_viewer",
        "app.ui.graph_renderer",
        "app.ui.ide_panel",
        "app.ui.keychain_settings",
        "app.ui.merge_editor",
        "app.ui.rebase_dialog",
        "app.ui.stash_panel",
        "app.ui.syntax_highlighter",
        "app.ui.worktree_panel",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "black",
        "pytest_cov",
        "tkinter",
        "unittest",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Git Dashboard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,       # macOS: 터미널 창 숨김
    disable_windowed_traceback=False,
    argv_emulation=True, # macOS: 드래그앤드롭 파일 열기 지원
    target_arch=None,    # 현재 아키텍처 (arm64/x86_64)
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Git Dashboard",
)

app = BUNDLE(
    coll,
    name="Git Dashboard.app",
    icon=None,           # resources/icons/menu_icon.icns 준비 시 교체
    bundle_identifier="com.jypark.git-dashboard",
    version="2.1.0",
    info_plist={
        "CFBundleName": "Git Dashboard",
        "CFBundleDisplayName": "Git Dashboard",
        "CFBundleVersion": "2.1.0",
        "CFBundleShortVersionString": "2.1.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,  # 다크모드 지원
        "LSMinimumSystemVersion": "13.0",
        "NSHumanReadableCopyright": "© 2026 jypark",
    },
)
