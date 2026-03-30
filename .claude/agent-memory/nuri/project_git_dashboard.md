---
name: git-dashboard project context
description: macOS Git Workflow GUI Dashboard -- PyQt6 + QSystemTrayIcon, 4-Layer Architecture, 4-week PDCA plan with 12 features (F-01~F-12)
type: project
---

Git Dashboard is a macOS-only desktop app wrapping existing shell scripts (branch_sync, pr_checker, release_helper, hotfix_workflow) into a PyQt6 GUI.

**Key Technical Decisions (2026-03-30)**:
- QSystemTrayIcon chosen over rumps for menu bar (event loop conflict avoidance)
- 4-Layer: Infrastructure -> Domain -> Application -> Presentation
- GitPython + subprocess hybrid (pure Python + shell script wrapping)
- Poetry for dependency management, PyInstaller for .app packaging

**Why:** User manages multiple AWS CodeCommit repos (aipd, community, citeasy) with develop -> release/* -> main branching strategy. Needs visual dashboard to reduce terminal context-switching.

**How to apply:** Implementation follows bottom-up order (Infrastructure first). Domain layer must be pure Python (no PyQt6 imports). All Git operations go through QThread to prevent UI blocking.

**Schedule**: MVP (W1, F-01~F-04) -> Workflow (W2-3, F-05~F-08) -> Polish+Package (W4, F-09~F-12)

**Plan doc**: `docs/plan/git-dashboard-plan.md`
**Design doc**: `git-dashboard-design.md`
