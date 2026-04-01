# Git Dashboard v2.0

macOS 전용 Git 워크플로우 GUI 대시보드 — SourceTree 수준의 Stage/Commit/Push 워크플로우와 커밋 그래프 시각화를 제공합니다.

## 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python 3.11+ |
| GUI 프레임워크 | PyQt6 6.6+ |
| Git 라이브러리 | GitPython 3.1+ |
| 패키지 관리 | Poetry |
| 배포 | PyInstaller → `.app` → DMG |
| 대상 OS | macOS 13 Ventura 이상 |
| 아키텍처 | 4-Layer (Infrastructure → Domain → Application → Presentation) |
| Design System | 중앙 집중식 색상·타이포·컴포넌트 토큰 (`app/ui/design_system.py`) |

## 기능

### v2.0 — 커밋 워크플로우 · 시각화

| 기능 | 설명 |
|------|------|
| **Commit Workflow** | Staged/Unstaged 파일 목록, 파일별 diff 미리보기, Stage/Unstage, Commit, Amend |
| **Push / Pull / Fetch** | 툴바 원클릭 git push/pull/fetch, 비동기 처리 |
| **Branch Checkout** | 브랜치 목록 더블클릭으로 즉시 checkout |
| **Discard Changes** | Unstaged 파일 우클릭 → 변경사항 되돌리기 |
| **커밋 그래프** | DAG 토폴로지 기반 브랜치 히스토리 시각화 |
| **Diff Viewer** | Inline / Side-by-Side 모드, 라인 번호, 구문 강조 |
| **Stash 관리** | stash push/pop/apply/drop, diff 미리보기 |
| **Worktree** | git worktree 목록 조회 및 관리 |
| **Interactive Rebase** | 커밋 순서 변경, squash, fixup UI |
| **Merge Conflict** | 3-way merge 에디터 |
| **Design System** | 하늘색(sky blue) 액센트, 5단계 배경 계층, 다크 테마 |

### v1.0 — 대시보드 · 기본 기능

| 기능 | 설명 |
|------|------|
| 브랜치 상태 시각화 | 현재 브랜치, ahead/behind, dirty 상태 실시간 표시 |
| 원클릭 동기화 | origin/develop fetch → pull 원클릭 처리 |
| 커밋 로그 | 최근 커밋 목록 (hash, 메시지, 작성자, 날짜) |
| PR 품질 체크 | 커밋 컨벤션, 변경 파일 수, TODO 잔존 검사 |
| Release 워크플로우 | `release/*` 브랜치 자동 생성 |
| Hotfix 워크플로우 | `hotfix/*` 브랜치 자동 생성 |
| 다중 저장소 관리 | 사이드바에서 여러 프로젝트 전환 |
| Pre-push Hook 시각화 | `.git/hooks/pre-push` 실행 결과 확인 |
| macOS 알림 | 브랜치 뒤처짐·충돌 위험 시 시스템 알림 |
| 메뉴바 상주 | 시스템 트레이 아이콘으로 상태 표시 |

## 설치

### DMG (권장)

1. [GitDashboard-0.1.0.dmg](./dist/GitDashboard-0.1.0.dmg) 다운로드
2. DMG 마운트 후 `Git Dashboard.app`을 `Applications` 폴더로 드래그

### 소스 실행

```bash
pip install poetry
poetry install
poetry run python main.py
```

## 빌드

```bash
make build   # dist/Git Dashboard.app 생성
make dmg     # dist/GitDashboard-0.1.0.dmg 생성
```

## 개발

```bash
make run     # 개발 모드 실행
make test    # 테스트 실행
make clean   # 빌드 산출물 정리
```

## 프로젝트 구조

```
git-dashboard-app/
├── main.py                        # 진입점
├── pyproject.toml                 # Poetry 의존성
├── resources/styles/dark_theme.qss
├── app/
│   ├── ui/                        # Presentation Layer
│   │   ├── design_system.py       # Design Token (C, T, S, QSS)
│   │   ├── main_window.py         # MainWindow + 탭 레이아웃
│   │   ├── dashboard_panel.py     # 개요 대시보드
│   │   ├── commit_panel.py        # Stage/Unstage/Commit UI
│   │   ├── diff_viewer.py         # Diff 뷰어 (Inline/Side-by-Side)
│   │   ├── commit_graph_view.py   # 커밋 그래프 뷰
│   │   ├── graph_renderer.py      # QPainter 렌더링 엔진
│   │   ├── stash_panel.py         # Stash 관리
│   │   ├── worktree_panel.py      # Worktree 관리
│   │   ├── rebase_dialog.py       # Interactive Rebase
│   │   ├── merge_editor.py        # 3-way Merge 에디터
│   │   ├── keychain_settings.py   # macOS Keychain 설정
│   │   └── ide_panel.py           # IntelliJ IDE 연동
│   ├── controller/                # Application Layer
│   │   ├── workflow_controller.py
│   │   └── git_worker.py          # QThread 비동기 git 작업
│   ├── domain/                    # Domain Layer
│   │   ├── models.py
│   │   ├── commit_graph_builder.py
│   │   ├── diff_parser.py
│   │   ├── stash_manager.py
│   │   ├── rebase_orchestrator.py
│   │   └── conflict_resolver.py
│   └── infrastructure/            # Infrastructure Layer
│       ├── git_repository.py      # GitPython 래핑
│       ├── config_store.py
│       ├── keychain_service.py
│       └── ide_integration_service.py
├── docs/
│   ├── 01-plan/                   # 기능 계획 문서
│   ├── 02-design/                 # 설계 문서
│   └── 03-analysis/               # Gap 분석 결과
└── tests/
```

## 요구 사항

- macOS 13 Ventura 이상
- Python 3.11+
- Git 설치
- AWS CodeCommit 등 Git 호스팅 인증 설정 완료

## 설계 문서

- [`git-dashboard-design.md`](./git-dashboard-design.md) — v1.0 전체 설계
- [`git-dashboard-design-v2.md`](./git-dashboard-design-v2.md) — v2.0 설계
