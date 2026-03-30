# Git Dashboard

macOS 전용 Git 워크플로우 GUI 대시보드.

터미널 없이 브랜치 상태 확인, 원클릭 동기화, Release/Hotfix 워크플로우를 관리합니다.

## 스택

- **Python 3.11+** / **PyQt6** / **GitPython**
- 4-Layer 아키텍처 (Infrastructure → Domain → Application → Presentation)
- Poetry 패키지 관리

## 빠른 시작

```bash
# 의존성 설치
pip install poetry
poetry install

# 실행
poetry run python main.py

# 테스트
poetry run pytest tests/ -v
```

## 프로젝트 구조

```
app/
├── infrastructure/   # GitRepository, ConfigStore, ScriptRunner
├── domain/          # BranchManager, PrChecker, ReleaseManager
├── controller/      # GitWorker (QThread), WorkflowController
└── ui/              # MainWindow, BranchPanel, CommitLogPanel, ...
```

## 개발 진행 상황

| Phase | 기능 | 상태 |
|-------|------|------|
| MVP W1 | F-01 브랜치 상태, F-02 동기화, F-03 커밋 로그, F-04 브랜치 목록 | 🚧 진행 중 |
| Phase 2 W2-3 | F-05 PR체커, F-06 Release, F-07 Hotfix, F-08 메뉴바 | ⏳ 예정 |
| Phase 3 W4 | F-09 다중저장소, F-10 Hook 시각화, F-11 알림, F-12 패키징 | ⏳ 예정 |

## 설계 문서

- [`git-dashboard-design.md`](./git-dashboard-design.md) — 전체 설계
- [`docs/plan/git-dashboard-plan.md`](./docs/plan/git-dashboard-plan.md) — 상세 개발 계획
- [`docs/plan/git-dashboard-visual-plan.md`](./docs/plan/git-dashboard-visual-plan.md) — Mermaid 다이어그램
- [`docs/plan/git-dashboard-plan.html`](./docs/plan/git-dashboard-plan.html) — HTML 시각화 대시보드
