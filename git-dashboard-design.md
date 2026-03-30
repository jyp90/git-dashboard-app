# Git Workflow GUI Dashboard
## 설계 문서 v1.0

> macOS 전용 개인 개발 생산성 도구  
> Python 3.11+ / PyQt6 / rumps  
> 작성일: 2026-03-30

---

## 1. 프로젝트 개요

### 1.1 목적
기존 Git 자동화 쉘 스크립트(branch sync, PR checker, release helper, hotfix workflow 등)를
PyQt6 기반 GUI 앱으로 래핑하여, 터미널 없이 시각적으로 Git 워크플로우를 관리한다.

### 1.2 타겟 환경
| 항목 | 내용 |
|------|------|
| OS | macOS 13 Ventura 이상 |
| Git 호스팅 | AWS CodeCommit |
| 브랜치 전략 | `develop → release/* → main` |
| 빌드 도구 | Gradle (Java/Spring Boot 프로젝트) |
| 배포 형태 | `.app` 패키지 (PyInstaller) + 메뉴바 상주 |

### 1.3 핵심 가치
- **터미널 없이** 반복 워크플로우를 원클릭으로 처리
- **브랜치 상태를 한눈에** 시각화
- 기존 쉘 스크립트를 **재작성 없이 래핑**하여 점진적 마이그레이션

---

## 2. 기능 명세

### 2.1 MVP (1주차 목표)
| ID | 기능 | 설명 |
|----|------|------|
| F-01 | 브랜치 상태 패널 | 현재 브랜치, 로컬/리모트 커밋 diff, dirty 상태 표시 |
| F-02 | 원클릭 브랜치 동기화 | `develop` ← origin 동기화 (기존 branch-sync 스크립트 래핑) |
| F-03 | 커밋 로그 뷰어 | 최근 20개 커밋 리스트 (hash, message, author, date) |
| F-04 | 브랜치 목록 | 로컬/리모트 브랜치 트리 표시 |

### 2.2 Phase 2 (2~3주차 목표)
| ID | 기능 | 설명 |
|----|------|------|
| F-05 | PR 품질 체커 | 커밋 컨벤션, 파일 변경 수, TODO 잔존 여부 검사 |
| F-06 | Release 워크플로우 | `release/*` 브랜치 생성 → 버전 태깅 → main 머지 가이드 |
| F-07 | Hotfix 워크플로우 | `hotfix/*` 브랜치 생성 → 패치 → develop/main 반영 |
| F-08 | 메뉴바 상주 | macOS 상단 메뉴바에 아이콘 상주, 핵심 액션 바로 접근 |

### 2.3 Phase 3 (4주차 목표)
| ID | 기능 | 설명 |
|----|------|------|
| F-09 | 다중 저장소 관리 | 여러 프로젝트(aipd, community, citeasy 등) 탭 전환 |
| F-10 | Pre-push Hook 시각화 | 훅 실행 결과를 UI에서 확인 |
| F-11 | 알림 | 브랜치 뒤처짐, 머지 충돌 가능성 macOS 알림 |
| F-12 | .app 패키징 | PyInstaller 기반 배포 빌드 |

---

## 3. 기술 스택

```
git-dashboard/
│
├── Runtime
│   ├── Python 3.11+
│   ├── PyQt6            # 메인 GUI 프레임워크
│   └── rumps            # macOS 메뉴바 상주
│
├── Git 연동
│   ├── GitPython        # Git 객체 조작 (순수 Python)
│   └── subprocess       # 기존 쉘 스크립트 래핑
│
├── 패키징
│   └── PyInstaller      # .app 빌드
│
└── 개발 도구
    ├── pytest           # 유닛 테스트
    ├── black            # 코드 포매터
    └── pyproject.toml   # 의존성 관리 (Poetry or pip)
```

### 3.1 PyQt6 vs 대안 선택 이유
| 항목 | PyQt6 | Tkinter | Electron |
|------|-------|---------|----------|
| macOS 네이티브 룩앤필 | ✅ 우수 | ❌ 구식 | △ 가능 |
| 학습 비용 | 중간 | 낮음 | 높음 |
| 패키징 용이성 | ✅ | ✅ | △ 무거움 |
| 커스텀 위젯 | ✅ 풍부 | ❌ 제한 | ✅ |

---

## 4. 아키텍처

### 4.1 레이어 구조
```
┌─────────────────────────────────────────┐
│              Presentation Layer          │
│   (PyQt6 Widgets / rumps MenuBar)        │
├─────────────────────────────────────────┤
│              Application Layer           │
│   (WorkflowController / EventHandler)    │
├─────────────────────────────────────────┤
│               Domain Layer               │
│   (BranchManager / CommitAnalyzer /      │
│    PrChecker / ReleaseManager)           │
├─────────────────────────────────────────┤
│            Infrastructure Layer          │
│   (GitRepository / ScriptRunner /        │
│    ConfigStore)                          │
└─────────────────────────────────────────┘
```

### 4.2 핵심 설계 원칙
- **파일 = 클래스** 원칙: 1 파일 1 클래스, 단일 책임
- **Script Runner 패턴**: 기존 쉘 스크립트는 재작성 없이 subprocess로 래핑
- **Signal/Slot**: PyQt6 시그널로 레이어 간 의존성 역전
- **Worker Thread**: Git 작업은 QThread로 분리 → UI 블로킹 방지

---

## 5. 파일 구조

```
git-dashboard/
├── main.py                          # 앱 진입점
├── pyproject.toml
├── README.md
│
├── app/
│   ├── __init__.py
│   │
│   ├── ui/                          # Presentation Layer
│   │   ├── main_window.py           # MainWindow (QMainWindow)
│   │   ├── branch_panel.py          # BranchStatusPanel (QWidget)
│   │   ├── commit_log_panel.py      # CommitLogPanel (QWidget)
│   │   ├── workflow_panel.py        # WorkflowPanel (QWidget)
│   │   ├── pr_check_panel.py        # PrCheckPanel (QWidget)
│   │   └── menu_bar_app.py          # MenuBarApp (rumps.App)
│   │
│   ├── controller/                  # Application Layer
│   │   ├── workflow_controller.py   # WorkflowController
│   │   └── git_worker.py            # GitWorker (QThread)
│   │
│   ├── domain/                      # Domain Layer
│   │   ├── branch_manager.py        # BranchManager
│   │   ├── commit_analyzer.py       # CommitAnalyzer
│   │   ├── pr_checker.py            # PrChecker
│   │   └── release_manager.py       # ReleaseManager
│   │
│   └── infrastructure/              # Infrastructure Layer
│       ├── git_repository.py        # GitRepository (GitPython 래핑)
│       ├── script_runner.py         # ScriptRunner (subprocess 래핑)
│       └── config_store.py          # ConfigStore (JSON 설정 저장)
│
├── scripts/                         # 기존 쉘 스크립트 (변경 없이 유지)
│   ├── branch_sync.sh
│   ├── pr_checker.sh
│   ├── release_helper.sh
│   └── hotfix_workflow.sh
│
├── resources/
│   ├── icons/
│   │   └── menu_icon.png
│   └── styles/
│       └── dark_theme.qss
│
└── tests/
    ├── test_branch_manager.py
    ├── test_commit_analyzer.py
    └── test_pr_checker.py
```

---

## 6. 주요 클래스 명세

### 6.1 Infrastructure Layer

#### `GitRepository` (git_repository.py)
```python
class GitRepository:
    """GitPython 기반 저장소 접근 추상화"""

    def __init__(self, repo_path: str): ...
    def get_current_branch(self) -> str: ...
    def get_branches(self, remote: bool = False) -> list[str]: ...
    def get_commit_log(self, limit: int = 20) -> list[Commit]: ...
    def get_status(self) -> RepoStatus: ...
    def get_ahead_behind(self, branch: str) -> tuple[int, int]: ...
```

#### `ScriptRunner` (script_runner.py)
```python
class ScriptRunner:
    """기존 쉘 스크립트 subprocess 래핑"""

    def run(self, script_name: str, args: list[str] = []) -> ScriptResult: ...
    def run_async(self, script_name: str, callback: Callable) -> None: ...
```

#### `ConfigStore` (config_store.py)
```python
class ConfigStore:
    """~/.git-dashboard/config.json 관리"""

    def get_repositories(self) -> list[RepoConfig]: ...
    def add_repository(self, path: str, name: str) -> None: ...
    def get_active_repo(self) -> RepoConfig: ...
```

### 6.2 Domain Layer

#### `BranchManager` (branch_manager.py)
```python
class BranchManager:
    """브랜치 상태 분석 및 동기화 로직"""

    def get_branch_summary(self) -> BranchSummary: ...
    def sync_develop(self) -> SyncResult: ...
    def create_release_branch(self, version: str) -> BranchResult: ...
    def create_hotfix_branch(self, issue_id: str) -> BranchResult: ...
```

#### `PrChecker` (pr_checker.py)
```python
class PrChecker:
    """PR 품질 검사 (커밋 컨벤션, 변경 규모, TODO 잔존 등)"""

    def check(self, base: str, head: str) -> PrCheckReport: ...
    def check_commit_convention(self) -> list[CheckItem]: ...
    def check_file_changes(self, threshold: int = 20) -> CheckItem: ...
    def check_todo_comments(self) -> list[CheckItem]: ...
```

### 6.3 Application Layer

#### `GitWorker` (git_worker.py)
```python
class GitWorker(QThread):
    """Git 작업을 별도 스레드에서 실행 → UI 블로킹 방지"""

    result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, task: Callable): ...
    def run(self) -> None: ...
```

### 6.4 Presentation Layer

#### `MainWindow` (main_window.py)
```python
class MainWindow(QMainWindow):
    """탭 기반 메인 윈도우 (브랜치 / 커밋 / 워크플로우 / PR 체크)"""
```

---

## 7. UI 레이아웃

```
┌─────────────────────────────────────────────────────┐
│  🌿 Git Dashboard          [저장소: aipd ▾]  [⚙]   │
├─────────┬───────────────────────────────────────────┤
│ Branch  │  현재 브랜치: feature/ai-reader-fix         │
│ Commit  │  ↑2 ↓0  (origin/develop 대비)              │
│ PR Check│  ─────────────────────────────────────     │
│ Release │  LOCAL BRANCHES          REMOTE BRANCHES   │
│ Hotfix  │  * feature/ai-reader-fix  origin/develop   │
│         │    develop                origin/main      │
│         │    main                   origin/release.. │
│         │  ─────────────────────────────────────     │
│         │  [⟳ Sync Develop]  [🔍 Check PR]          │
└─────────┴───────────────────────────────────────────┘
```

**메뉴바 상주 (rumps)**
```
메뉴바 아이콘 클릭
├── 🌿 현재 브랜치: feature/ai-reader-fix
├── ─────────────
├── ⟳ Sync Develop
├── 🔍 Check PR
├── 🚀 Start Release...
├── 🔥 Start Hotfix...
├── ─────────────
└── 창 열기 / 종료
```

---

## 8. 데이터 모델

```python
# 주요 도메인 객체 (dataclass)

@dataclass
class BranchSummary:
    current: str
    ahead: int
    behind: int
    is_dirty: bool
    local_branches: list[str]
    remote_branches: list[str]

@dataclass
class Commit:
    hash: str
    short_hash: str
    message: str
    author: str
    date: datetime

@dataclass
class PrCheckReport:
    passed: bool
    items: list[CheckItem]
    summary: str

@dataclass
class CheckItem:
    category: str        # "convention" | "size" | "todo"
    passed: bool
    message: str

@dataclass
class ScriptResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int
```

---

## 9. 개발 일정

### Week 1: MVP
| 일차 | 작업 |
|------|------|
| 1일 | 프로젝트 세팅, pyproject.toml, 폴더 구조 생성 |
| 2일 | GitRepository, ConfigStore 구현 + 유닛 테스트 |
| 3일 | BranchManager 구현 |
| 4일 | MainWindow + BranchPanel UI 구현 |
| 5일 | GitWorker (QThread) 연결, 실제 저장소로 동작 확인 |

### Week 2: 워크플로우
| 일차 | 작업 |
|------|------|
| 6~7일 | ScriptRunner로 기존 스크립트 래핑 |
| 8~9일 | CommitLogPanel, WorkflowPanel UI |
| 10일 | Release / Hotfix 워크플로우 UI 연결 |

### Week 3: 품질 + 메뉴바
| 일차 | 작업 |
|------|------|
| 11~12일 | PrChecker 구현 + PrCheckPanel UI |
| 13일 | rumps 메뉴바 상주 앱 구현 |
| 14~15일 | 다크 테마 QSS 적용, UI 다듬기 |

### Week 4: 완성
| 일차 | 작업 |
|------|------|
| 16~17일 | 다중 저장소 탭 전환 |
| 18~19일 | macOS 알림, Pre-push Hook 시각화 |
| 20일 | PyInstaller 패키징, 테스트, 문서화 |

---

## 10. 비기능 요구사항

| 항목 | 목표 |
|------|------|
| UI 응답성 | Git 작업 중에도 UI 블로킹 없음 (QThread 필수) |
| 초기 로딩 | 3초 이내 메인 윈도우 표시 |
| 안정성 | Git 명령 실패 시 에러 메시지 표시, 앱 크래시 없음 |
| 설정 유지 | 앱 재시작 후 저장소 경로, 테마 설정 유지 |
| 패키지 크기 | .app 번들 100MB 이하 |

---

## 11. 리스크 & 대응

| 리스크 | 가능성 | 대응 |
|--------|--------|------|
| rumps + PyQt6 동시 실행 충돌 (각자 다른 이벤트 루프) | 높음 | 메뉴바는 별도 프로세스로 분리하거나 PyQt6 SystemTray로 대체 |
| AWS CodeCommit 인증 (HTTPS/SSH) | 중간 | 로컬 git credential 그대로 활용, 앱에서 별도 인증 불필요 |
| PyInstaller macOS 패키징 오류 | 중간 | 초기부터 CI 빌드 테스트, 가상환경 격리 |
| 기존 쉘 스크립트 경로 의존성 | 낮음 | ConfigStore에서 스크립트 경로 설정 가능하도록 |

---

*다음 단계: 프로젝트 초기 세팅 및 Week 1 Day 1 작업 시작*
