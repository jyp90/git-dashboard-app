# Git Dashboard Planning Document

> **Summary**: macOS Git Workflow GUI Dashboard - PyQt6 + QSystemTrayIcon 기반 개인 개발 생산성 도구
>
> **Project**: git-dashboard
> **Author**: jypark
> **Date**: 2026-03-30
> **Status**: Detailed
> **Design Reference**: `git-dashboard-design.md` v1.0

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 반복적인 Git 워크플로우(branch sync, PR check, release, hotfix)를 매번 터미널에서 수동 실행해야 하며, 브랜치 상태를 한눈에 파악하기 어렵다 |
| **Solution** | PyQt6 기반 4-Layer 아키텍처 GUI 앱 + macOS 메뉴바 상주로 원클릭 Git 워크플로우 제공. 기존 쉘 스크립트는 ScriptRunner 패턴으로 재작성 없이 래핑 |
| **Function/UX Effect** | 브랜치 상태 실시간 시각화, 원클릭 동기화/릴리스/핫픽스, 메뉴바에서 즉시 접근. QThread로 UI 블로킹 없는 반응형 UX |
| **Core Value** | 개인 개발자의 Git 반복 작업 시간 50% 이상 절감, 터미널 컨텍스트 스위칭 제거 |

---

## 1. Overview

### 1.1 Purpose

기존 Git 자동화 쉘 스크립트(branch_sync.sh, pr_checker.sh, release_helper.sh, hotfix_workflow.sh)를 PyQt6 기반 GUI 앱으로 래핑하여, 터미널 없이 시각적으로 Git 워크플로우를 관리한다.

### 1.2 Background

- AWS CodeCommit 기반 프로젝트(aipd, community, citeasy 등)를 관리하며, 반복적인 `develop -> release/* -> main` 워크플로우가 빈번
- 이미 쉘 스크립트로 자동화되어 있으나 터미널 진입/경로 이동/실행이 번거로움
- 브랜치 상태(ahead/behind, dirty files)를 한눈에 파악할 시각적 도구 필요
- macOS 전용이므로 네이티브 룩앤필 + 메뉴바 상주가 가능

### 1.3 Related Documents

- Design: `git-dashboard-design.md` v1.0
- Project Context: `CLAUDE.md`

---

## 2. Scope

### 2.1 In Scope

- [x] F-01: 브랜치 상태 패널 (현재 브랜치, ahead/behind, dirty)
- [x] F-02: 원클릭 브랜치 동기화 (develop <- origin)
- [x] F-03: 커밋 로그 뷰어 (최근 20개)
- [x] F-04: 로컬/리모트 브랜치 목록
- [x] F-05: PR 품질 체커
- [x] F-06: Release 워크플로우
- [x] F-07: Hotfix 워크플로우
- [x] F-08: macOS 메뉴바 상주
- [x] F-09: 다중 저장소 관리
- [x] F-10: Pre-push Hook 시각화
- [x] F-11: macOS 알림
- [x] F-12: .app 패키징

### 2.2 Out of Scope

- Windows/Linux 지원
- 원격 CI/CD 통합 (AWS CodePipeline 등)
- 코드 에디터 통합 (VS Code extension)
- Git 서버 인증 관리 (로컬 credential 사용)
- Merge conflict 해결 UI

---

## 3. Feature Decomposition (F-01 ~ F-12)

### 3.1 Functional Requirements

| ID | Feature | Priority | Phase | Complexity | Status |
|----|---------|----------|-------|------------|--------|
| F-01 | 브랜치 상태 패널 | **Critical** | MVP (W1) | Medium | Pending |
| F-02 | 원클릭 브랜치 동기화 | **Critical** | MVP (W1) | Low | Pending |
| F-03 | 커밋 로그 뷰어 | **High** | MVP (W1) | Low | Pending |
| F-04 | 브랜치 목록 | **High** | MVP (W1) | Low | Pending |
| F-05 | PR 품질 체커 | **High** | Phase 2 (W2-3) | High | Pending |
| F-06 | Release 워크플로우 | **High** | Phase 2 (W2-3) | High | Pending |
| F-07 | Hotfix 워크플로우 | **Medium** | Phase 2 (W2-3) | Medium | Pending |
| F-08 | 메뉴바 상주 | **High** | Phase 2 (W2-3) | High | Pending |
| F-09 | 다중 저장소 관리 | **Medium** | Phase 3 (W4) | Medium | Pending |
| F-10 | Pre-push Hook 시각화 | **Low** | Phase 3 (W4) | Medium | Pending |
| F-11 | macOS 알림 | **Low** | Phase 3 (W4) | Low | Pending |
| F-12 | .app 패키징 | **High** | Phase 3 (W4) | High | Pending |

### 3.2 Feature Detail Cards

#### F-01: 브랜치 상태 패널
- **Input**: GitRepository.get_current_branch(), get_status(), get_ahead_behind()
- **Output**: BranchStatusPanel(QWidget) - 현재 브랜치명, ahead/behind 카운트, dirty 상태 badge
- **Dependencies**: GitRepository, BranchManager
- **Layer**: Presentation(BranchPanel) <- Domain(BranchManager) <- Infrastructure(GitRepository)

#### F-02: 원클릭 브랜치 동기화
- **Input**: 사용자 "Sync Develop" 버튼 클릭
- **Output**: develop <- origin/develop fetch & merge, 결과 표시
- **Dependencies**: BranchManager.sync_develop(), ScriptRunner(branch_sync.sh)
- **Key Constraint**: QThread 필수 (UI 블로킹 방지)

#### F-03: 커밋 로그 뷰어
- **Input**: GitRepository.get_commit_log(limit=20)
- **Output**: CommitLogPanel(QWidget) - hash, message, author, date 테이블
- **Dependencies**: GitRepository, CommitAnalyzer

#### F-04: 브랜치 목록
- **Input**: GitRepository.get_branches(remote=True/False)
- **Output**: BranchPanel 내 로컬/리모트 브랜치 트리뷰
- **Dependencies**: GitRepository

#### F-05: PR 품질 체커
- **Input**: base branch, head branch 지정
- **Output**: PrCheckReport (convention 준수, 파일 변경 수, TODO 잔존)
- **Dependencies**: PrChecker, ScriptRunner(pr_checker.sh)
- **Complexity Note**: 커밋 메시지 파싱 + 파일 diff 분석 필요

#### F-06: Release 워크플로우
- **Input**: 버전 번호 입력
- **Output**: release/* 브랜치 생성 -> 버전 태깅 -> main 머지 가이드
- **Dependencies**: ReleaseManager, ScriptRunner(release_helper.sh)
- **Complexity Note**: 멀티스텝 위저드 UI + 롤백 지원

#### F-07: Hotfix 워크플로우
- **Input**: issue ID 입력
- **Output**: hotfix/* 브랜치 생성 -> 패치 -> develop/main 반영
- **Dependencies**: ReleaseManager, ScriptRunner(hotfix_workflow.sh)

#### F-08: 메뉴바 상주
- **Input**: 없음 (앱 시작 시 자동 상주)
- **Output**: macOS 상단 메뉴바 아이콘 + 드롭다운 메뉴
- **Dependencies**: PyQt6.QSystemTrayIcon
- **Complexity Note**: 이벤트 루프 충돌 해결 (QSystemTrayIcon 우선 채택)

#### F-09: 다중 저장소 관리
- **Input**: ConfigStore.get_repositories()
- **Output**: 탭 전환 UI (aipd, community, citeasy 등)
- **Dependencies**: ConfigStore, MainWindow 탭 구조

#### F-10: Pre-push Hook 시각화
- **Input**: Git pre-push hook 실행 결과
- **Output**: 훅 실행 로그를 UI에서 확인
- **Dependencies**: ScriptRunner, Git hook 설정

#### F-11: macOS 알림
- **Input**: 폴링 또는 이벤트 감지 (브랜치 뒤처짐, 머지 충돌 가능성)
- **Output**: macOS 네이티브 알림
- **Dependencies**: pyobjc 또는 osascript 래핑

#### F-12: .app 패키징
- **Input**: 전체 소스 + 의존성
- **Output**: 독립 실행 .app 번들 (100MB 이하)
- **Dependencies**: PyInstaller, 가상환경 격리

### 3.3 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| **UI 응답성** | Git 작업 중에도 UI 블로킹 없음 | QThread 분리 확인, 수동 UX 테스트 |
| **초기 로딩** | 3초 이내 메인 윈도우 표시 | time measurement (launch -> window shown) |
| **안정성** | Git 명령 실패 시 에러 표시, 앱 크래시 없음 | 에러 주입 테스트 |
| **설정 유지** | 재시작 후 저장소 경로, 테마 설정 유지 | ConfigStore 영속성 검증 |
| **패키지 크기** | .app 번들 100MB 이하 | PyInstaller 빌드 후 측정 |

---

## 4. Technical Decisions

### 4.1 Project Level Selection

| Level | Characteristics | Selected |
|-------|-----------------|:--------:|
| **Starter** | 단순 구조 | -- |
| **Dynamic** | Feature 모듈 기반 | -- |
| **Enterprise** | 엄격한 레이어 분리, DI | -- |
| **Custom (4-Layer Desktop)** | Presentation/Application/Domain/Infrastructure | **Selected** |

> 선택 근거: 웹 서비스가 아닌 데스크톱 앱이므로 Enterprise MSA 패턴은 불필요하나, 설계 문서에 4-Layer 아키텍처가 명시되어 있으므로 Clean Architecture 원칙을 따르되 데스크톱 앱에 맞게 적용

### 4.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| GUI Framework | PyQt6 / Tkinter / Electron | **PyQt6** | macOS 네이티브 룩앤필, 풍부한 위젯, QThread 지원 |
| 메뉴바 상주 | rumps / QSystemTrayIcon | **QSystemTrayIcon (1차), rumps (fallback)** | 아래 상세 분석 참조 |
| Git 라이브러리 | GitPython / pygit2 / subprocess | **GitPython + subprocess** | GitPython으로 객체 조작, 기존 스크립트는 subprocess 래핑 |
| 패키지 관리 | Poetry / pip / pipenv | **Poetry** | pyproject.toml 표준, lock 파일, 가상환경 관리 |
| 패키징 | PyInstaller / py2app / Nuitka | **PyInstaller** | macOS .app 빌드 검증 사례 풍부 |
| 테스트 | pytest / unittest | **pytest** | 간결한 문법, fixture 지원, 풍부한 플러그인 |
| 포매터 | black / ruff / autopep8 | **black** | zero-config, 일관된 스타일 |
| 쓰레딩 | QThread / threading / asyncio | **QThread** | PyQt6 시그널/슬롯과 자연스러운 통합 |

### 4.3 rumps vs QSystemTrayIcon 상세 분석

| 항목 | rumps | QSystemTrayIcon |
|------|-------|-----------------|
| 이벤트 루프 | NSRunLoop (별도) | Qt 이벤트 루프 (통합) |
| PyQt6 공존 | **충돌 가능** (별도 프로세스 필요) | **자연스러운 통합** |
| 기능 범위 | 메뉴바 전용, 네이티브 | 시스템 트레이, 크로스플랫폼 |
| macOS 메뉴 | 완전한 네이티브 메뉴 | 기본 QMenu |
| 구현 복잡도 | 별도 프로세스 IPC 필요 | PyQt6 앱 내 직접 통합 |

**결정**: QSystemTrayIcon을 1차 방안으로 채택
- PyQt6와 동일한 이벤트 루프에서 동작하므로 충돌 없음
- rumps 수준의 네이티브 메뉴가 필요할 경우 Phase 2에서 rumps를 별도 프로세스로 분리 검토
- 리스크 완화: Week 2 시작 시 QSystemTrayIcon 프로토타입을 먼저 구현하여 macOS에서의 UX 검증

### 4.4 Clean Architecture Approach (4-Layer)

```
git-dashboard/
├── main.py                          # 진입점: QApplication + MainWindow 초기화
│
├── app/
│   ├── __init__.py
│   │
│   ├── infrastructure/              # Layer 1: 외부 시스템 접근
│   │   ├── git_repository.py        #   GitPython 래핑
│   │   ├── script_runner.py         #   subprocess 래핑
│   │   └── config_store.py          #   JSON 설정 파일 관리
│   │
│   ├── domain/                      # Layer 2: 비즈니스 로직 (순수 Python)
│   │   ├── models.py                #   dataclass 모음 (BranchSummary, Commit 등)
│   │   ├── branch_manager.py        #   브랜치 상태/동기화 로직
│   │   ├── commit_analyzer.py       #   커밋 분석
│   │   ├── pr_checker.py            #   PR 품질 검사
│   │   └── release_manager.py       #   릴리스/핫픽스 워크플로우
│   │
│   ├── controller/                  # Layer 3: 유스케이스 조율
│   │   ├── workflow_controller.py   #   워크플로우 조율, Signal/Slot 중개
│   │   └── git_worker.py            #   QThread 래퍼 (비동기 Git 작업)
│   │
│   └── ui/                          # Layer 4: 사용자 인터페이스
│       ├── main_window.py           #   QMainWindow (탭 기반)
│       ├── branch_panel.py          #   브랜치 상태 위젯
│       ├── commit_log_panel.py      #   커밋 로그 위젯
│       ├── workflow_panel.py        #   릴리스/핫픽스 위젯
│       ├── pr_check_panel.py        #   PR 체크 위젯
│       └── menu_bar_app.py          #   QSystemTrayIcon 래퍼
│
├── scripts/                         # 기존 쉘 스크립트 (수정 금지)
├── resources/                       # 아이콘, QSS 스타일시트
└── tests/                           # 유닛 + 통합 테스트
```

**Dependency Direction**: UI -> Controller -> Domain -> Infrastructure

**Key Rule**: Domain Layer는 PyQt6에 의존하지 않는다 (순수 Python 클래스).

### 4.5 주요 기술 결정 코드 스니펫

#### 4.5.1 GitRepository - GitPython 래핑 패턴

```python
# app/infrastructure/git_repository.py
from git import Repo, InvalidGitRepositoryError
from app.domain.models import BranchSummary, Commit, RepoStatus

class GitRepository:
    """GitPython 기반 저장소 접근 추상화.

    모든 Git 저수준 접근을 캡슐화하여 Domain Layer가 GitPython에 직접 의존하지 않도록 한다.
    """

    def __init__(self, repo_path: str):
        try:
            self._repo = Repo(repo_path)
        except InvalidGitRepositoryError:
            raise ValueError(f"Invalid git repository: {repo_path}")
        self._path = repo_path

    def get_current_branch(self) -> str:
        """현재 체크아웃된 브랜치명 반환. Detached HEAD면 커밋 해시 반환."""
        if self._repo.head.is_detached:
            return f"(detached: {self._repo.head.commit.hexsha[:7]})"
        return self._repo.active_branch.name

    def get_branches(self, remote: bool = False) -> list[str]:
        """로컬 또는 리모트 브랜치 목록 반환."""
        if remote:
            return [ref.name for ref in self._repo.remote().refs]
        return [branch.name for branch in self._repo.branches]

    def get_commit_log(self, limit: int = 20) -> list[Commit]:
        """최근 N개 커밋을 Commit 도메인 객체로 반환."""
        commits = []
        for c in self._repo.iter_commits(max_count=limit):
            commits.append(Commit(
                hash=c.hexsha,
                short_hash=c.hexsha[:7],
                message=c.message.strip(),
                author=str(c.author),
                date=c.committed_datetime,
            ))
        return commits

    def get_status(self) -> RepoStatus:
        """워킹 트리 상태 (dirty, untracked 등) 반환."""
        return RepoStatus(
            is_dirty=self._repo.is_dirty(),
            untracked_files=self._repo.untracked_files,
            changed_files=[item.a_path for item in self._repo.index.diff(None)],
            staged_files=[item.a_path for item in self._repo.index.diff("HEAD")],
        )

    def get_ahead_behind(self, branch: str = "develop") -> tuple[int, int]:
        """로컬 브랜치가 origin 대비 ahead/behind 커밋 수."""
        local = self._repo.heads[branch].commit
        remote = self._repo.remotes.origin.refs[branch].commit
        ahead = len(list(self._repo.iter_commits(f"origin/{branch}..{branch}")))
        behind = len(list(self._repo.iter_commits(f"{branch}..origin/{branch}")))
        return (ahead, behind)

    def fetch(self) -> None:
        """origin에서 최신 정보 가져오기."""
        self._repo.remotes.origin.fetch()
```

#### 4.5.2 Domain Models - dataclass 정의

```python
# app/domain/models.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class CheckCategory(Enum):
    CONVENTION = "convention"
    SIZE = "size"
    TODO = "todo"

@dataclass
class BranchSummary:
    current: str
    ahead: int
    behind: int
    is_dirty: bool
    local_branches: list[str] = field(default_factory=list)
    remote_branches: list[str] = field(default_factory=list)

@dataclass
class Commit:
    hash: str
    short_hash: str
    message: str
    author: str
    date: datetime

@dataclass
class RepoStatus:
    is_dirty: bool
    untracked_files: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    staged_files: list[str] = field(default_factory=list)

@dataclass
class CheckItem:
    category: CheckCategory
    passed: bool
    message: str

@dataclass
class PrCheckReport:
    passed: bool
    items: list[CheckItem] = field(default_factory=list)
    summary: str = ""

@dataclass
class ScriptResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int

@dataclass
class SyncResult:
    success: bool
    message: str
    commits_pulled: int = 0

@dataclass
class BranchResult:
    success: bool
    branch_name: str
    message: str

@dataclass
class RepoConfig:
    name: str
    path: str
    is_active: bool = False
```

#### 4.5.3 GitWorker - QThread 패턴

```python
# app/controller/git_worker.py
from typing import Callable, Any
from PyQt6.QtCore import QThread, pyqtSignal

class GitWorker(QThread):
    """Git 작업을 별도 스레드에서 실행하는 QThread 래퍼.

    Usage:
        worker = GitWorker(lambda: branch_manager.sync_develop())
        worker.result_ready.connect(self.on_sync_complete)
        worker.error_occurred.connect(self.on_sync_error)
        worker.start()
    """

    result_ready = pyqtSignal(object)   # 작업 결과 전달
    error_occurred = pyqtSignal(str)    # 에러 메시지 전달
    progress = pyqtSignal(str)          # 진행 상태 메시지

    def __init__(self, task: Callable[[], Any], parent=None):
        super().__init__(parent)
        self._task = task

    def run(self) -> None:
        try:
            result = self._task()
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))
```

#### 4.5.4 WorkflowController - Signal/Slot 중개 패턴

```python
# app/controller/workflow_controller.py
from PyQt6.QtCore import QObject, pyqtSignal
from app.domain.branch_manager import BranchManager
from app.domain.models import BranchSummary, SyncResult
from app.controller.git_worker import GitWorker

class WorkflowController(QObject):
    """UI와 Domain 사이의 중개자. 모든 Git 작업을 GitWorker로 래핑.

    Presentation Layer는 이 컨트롤러만 호출하며, Domain/Infrastructure 직접 접근 금지.
    """

    # UI 업데이트용 시그널
    branch_updated = pyqtSignal(BranchSummary)
    sync_completed = pyqtSignal(SyncResult)
    error_occurred = pyqtSignal(str)
    loading_started = pyqtSignal()
    loading_finished = pyqtSignal()

    def __init__(self, branch_manager: BranchManager, parent=None):
        super().__init__(parent)
        self._branch_manager = branch_manager
        self._active_worker: GitWorker | None = None

    def refresh_branch_status(self) -> None:
        """브랜치 상태 새로고침 (비동기)."""
        self._run_task(
            task=self._branch_manager.get_branch_summary,
            on_success=self.branch_updated.emit,
        )

    def sync_develop(self) -> None:
        """develop 브랜치 동기화 (비동기)."""
        self._run_task(
            task=self._branch_manager.sync_develop,
            on_success=self.sync_completed.emit,
        )

    def _run_task(self, task, on_success) -> None:
        """GitWorker로 태스크를 래핑하여 비동기 실행.
        동시에 하나의 워커만 실행 (큐잉 패턴).
        """
        if self._active_worker and self._active_worker.isRunning():
            return  # 이전 작업 완료 대기

        self.loading_started.emit()
        self._active_worker = GitWorker(task)
        self._active_worker.result_ready.connect(on_success)
        self._active_worker.result_ready.connect(lambda _: self.loading_finished.emit())
        self._active_worker.error_occurred.connect(self.error_occurred.emit)
        self._active_worker.error_occurred.connect(lambda _: self.loading_finished.emit())
        self._active_worker.start()
```

#### 4.5.5 ScriptRunner - subprocess 래핑 패턴

```python
# app/infrastructure/script_runner.py
import subprocess
from pathlib import Path
from app.domain.models import ScriptResult

class ScriptRunner:
    """기존 쉘 스크립트를 subprocess로 래핑. 스크립트 자체는 수정하지 않는다.

    scripts/ 폴더의 기존 쉘 스크립트를 실행하고 결과를 ScriptResult로 반환.
    """

    def __init__(self, scripts_dir: str | Path):
        self._scripts_dir = Path(scripts_dir)
        if not self._scripts_dir.exists():
            raise FileNotFoundError(f"Scripts directory not found: {scripts_dir}")

    def run(self, script_name: str, args: list[str] | None = None,
            timeout: int = 60, cwd: str | None = None) -> ScriptResult:
        """쉘 스크립트 동기 실행."""
        script_path = self._scripts_dir / script_name
        if not script_path.exists():
            return ScriptResult(
                success=False, stdout="",
                stderr=f"Script not found: {script_name}",
                return_code=-1,
            )

        cmd = ["bash", str(script_path)] + (args or [])
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            return ScriptResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ScriptResult(
                success=False, stdout="",
                stderr=f"Script timed out after {timeout}s",
                return_code=-2,
            )
        except Exception as e:
            return ScriptResult(
                success=False, stdout="",
                stderr=str(e),
                return_code=-3,
            )
```

#### 4.5.6 ConfigStore - JSON 설정 관리 패턴

```python
# app/infrastructure/config_store.py
import json
from pathlib import Path
from app.domain.models import RepoConfig

CONFIG_DIR = Path.home() / ".git-dashboard"
CONFIG_FILE = CONFIG_DIR / "config.json"

class ConfigStore:
    """~/.git-dashboard/config.json 기반 설정 관리.

    앱 재시작 후에도 저장소 경로, 테마 설정 등이 유지되도록 JSON 파일로 영속화.
    """

    def __init__(self, config_path: Path | None = None):
        self._config_path = config_path or CONFIG_FILE
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if self._config_path.exists():
            with open(self._config_path, "r") as f:
                return json.load(f)
        return {"repositories": [], "theme": "dark", "active_repo": None}

    def _save(self) -> None:
        with open(self._config_path, "w") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get_repositories(self) -> list[RepoConfig]:
        return [RepoConfig(**r) for r in self._data.get("repositories", [])]

    def add_repository(self, path: str, name: str) -> None:
        repos = self._data.setdefault("repositories", [])
        if not any(r["path"] == path for r in repos):
            repos.append({"name": name, "path": path, "is_active": len(repos) == 0})
            self._save()

    def get_active_repo(self) -> RepoConfig | None:
        for r in self._data.get("repositories", []):
            if r.get("is_active"):
                return RepoConfig(**r)
        repos = self._data.get("repositories", [])
        return RepoConfig(**repos[0]) if repos else None

    def set_active_repo(self, path: str) -> None:
        for r in self._data.get("repositories", []):
            r["is_active"] = (r["path"] == path)
        self._save()

    def get_theme(self) -> str:
        return self._data.get("theme", "dark")

    def set_theme(self, theme: str) -> None:
        self._data["theme"] = theme
        self._save()
```

---

## 5. Implementation Priority & Order

### 5.1 구현 순서 (4-Layer, Bottom-Up)

```
Phase 1 (MVP - Week 1):
  Infrastructure ---
    1. git_repository.py     (GitPython 래핑)
    2. config_store.py       (JSON 설정 관리)
    3. script_runner.py      (subprocess 래핑)
  Domain ---
    4. models.py             (dataclass: BranchSummary, Commit, etc.)
    5. branch_manager.py     (브랜치 상태 + 동기화)
    6. commit_analyzer.py    (커밋 로그 분석)
  Application ---
    7. git_worker.py         (QThread 래퍼)
    8. workflow_controller.py (Signal/Slot 조율)
  Presentation ---
    9. main_window.py        (탭 기반 메인 윈도우)
   10. branch_panel.py       (F-01: 브랜치 상태)
   11. commit_log_panel.py   (F-03: 커밋 로그)

Phase 2 (Workflow - Week 2~3):
  Domain ---
   12. pr_checker.py         (PR 품질 검사 로직)
   13. release_manager.py    (릴리스/핫픽스 도메인)
  Presentation ---
   14. workflow_panel.py     (F-06, F-07: 릴리스/핫픽스 UI)
   15. pr_check_panel.py     (F-05: PR 체크 UI)
   16. menu_bar_app.py       (F-08: QSystemTrayIcon)
  Style ---
   17. dark_theme.qss        (다크 테마)

Phase 3 (Polish - Week 4):
  Infrastructure ---
   18. config_store.py 확장  (다중 저장소 설정)
  Presentation ---
   19. main_window.py 확장   (F-09: 탭 전환)
   20. 알림 모듈             (F-11: macOS 알림)
  Build ---
   21. PyInstaller spec      (F-12: .app 패키징)
```

### 5.2 Critical Path

```
git_repository.py -> branch_manager.py -> git_worker.py -> branch_panel.py -> main_window.py
                                                         /
config_store.py -----------------------------------------
```

git_repository.py가 모든 도메인 로직의 기반이므로, 이 클래스의 품질과 테스트 커버리지가 전체 프로젝트의 핵심 경로.

---

## 6. File-Level Implementation Checklist

### 6.1 Infrastructure Layer

#### `app/infrastructure/git_repository.py` (GitRepository)

- [ ] `__init__(self, repo_path: str)` - Repo 객체 생성, InvalidGitRepositoryError 처리
- [ ] `get_current_branch() -> str` - 현재 브랜치명 반환, detached HEAD 처리
- [ ] `get_branches(remote: bool = False) -> list[str]` - 로컬/리모트 브랜치 목록
- [ ] `get_commit_log(limit: int = 20) -> list[Commit]` - 최근 N개 커밋
- [ ] `get_status() -> RepoStatus` - dirty, untracked, staged 파일 목록
- [ ] `get_ahead_behind(branch: str) -> tuple[int, int]` - ahead/behind 카운트
- [ ] `fetch() -> None` - origin fetch
- [ ] `pull(branch: str) -> bool` - origin pull (merge)
- [ ] `get_diff_stat(base: str, head: str) -> DiffStat` - 브랜치 간 diff 통계
- [ ] `get_file_diff(base: str, head: str) -> list[str]` - 변경된 파일 목록

#### `app/infrastructure/config_store.py` (ConfigStore)

- [ ] `__init__(self, config_path: Path | None)` - 설정 파일 로딩/생성
- [ ] `_load() -> dict` - JSON 파일 읽기
- [ ] `_save() -> None` - JSON 파일 쓰기
- [ ] `get_repositories() -> list[RepoConfig]` - 등록된 저장소 목록
- [ ] `add_repository(path: str, name: str) -> None` - 저장소 추가
- [ ] `remove_repository(path: str) -> None` - 저장소 제거
- [ ] `get_active_repo() -> RepoConfig | None` - 현재 활성 저장소
- [ ] `set_active_repo(path: str) -> None` - 활성 저장소 변경
- [ ] `get_theme() -> str` - 현재 테마
- [ ] `set_theme(theme: str) -> None` - 테마 변경
- [ ] `get_scripts_dir() -> Path` - 스크립트 디렉토리 경로

#### `app/infrastructure/script_runner.py` (ScriptRunner)

- [ ] `__init__(self, scripts_dir: str | Path)` - 스크립트 디렉토리 검증
- [ ] `run(script_name, args, timeout, cwd) -> ScriptResult` - 동기 실행
- [ ] `run_async(script_name, args, callback) -> None` - 비동기 실행 (Thread)
- [ ] `list_scripts() -> list[str]` - 사용 가능한 스크립트 목록
- [ ] `validate_script(script_name) -> bool` - 스크립트 존재/실행 권한 확인

### 6.2 Domain Layer

#### `app/domain/models.py` (도메인 모델)

- [ ] `BranchSummary` dataclass - current, ahead, behind, is_dirty, local_branches, remote_branches
- [ ] `Commit` dataclass - hash, short_hash, message, author, date
- [ ] `RepoStatus` dataclass - is_dirty, untracked_files, changed_files, staged_files
- [ ] `CheckItem` dataclass - category (CheckCategory Enum), passed, message
- [ ] `PrCheckReport` dataclass - passed, items, summary
- [ ] `ScriptResult` dataclass - success, stdout, stderr, return_code
- [ ] `SyncResult` dataclass - success, message, commits_pulled
- [ ] `BranchResult` dataclass - success, branch_name, message
- [ ] `RepoConfig` dataclass - name, path, is_active
- [ ] `CheckCategory` Enum - CONVENTION, SIZE, TODO
- [ ] `ReleaseInfo` dataclass - version, branch_name, tag_name, created_at
- [ ] `HookResult` dataclass - hook_name, success, output, duration

#### `app/domain/branch_manager.py` (BranchManager)

- [ ] `__init__(self, git_repo: GitRepository)` - GitRepository 의존성 주입
- [ ] `get_branch_summary() -> BranchSummary` - 종합 브랜치 상태
- [ ] `sync_develop() -> SyncResult` - develop 브랜치 동기화 (fetch + merge)
- [ ] `create_release_branch(version: str) -> BranchResult` - release/* 브랜치 생성
- [ ] `create_hotfix_branch(issue_id: str) -> BranchResult` - hotfix/* 브랜치 생성
- [ ] `get_branch_tree() -> dict` - 로컬/리모트 브랜치 트리 구조
- [ ] `is_branch_mergeable(source: str, target: str) -> bool` - 머지 가능 여부

#### `app/domain/commit_analyzer.py` (CommitAnalyzer)

- [ ] `__init__(self, git_repo: GitRepository)` - GitRepository 의존성 주입
- [ ] `get_recent_commits(limit: int = 20) -> list[Commit]` - 최근 커밋 목록
- [ ] `check_commit_convention(commit: Commit) -> CheckItem` - 커밋 메시지 컨벤션 검사
- [ ] `get_commit_stats(days: int = 7) -> dict` - 기간별 커밋 통계
- [ ] `search_commits(keyword: str) -> list[Commit]` - 커밋 메시지 검색

#### `app/domain/pr_checker.py` (PrChecker)

- [ ] `__init__(self, git_repo: GitRepository)` - GitRepository 의존성 주입
- [ ] `check(base: str, head: str) -> PrCheckReport` - 전체 PR 품질 검사
- [ ] `check_commit_convention(base: str, head: str) -> list[CheckItem]` - 커밋 컨벤션
- [ ] `check_file_changes(base: str, head: str, threshold: int = 20) -> CheckItem` - 변경 파일 수
- [ ] `check_todo_comments(base: str, head: str) -> list[CheckItem]` - TODO 잔존
- [ ] `check_large_files(base: str, head: str, max_kb: int = 500) -> CheckItem` - 대용량 파일
- [ ] `_build_summary(items: list[CheckItem]) -> str` - 검사 결과 요약 생성

#### `app/domain/release_manager.py` (ReleaseManager)

- [ ] `__init__(self, git_repo, script_runner, branch_manager)` - 의존성 주입
- [ ] `start_release(version: str) -> BranchResult` - release 워크플로우 시작
- [ ] `finish_release(version: str) -> BranchResult` - release 완료 (태깅 + main 머지)
- [ ] `start_hotfix(issue_id: str) -> BranchResult` - hotfix 워크플로우 시작
- [ ] `finish_hotfix(issue_id: str) -> BranchResult` - hotfix 완료 (develop + main 반영)
- [ ] `get_release_history() -> list[ReleaseInfo]` - 릴리스 이력
- [ ] `validate_version(version: str) -> bool` - 버전 문자열 검증 (semver)

### 6.3 Application Layer

#### `app/controller/git_worker.py` (GitWorker)

- [ ] `result_ready = pyqtSignal(object)` - 성공 결과 시그널
- [ ] `error_occurred = pyqtSignal(str)` - 에러 시그널
- [ ] `progress = pyqtSignal(str)` - 진행 상태 시그널
- [ ] `__init__(self, task: Callable, parent)` - 태스크 함수 주입
- [ ] `run() -> None` - QThread.run 오버라이드, try/except 래핑

#### `app/controller/workflow_controller.py` (WorkflowController)

- [ ] `branch_updated = pyqtSignal(BranchSummary)` - 브랜치 상태 갱신 시그널
- [ ] `sync_completed = pyqtSignal(SyncResult)` - 동기화 완료 시그널
- [ ] `commit_log_updated = pyqtSignal(list)` - 커밋 로그 갱신 시그널
- [ ] `pr_check_completed = pyqtSignal(PrCheckReport)` - PR 체크 완료 시그널
- [ ] `error_occurred = pyqtSignal(str)` - 에러 시그널
- [ ] `loading_started = pyqtSignal()` - 로딩 시작 시그널
- [ ] `loading_finished = pyqtSignal()` - 로딩 완료 시그널
- [ ] `__init__(self, branch_manager, commit_analyzer, pr_checker, release_manager)` - DI
- [ ] `refresh_branch_status() -> None` - 비동기 브랜치 상태 갱신
- [ ] `sync_develop() -> None` - 비동기 develop 동기화
- [ ] `load_commit_log(limit: int = 20) -> None` - 비동기 커밋 로그 로딩
- [ ] `run_pr_check(base: str, head: str) -> None` - 비동기 PR 체크
- [ ] `start_release(version: str) -> None` - 비동기 릴리스 시작
- [ ] `start_hotfix(issue_id: str) -> None` - 비동기 핫픽스 시작
- [ ] `_run_task(task, on_success) -> None` - GitWorker 래핑 헬퍼

### 6.4 Presentation Layer

#### `app/ui/main_window.py` (MainWindow)

- [ ] `__init__(self, controller: WorkflowController)` - 컨트롤러 주입
- [ ] `_setup_ui() -> None` - QTabWidget 기반 UI 구성
- [ ] `_setup_tabs() -> None` - 탭 추가 (Branch, Commit, PR Check, Release, Hotfix)
- [ ] `_setup_toolbar() -> None` - 저장소 선택 드롭다운 + 설정 버튼
- [ ] `_setup_statusbar() -> None` - 하단 상태바 (로딩 인디케이터)
- [ ] `_connect_signals() -> None` - 컨트롤러 시그널 연결
- [ ] `on_repo_changed(repo_path: str) -> None` - 저장소 전환 핸들러
- [ ] `on_loading_started() -> None` - 로딩 인디케이터 표시
- [ ] `on_loading_finished() -> None` - 로딩 인디케이터 숨김
- [ ] `on_error(message: str) -> None` - 에러 다이얼로그 표시

#### `app/ui/branch_panel.py` (BranchStatusPanel)

- [ ] `__init__(self, controller: WorkflowController)` - 컨트롤러 주입
- [ ] `_setup_ui() -> None` - 현재 브랜치, ahead/behind, dirty 상태 위젯 구성
- [ ] `_setup_branch_tree() -> None` - QTreeWidget 로컬/리모트 브랜치 트리
- [ ] `_setup_action_buttons() -> None` - Sync Develop, Refresh 버튼
- [ ] `update_branch_info(summary: BranchSummary) -> None` - 슬롯: 브랜치 정보 업데이트
- [ ] `on_sync_clicked() -> None` - Sync 버튼 클릭 핸들러
- [ ] `on_sync_completed(result: SyncResult) -> None` - 동기화 결과 표시

#### `app/ui/commit_log_panel.py` (CommitLogPanel)

- [ ] `__init__(self, controller: WorkflowController)` - 컨트롤러 주입
- [ ] `_setup_ui() -> None` - QTableWidget (hash, message, author, date 컬럼)
- [ ] `_setup_filters() -> None` - 검색 바, 날짜 필터
- [ ] `update_commits(commits: list[Commit]) -> None` - 슬롯: 커밋 목록 업데이트
- [ ] `on_commit_selected(row: int) -> None` - 커밋 선택 시 상세 표시

#### `app/ui/workflow_panel.py` (WorkflowPanel)

- [ ] `__init__(self, controller: WorkflowController)` - 컨트롤러 주입
- [ ] `_setup_release_ui() -> None` - Release 위저드 (버전 입력 + 단계별 가이드)
- [ ] `_setup_hotfix_ui() -> None` - Hotfix 위저드 (이슈 ID 입력)
- [ ] `on_release_start() -> None` - Release 시작 핸들러
- [ ] `on_release_finish() -> None` - Release 완료 핸들러
- [ ] `on_hotfix_start() -> None` - Hotfix 시작 핸들러
- [ ] `on_hotfix_finish() -> None` - Hotfix 완료 핸들러
- [ ] `update_progress(step: int, total: int, message: str) -> None` - 진행 상태 표시

#### `app/ui/pr_check_panel.py` (PrCheckPanel)

- [ ] `__init__(self, controller: WorkflowController)` - 컨트롤러 주입
- [ ] `_setup_ui() -> None` - base/head 브랜치 선택 + Check 버튼 + 결과 영역
- [ ] `_setup_result_view() -> None` - CheckItem 목록 표시 (pass/fail 아이콘)
- [ ] `on_check_clicked() -> None` - PR Check 실행 핸들러
- [ ] `update_result(report: PrCheckReport) -> None` - 슬롯: 검사 결과 표시
- [ ] `_render_check_item(item: CheckItem) -> QWidget` - 개별 검사 항목 위젯

#### `app/ui/menu_bar_app.py` (MenuBarApp)

- [ ] `__init__(self, controller: WorkflowController)` - 컨트롤러 주입
- [ ] `_setup_tray() -> None` - QSystemTrayIcon + QMenu 구성
- [ ] `_setup_menu() -> None` - 메뉴 항목 (현재 브랜치, Sync, PR Check, Release, Hotfix)
- [ ] `update_branch_info(summary: BranchSummary) -> None` - 메뉴 텍스트 업데이트
- [ ] `on_tray_activated(reason) -> None` - 트레이 아이콘 클릭 핸들러
- [ ] `show_notification(title: str, message: str) -> None` - macOS 알림 표시

### 6.5 Entry Point

#### `main.py`

- [ ] QApplication 생성
- [ ] ConfigStore 초기화
- [ ] GitRepository 초기화 (활성 저장소 경로)
- [ ] Domain 객체 생성 (BranchManager, CommitAnalyzer, PrChecker, ReleaseManager)
- [ ] WorkflowController 생성 (도메인 객체 주입)
- [ ] MainWindow 생성 (컨트롤러 주입)
- [ ] MenuBarApp 생성 (컨트롤러 주입)
- [ ] QSS 다크 테마 로딩
- [ ] app.exec() 실행

### 6.6 Tests

#### `tests/test_git_repository.py`

- [ ] `test_init_valid_repo` - 유효한 저장소 초기화
- [ ] `test_init_invalid_repo` - 잘못된 경로 ValueError
- [ ] `test_get_current_branch` - 현재 브랜치명 반환
- [ ] `test_get_current_branch_detached` - detached HEAD 처리
- [ ] `test_get_branches_local` - 로컬 브랜치 목록
- [ ] `test_get_branches_remote` - 리모트 브랜치 목록
- [ ] `test_get_commit_log` - 커밋 로그 반환 (limit 검증)
- [ ] `test_get_status_clean` - 클린 워킹 트리
- [ ] `test_get_status_dirty` - 더티 워킹 트리 (untracked, changed, staged)
- [ ] `test_get_ahead_behind` - ahead/behind 카운트
- [ ] `test_fetch` - origin fetch 성공

#### `tests/test_config_store.py`

- [ ] `test_init_creates_config` - 설정 파일 자동 생성
- [ ] `test_add_repository` - 저장소 추가
- [ ] `test_add_duplicate_repository` - 중복 추가 방지
- [ ] `test_get_active_repo` - 활성 저장소 반환
- [ ] `test_set_active_repo` - 활성 저장소 변경
- [ ] `test_get_set_theme` - 테마 저장/로딩
- [ ] `test_persistence` - 파일 재로딩 후 데이터 유지

#### `tests/test_branch_manager.py`

- [ ] `test_get_branch_summary` - BranchSummary 정상 반환
- [ ] `test_sync_develop_success` - 동기화 성공
- [ ] `test_sync_develop_already_up_to_date` - 이미 최신
- [ ] `test_sync_develop_conflict` - 충돌 시 에러 처리
- [ ] `test_create_release_branch` - release/* 브랜치 생성
- [ ] `test_create_hotfix_branch` - hotfix/* 브랜치 생성

#### `tests/test_commit_analyzer.py`

- [ ] `test_get_recent_commits` - 커밋 목록 반환
- [ ] `test_check_commit_convention_pass` - 컨벤션 준수 커밋
- [ ] `test_check_commit_convention_fail` - 컨벤션 위반 커밋
- [ ] `test_search_commits` - 키워드 검색

#### `tests/test_pr_checker.py`

- [ ] `test_check_all_pass` - 전체 검사 통과
- [ ] `test_check_convention_fail` - 커밋 컨벤션 실패
- [ ] `test_check_file_changes_over_threshold` - 파일 변경 수 초과
- [ ] `test_check_todo_found` - TODO 잔존 감지
- [ ] `test_check_large_files` - 대용량 파일 감지

#### `tests/test_script_runner.py`

- [ ] `test_run_success` - 스크립트 정상 실행
- [ ] `test_run_script_not_found` - 없는 스크립트 에러
- [ ] `test_run_timeout` - 타임아웃 처리
- [ ] `test_run_with_args` - 인자 전달
- [ ] `test_list_scripts` - 스크립트 목록 조회

#### `tests/test_workflow_controller.py`

- [ ] `test_refresh_branch_status` - 비동기 브랜치 갱신 시그널
- [ ] `test_sync_develop` - 비동기 동기화 시그널
- [ ] `test_concurrent_task_queuing` - 동시 작업 큐잉

---

## 7. Day-by-Day Detailed Work Plan

### Week 1: MVP (F-01 ~ F-04)

#### Day 1 (AM): 프로젝트 초기 세팅

| Time | Task | Output |
|------|------|--------|
| 09:00-10:00 | Poetry 프로젝트 초기화, pyproject.toml 작성 | `pyproject.toml` |
| 10:00-10:30 | 폴더 구조 생성 (app/, scripts/, resources/, tests/) | 디렉토리 트리 |
| 10:30-11:00 | `__init__.py` 파일 생성, main.py 스켈레톤 | `main.py` (빈 QApplication) |
| 11:00-12:00 | PyInstaller smoke test (빈 앱 빌드) | 빌드 성공 확인 |

#### Day 1 (PM): 도메인 모델 + GitRepository 기반

| Time | Task | Output |
|------|------|--------|
| 13:00-14:30 | `app/domain/models.py` 전체 dataclass 정의 | 모든 도메인 모델 |
| 14:30-16:00 | `app/infrastructure/git_repository.py` 기본 메서드 (init, current_branch, branches) | GitRepository 기본 |
| 16:00-17:00 | `tests/test_git_repository.py` (init, current_branch 테스트) | 3개 테스트 케이스 |

#### Day 2 (AM): GitRepository 완성

| Time | Task | Output |
|------|------|--------|
| 09:00-10:30 | GitRepository.get_commit_log(), get_status() 구현 | 커밋/상태 메서드 |
| 10:30-12:00 | GitRepository.get_ahead_behind(), fetch(), pull() 구현 | 동기화 메서드 |

#### Day 2 (PM): GitRepository 테스트 + ConfigStore

| Time | Task | Output |
|------|------|--------|
| 13:00-14:30 | `tests/test_git_repository.py` 나머지 테스트 케이스 | 8개 이상 테스트 |
| 14:30-16:00 | `app/infrastructure/config_store.py` 구현 | ConfigStore |
| 16:00-17:00 | `tests/test_config_store.py` | 7개 테스트 케이스 |

#### Day 3 (AM): BranchManager + CommitAnalyzer

| Time | Task | Output |
|------|------|--------|
| 09:00-10:30 | `app/domain/branch_manager.py` 구현 | BranchManager |
| 10:30-12:00 | `tests/test_branch_manager.py` | 6개 테스트 케이스 |

#### Day 3 (PM): CommitAnalyzer + ScriptRunner

| Time | Task | Output |
|------|------|--------|
| 13:00-14:30 | `app/domain/commit_analyzer.py` 구현 | CommitAnalyzer |
| 14:30-15:30 | `tests/test_commit_analyzer.py` | 4개 테스트 케이스 |
| 15:30-17:00 | `app/infrastructure/script_runner.py` 구현 | ScriptRunner |

#### Day 4 (AM): Application Layer

| Time | Task | Output |
|------|------|--------|
| 09:00-10:00 | `app/controller/git_worker.py` 구현 | GitWorker (QThread) |
| 10:00-12:00 | `app/controller/workflow_controller.py` 구현 | WorkflowController |

#### Day 4 (PM): Presentation Layer - MainWindow + BranchPanel

| Time | Task | Output |
|------|------|--------|
| 13:00-14:30 | `app/ui/main_window.py` - QTabWidget 기반 윈도우 | MainWindow |
| 14:30-16:00 | `app/ui/branch_panel.py` - 브랜치 상태 + 트리뷰 | BranchStatusPanel |
| 16:00-17:00 | `app/ui/commit_log_panel.py` - 커밋 로그 테이블 | CommitLogPanel |

#### Day 5 (AM): 통합 + 연결

| Time | Task | Output |
|------|------|--------|
| 09:00-10:30 | `main.py` 완성 - 전체 DI 조립 + QApplication 실행 | 앱 실행 가능 |
| 10:30-12:00 | 컨트롤러 <-> UI 시그널 연결, 실 저장소로 동작 확인 | E2E 동작 |

#### Day 5 (PM): MVP 마무리

| Time | Task | Output |
|------|------|--------|
| 13:00-14:30 | 버그 수정 + UI 레이아웃 미세 조정 | UI 완성도 향상 |
| 14:30-15:30 | `tests/test_script_runner.py` | 5개 테스트 케이스 |
| 15:30-17:00 | 전체 테스트 실행, coverage 확인 (>= 80% Infrastructure) | MVP QA 완료 |

**Week 1 완료 기준**: 앱 실행 시 브랜치 상태, 커밋 로그, 브랜치 목록 표시, Sync Develop 동작

---

### Week 2: 워크플로우 + ScriptRunner (F-05 ~ F-07 기반)

#### Day 6 (AM): ScriptRunner 래핑 테스트

| Time | Task | Output |
|------|------|--------|
| 09:00-10:30 | scripts/ 폴더에 기존 쉘 스크립트 배치, 실행 권한 확인 | 스크립트 준비 |
| 10:30-12:00 | ScriptRunner로 branch_sync.sh 래핑 + 실행 테스트 | 동기화 스크립트 래핑 |

#### Day 6 (PM): 나머지 스크립트 래핑

| Time | Task | Output |
|------|------|--------|
| 13:00-14:30 | pr_checker.sh 래핑 + 테스트 | PR 체커 래핑 |
| 14:30-16:00 | release_helper.sh 래핑 + 테스트 | 릴리스 스크립트 래핑 |
| 16:00-17:00 | hotfix_workflow.sh 래핑 + 테스트 | 핫픽스 스크립트 래핑 |

#### Day 7 (AM): PrChecker 도메인 로직

| Time | Task | Output |
|------|------|--------|
| 09:00-10:30 | `app/domain/pr_checker.py` - check_commit_convention() | 커밋 컨벤션 검사 |
| 10:30-12:00 | PrChecker - check_file_changes(), check_todo_comments() | 파일/TODO 검사 |

#### Day 7 (PM): PrChecker 테스트

| Time | Task | Output |
|------|------|--------|
| 13:00-14:30 | `tests/test_pr_checker.py` 전체 테스트 | 5개 테스트 케이스 |
| 14:30-16:00 | PrChecker.check() 통합 - PrCheckReport 생성 | 전체 PR 검사 통합 |
| 16:00-17:00 | WorkflowController에 PR 체크 메서드 추가 | 컨트롤러 확장 |

#### Day 8 (AM): CommitLogPanel 완성

| Time | Task | Output |
|------|------|--------|
| 09:00-10:30 | CommitLogPanel 상세 구현 (정렬, 검색 필터) | 완성된 커밋 로그 UI |
| 10:30-12:00 | 커밋 선택 시 상세 정보 표시 (diff stat) | 커밋 상세 뷰 |

#### Day 8 (PM): PrCheckPanel UI

| Time | Task | Output |
|------|------|--------|
| 13:00-14:30 | `app/ui/pr_check_panel.py` - base/head 선택 + Check 버튼 | PR 체크 UI |
| 14:30-16:00 | 검사 결과 렌더링 (pass/fail 아이콘, 요약) | 결과 표시 |
| 16:00-17:00 | WorkflowController 시그널 연결 | PR 체크 E2E |

#### Day 9 (AM): ReleaseManager 도메인

| Time | Task | Output |
|------|------|--------|
| 09:00-10:30 | `app/domain/release_manager.py` - start_release(), finish_release() | 릴리스 도메인 |
| 10:30-12:00 | ReleaseManager - start_hotfix(), finish_hotfix() | 핫픽스 도메인 |

#### Day 9 (PM): ReleaseManager 테스트

| Time | Task | Output |
|------|------|--------|
| 13:00-14:30 | `tests/test_release_manager.py` | 릴리스/핫픽스 테스트 |
| 14:30-16:00 | WorkflowController에 릴리스/핫픽스 메서드 추가 | 컨트롤러 확장 |
| 16:00-17:00 | E2E 테스트 (더미 저장소에서 릴리스 워크플로우) | 통합 검증 |

#### Day 10 (AM): WorkflowPanel UI

| Time | Task | Output |
|------|------|--------|
| 09:00-10:30 | `app/ui/workflow_panel.py` - Release 위저드 UI | 릴리스 UI |
| 10:30-12:00 | WorkflowPanel - Hotfix 위저드 UI | 핫픽스 UI |

#### Day 10 (PM): 통합 + Week 2 마무리

| Time | Task | Output |
|------|------|--------|
| 13:00-14:30 | WorkflowPanel 컨트롤러 연결 + E2E 테스트 | 워크플로우 E2E |
| 14:30-16:00 | 버그 수정 + UI 미세 조정 | Week 2 완성도 |
| 16:00-17:00 | 전체 테스트 실행, coverage 확인 | Week 2 QA |

---

### Week 3: 메뉴바 + 테마 + 폴리싱 (F-08)

#### Day 11 (AM): PrChecker 고도화

| Time | Task | Output |
|------|------|--------|
| 09:00-10:30 | PrChecker - check_large_files(), _build_summary() 구현 | 추가 검사 항목 |
| 10:30-12:00 | PrCheckPanel UI 고도화 (결과 컬러링, 요약 카드) | 완성된 PR UI |

#### Day 11 (PM): PrChecker 통합 테스트

| Time | Task | Output |
|------|------|--------|
| 13:00-14:30 | PR 체크 E2E 테스트 (실 저장소) | 통합 검증 |
| 14:30-16:00 | ScriptRunner + PrChecker 연동 (pr_checker.sh 결과 병합) | 스크립트 통합 |
| 16:00-17:00 | 에러 케이스 처리 (리모트 없음, 브랜치 없음 등) | 에지 케이스 |

#### Day 12 (AM): QSystemTrayIcon 프로토타입

| Time | Task | Output |
|------|------|--------|
| 09:00-10:30 | QSystemTrayIcon 프로토타입 - 아이콘 표시 + 기본 메뉴 | 메뉴바 프로토타입 |
| 10:30-12:00 | macOS에서 동작 검증, 이벤트 루프 안정성 확인 | UX 검증 |

#### Day 12 (PM): MenuBarApp 완성

| Time | Task | Output |
|------|------|--------|
| 13:00-14:30 | `app/ui/menu_bar_app.py` - 전체 메뉴 구성 | MenuBarApp |
| 14:30-16:00 | 메뉴 항목 클릭 -> 해당 탭 활성화 연결 | 메뉴 -> UI 연결 |
| 16:00-17:00 | 현재 브랜치 정보 실시간 업데이트 | 메뉴바 동적 업데이트 |

#### Day 13 (AM): 아이콘 + 리소스

| Time | Task | Output |
|------|------|--------|
| 09:00-10:00 | 메뉴바 아이콘 제작/선정 (menu_icon.png) | `resources/icons/` |
| 10:00-12:00 | 앱 아이콘 (.icns), 앱 타이틀 바 아이콘 | 리소스 완성 |

#### Day 13 (PM): 다크 테마

| Time | Task | Output |
|------|------|--------|
| 13:00-15:00 | `resources/styles/dark_theme.qss` 작성 | QSS 다크 테마 |
| 15:00-17:00 | 모든 위젯에 테마 적용, 미세 조정 | 일관된 다크 UI |

#### Day 14 (AM): UI 폴리싱

| Time | Task | Output |
|------|------|--------|
| 09:00-10:30 | 레이아웃 정밀 조정 (간격, 폰트, 색상) | 완성도 향상 |
| 10:30-12:00 | 로딩 인디케이터 (스피너/프로그레스바) 구현 | UX 향상 |

#### Day 14 (PM): 에러 핸들링 + 에지 케이스

| Time | Task | Output |
|------|------|--------|
| 13:00-14:30 | Git 명령 실패 시 사용자 친화적 에러 메시지 | 에러 UX |
| 14:30-16:00 | 네트워크 끊김, 저장소 없음 등 에지 케이스 | 안정성 향상 |
| 16:00-17:00 | 전체 앱 흐름 수동 QA | Week 3 QA |

#### Day 15: Gap 분석 + 개선

| Time | Task | Output |
|------|------|--------|
| 09:00-12:00 | `/pdca analyze git-dashboard` 실행, Gap 분석 | 분석 보고서 |
| 13:00-17:00 | Gap 기반 수정 + 추가 테스트 | 품질 향상 |

---

### Week 4: 다중 저장소 + 알림 + 패키징 (F-09 ~ F-12)

#### Day 16 (AM): ConfigStore 확장

| Time | Task | Output |
|------|------|--------|
| 09:00-10:30 | ConfigStore - 다중 저장소 CRUD, 기본 저장소 설정 | ConfigStore 확장 |
| 10:30-12:00 | ConfigStore 테스트 확장 | 추가 테스트 |

#### Day 16 (PM): MainWindow 탭 전환

| Time | Task | Output |
|------|------|--------|
| 13:00-15:00 | MainWindow - 저장소별 탭 전환 UI (드롭다운 또는 탭) | 다중 저장소 UI |
| 15:00-17:00 | 저장소 전환 시 컨트롤러/도메인 재초기화 | 저장소 전환 E2E |

#### Day 17 (AM): 저장소 관리 다이얼로그

| Time | Task | Output |
|------|------|--------|
| 09:00-10:30 | 저장소 추가/제거 설정 다이얼로그 | 설정 UI |
| 10:30-12:00 | 저장소 추가 시 유효성 검증 (Git 저장소 여부 확인) | 입력 검증 |

#### Day 17 (PM): Pre-push Hook 시각화

| Time | Task | Output |
|------|------|--------|
| 13:00-14:30 | Hook 실행 결과 캡처 + 파싱 | Hook 결과 모델 |
| 14:30-16:00 | Hook 결과 UI (로그 뷰어) | Hook 시각화 |
| 16:00-17:00 | 테스트 | Hook 테스트 |

#### Day 18 (AM): macOS 알림

| Time | Task | Output |
|------|------|--------|
| 09:00-10:30 | macOS 알림 모듈 (osascript 또는 pyobjc) | 알림 구현 |
| 10:30-12:00 | 브랜치 뒤처짐 감지 -> 알림 트리거 | 알림 통합 |

#### Day 18 (PM): 알림 폴링 + 설정

| Time | Task | Output |
|------|------|--------|
| 13:00-14:30 | QTimer 기반 폴링 (5분 간격 브랜치 상태 체크) | 자동 모니터링 |
| 14:30-16:00 | 알림 설정 UI (on/off, 간격 설정) | 알림 설정 |
| 16:00-17:00 | 테스트 + 알림 동작 확인 | 알림 QA |

#### Day 19 (AM): PyInstaller 패키징

| Time | Task | Output |
|------|------|--------|
| 09:00-10:30 | PyInstaller .spec 파일 작성 | `git-dashboard.spec` |
| 10:30-12:00 | 첫 빌드 + 문제 해결 (hidden imports, data files) | .app 초안 빌드 |

#### Day 19 (PM): 패키징 최적화

| Time | Task | Output |
|------|------|--------|
| 13:00-14:30 | .app 번들 크기 최적화 (불필요 모듈 제외) | 100MB 이하 달성 |
| 14:30-16:00 | .app에서 리소스 경로 처리 (아이콘, QSS, 스크립트) | 리소스 번들링 |
| 16:00-17:00 | 깨끗한 macOS 환경에서 .app 실행 테스트 | 배포 검증 |

#### Day 20 (AM): 최종 QA

| Time | Task | Output |
|------|------|--------|
| 09:00-10:30 | 전체 테스트 실행, coverage >= 70% 확인 | 최종 테스트 |
| 10:30-12:00 | `/pdca analyze git-dashboard` 최종 Gap 분석 | 최종 분석 |

#### Day 20 (PM): 보고서 + 문서화

| Time | Task | Output |
|------|------|--------|
| 13:00-14:30 | Gap 기반 최종 수정 | 최종 수정 |
| 14:30-16:00 | `/pdca report git-dashboard` 완료 보고서 | 보고서 |
| 16:00-17:00 | README.md 업데이트, 사용 가이드 작성 | 문서화 완료 |

---

## 8. Test Strategy

### 8.1 레이어별 테스트 전략

| Layer | Test Type | Framework | Coverage Target |
|-------|-----------|-----------|-----------------|
| Infrastructure | Unit + Integration | pytest + tmp_path | >= 80% |
| Domain | Unit | pytest | >= 90% |
| Application | Unit + Signal 검증 | pytest + pytest-qt | >= 70% |
| Presentation | Integration (Manual + pytest-qt) | pytest-qt | >= 50% |

### 8.2 테스트 케이스 총 목록

#### Infrastructure Layer (21 TC)

| TC-ID | File | Test Case | Type |
|-------|------|-----------|------|
| TC-I-01 | test_git_repository.py | 유효한 저장소 초기화 | Unit |
| TC-I-02 | test_git_repository.py | 잘못된 경로 ValueError | Unit |
| TC-I-03 | test_git_repository.py | 현재 브랜치명 반환 | Unit |
| TC-I-04 | test_git_repository.py | detached HEAD 처리 | Unit |
| TC-I-05 | test_git_repository.py | 로컬 브랜치 목록 | Unit |
| TC-I-06 | test_git_repository.py | 리모트 브랜치 목록 | Unit |
| TC-I-07 | test_git_repository.py | 커밋 로그 반환 (limit) | Unit |
| TC-I-08 | test_git_repository.py | 클린 워킹 트리 상태 | Unit |
| TC-I-09 | test_git_repository.py | 더티 워킹 트리 상태 | Unit |
| TC-I-10 | test_git_repository.py | ahead/behind 카운트 | Integration |
| TC-I-11 | test_git_repository.py | origin fetch | Integration |
| TC-I-12 | test_config_store.py | 설정 파일 자동 생성 | Unit |
| TC-I-13 | test_config_store.py | 저장소 추가 | Unit |
| TC-I-14 | test_config_store.py | 중복 추가 방지 | Unit |
| TC-I-15 | test_config_store.py | 활성 저장소 반환 | Unit |
| TC-I-16 | test_config_store.py | 활성 저장소 변경 | Unit |
| TC-I-17 | test_config_store.py | 테마 저장/로딩 | Unit |
| TC-I-18 | test_config_store.py | 파일 재로딩 후 데이터 유지 | Integration |
| TC-I-19 | test_script_runner.py | 스크립트 정상 실행 | Unit |
| TC-I-20 | test_script_runner.py | 없는 스크립트 에러 | Unit |
| TC-I-21 | test_script_runner.py | 타임아웃 처리 | Unit |

#### Domain Layer (19 TC)

| TC-ID | File | Test Case | Type |
|-------|------|-----------|------|
| TC-D-01 | test_branch_manager.py | BranchSummary 정상 반환 | Unit |
| TC-D-02 | test_branch_manager.py | 동기화 성공 | Unit |
| TC-D-03 | test_branch_manager.py | 이미 최신 상태 | Unit |
| TC-D-04 | test_branch_manager.py | 충돌 시 에러 처리 | Unit |
| TC-D-05 | test_branch_manager.py | release/* 브랜치 생성 | Unit |
| TC-D-06 | test_branch_manager.py | hotfix/* 브랜치 생성 | Unit |
| TC-D-07 | test_commit_analyzer.py | 커밋 목록 반환 | Unit |
| TC-D-08 | test_commit_analyzer.py | 컨벤션 준수 커밋 | Unit |
| TC-D-09 | test_commit_analyzer.py | 컨벤션 위반 커밋 | Unit |
| TC-D-10 | test_commit_analyzer.py | 키워드 검색 | Unit |
| TC-D-11 | test_pr_checker.py | 전체 검사 통과 | Unit |
| TC-D-12 | test_pr_checker.py | 커밋 컨벤션 실패 | Unit |
| TC-D-13 | test_pr_checker.py | 파일 변경 수 초과 | Unit |
| TC-D-14 | test_pr_checker.py | TODO 잔존 감지 | Unit |
| TC-D-15 | test_pr_checker.py | 대용량 파일 감지 | Unit |
| TC-D-16 | test_release_manager.py | 릴리스 시작 | Unit |
| TC-D-17 | test_release_manager.py | 릴리스 완료 | Unit |
| TC-D-18 | test_release_manager.py | 핫픽스 시작 | Unit |
| TC-D-19 | test_release_manager.py | 핫픽스 완료 | Unit |

#### Application Layer (5 TC)

| TC-ID | File | Test Case | Type |
|-------|------|-----------|------|
| TC-A-01 | test_git_worker.py | 정상 태스크 실행 + result_ready 시그널 | Unit |
| TC-A-02 | test_git_worker.py | 에러 발생 + error_occurred 시그널 | Unit |
| TC-A-03 | test_workflow_controller.py | 브랜치 갱신 시그널 체인 | Integration |
| TC-A-04 | test_workflow_controller.py | 동기화 시그널 체인 | Integration |
| TC-A-05 | test_workflow_controller.py | 동시 작업 큐잉 | Integration |

### 8.3 테스트 환경

```bash
# 테스트 실행
poetry run pytest tests/ -v --cov=app --cov-report=html

# PyQt6 테스트 (pytest-qt 필요)
poetry add --group dev pytest-qt
poetry run pytest tests/ -v -k "test_ui"

# 특정 레이어만 테스트
poetry run pytest tests/test_git_repository.py tests/test_config_store.py -v  # Infrastructure
poetry run pytest tests/test_branch_manager.py tests/test_pr_checker.py -v     # Domain
```

### 8.4 Mock 전략

| Layer | Mock Target | Mock Method |
|-------|-------------|-------------|
| Infrastructure | 실제 Git 저장소 | `tmp_path` + `git init` (로컬 테스트 저장소) |
| Domain | GitRepository | `unittest.mock.MagicMock` |
| Application | Domain 객체 + QThread | `MagicMock` + `pytest-qt.qtbot` |
| Presentation | WorkflowController | `MagicMock` (시그널은 실제 사용) |

---

## 9. Work Estimation

### 9.1 Phase별 공수 산정

| Phase | 기능 수 | 예상 일수 | 비고 |
|-------|---------|----------|------|
| MVP (Week 1) | F-01~F-04 (4개) | **5일** | 핵심 기반 구조 + 기본 UI |
| Phase 2 (Week 2-3) | F-05~F-08 (4개) | **10일** | 워크플로우 + 메뉴바 |
| Phase 3 (Week 4) | F-09~F-12 (4개) | **5일** | 폴리싱 + 패키징 |
| **Total** | **12개** | **20일** | 버퍼 포함 4주 |

### 9.2 기능별 복잡도 상세

| 기능 ID | 기능명 | 복잡도 | 예상 일수 | 비고 |
|---------|--------|--------|----------|------|
| F-01 | 브랜치 상태 패널 | **Medium** | 1.5일 | GitRepository + BranchPanel + QThread 연결 |
| F-02 | 원클릭 브랜치 동기화 | **Low** | 0.5일 | BranchManager.sync_develop() 호출 + 버튼 |
| F-03 | 커밋 로그 뷰어 | **Low** | 1일 | GitPython log + QTableWidget |
| F-04 | 브랜치 목록 | **Low** | 0.5일 | F-01 패널 내 서브 기능 |
| F-05 | PR 품질 체커 | **High** | 2일 | 커밋 컨벤션 파싱 + diff 분석 + 결과 UI |
| F-06 | Release 워크플로우 | **High** | 2일 | 멀티스텝 위저드 UI + 스크립트 래핑 + 롤백 |
| F-07 | Hotfix 워크플로우 | **Medium** | 1일 | F-06과 유사 구조, develop+main 이중 반영 |
| F-08 | 메뉴바 상주 | **High** | 1.5일 | QSystemTrayIcon 구현 + 이벤트 루프 검증 |
| F-09 | 다중 저장소 관리 | **Medium** | 2일 | ConfigStore 확장 + 탭 전환 + 저장소별 상태 |
| F-10 | Pre-push Hook 시각화 | **Medium** | 1일 | Hook 실행 결과 캡처 + 로그 표시 |
| F-11 | macOS 알림 | **Low** | 0.5일 | pyobjc 또는 osascript 래핑 |
| F-12 | .app 패키징 | **High** | 2일 | PyInstaller spec 작성 + 의존성 번들링 + 서명 |
| --- | **합계** | --- | **15.5일** | 버퍼 포함 20 working days (4주) |

---

## 10. Success Criteria

### 10.1 Definition of Done (per Phase)

#### MVP (Week 1)
- [ ] git_repository.py 유닛 테스트 통과 (>= 80% coverage)
- [ ] 메인 윈도우에서 브랜치 상태 확인 가능
- [ ] develop 동기화 원클릭 동작
- [ ] 커밋 로그 20개 표시
- [ ] QThread로 UI 블로킹 없이 Git 작업 실행

#### Phase 2 (Week 2-3)
- [ ] 기존 4개 쉘 스크립트 모두 ScriptRunner로 래핑
- [ ] Release 워크플로우 full cycle 동작
- [ ] Hotfix 워크플로우 full cycle 동작
- [ ] PR 체크 결과 UI 표시
- [ ] macOS 메뉴바 상주 동작

#### Phase 3 (Week 4)
- [ ] 3개 이상 저장소 탭 전환 동작
- [ ] .app 패키징 성공, 100MB 이하
- [ ] macOS 알림 동작

### 10.2 Quality Criteria

- [ ] 전체 테스트 커버리지 >= 70%
- [ ] black 포매팅 적용 (CI 수준)
- [ ] Domain Layer에 PyQt6 import 없음 (의존 방향 준수)
- [ ] 앱 3초 이내 초기 로딩

---

## 11. Risks and Mitigation

| # | Risk | Impact | Likelihood | Mitigation |
|---|------|--------|------------|------------|
| R1 | rumps + PyQt6 이벤트 루프 충돌 | High | **High** | QSystemTrayIcon 우선 채택, rumps는 fallback으로 별도 프로세스 분리 |
| R2 | PyInstaller macOS 패키징 오류 | Medium | **Medium** | Week 1 D1에 PyInstaller smoke test 포함, CI에 빌드 테스트 추가 |
| R3 | AWS CodeCommit 인증 문제 | Medium | **Low** | 로컬 git credential 그대로 사용, SSH/HTTPS 양방향 지원 |
| R4 | 기존 쉘 스크립트 경로 의존성 | Low | **Low** | ConfigStore에서 스크립트 경로 설정 가능하게 |
| R5 | GitPython 대규모 저장소 성능 | Medium | **Medium** | 커밋 로그 limit 적용, 캐싱 전략 (ConfigStore 활용) |
| R6 | QThread 동시성 문제 | High | **Medium** | 한 번에 하나의 GitWorker만 실행하는 큐잉 패턴 적용 |
| R7 | macOS 권한 문제 (.app에서 파일시스템 접근) | Medium | **Medium** | Phase 3 초기에 entitlements 설정, sandbox 테스트 |

---

## 12. PDCA Cycle Plan

### 12.1 Phase Mapping

```
Plan  -- 현재 문서 (git-dashboard-plan.md)
Design -- git-dashboard-design.md (이미 완성)
Do     -- Week 1~4 구현
Check  -- Week별 Gap Analysis (/pdca analyze git-dashboard)
Act    -- Gap 기반 반복 개선 (/pdca iterate git-dashboard)
Report -- 완료 보고 (/pdca report git-dashboard)
```

### 12.2 Phase별 PDCA 적용

| Week | Do (구현) | Check (검증) | Act (개선) |
|------|----------|-------------|-----------|
| W1 (MVP) | F-01~F-04 구현 | pytest 유닛 테스트, 수동 UX 테스트 | 테스트 실패 시 즉시 수정 |
| W2 | F-05~F-07 구현 | 스크립트 래핑 통합 테스트 | ScriptRunner 에러 핸들링 보완 |
| W3 | F-08 + UI 폴리싱 | Gap 분석 (설계 vs 구현) | Match Rate < 90% 항목 수정 |
| W4 | F-09~F-12 구현 | PyInstaller 빌드 테스트, 최종 QA | 패키징 이슈 해결, 최종 보고서 |

### 12.3 Quality Gate

| Gate | Threshold | Next Action |
|------|-----------|-------------|
| Week 1 완료 | MVP 4개 기능 동작 + 테스트 통과 | Phase 2 시작 |
| Week 3 완료 | Match Rate >= 70% | Phase 3 시작 |
| Week 4 완료 | Match Rate >= 90%, Critical = 0 | `/pdca report git-dashboard` |

---

## 13. Development Environment Setup

```bash
# 1. 프로젝트 초기화
cd /Users/jypark/Documents/Claude/Projects/git-dashboard
poetry init --name git-dashboard --python "^3.11"

# 2. 의존성 추가
poetry add PyQt6 GitPython
poetry add rumps  # fallback용, Phase 2에서 판단
poetry add --group dev pytest pytest-qt pytest-cov black pyinstaller

# 3. 폴더 구조 생성
mkdir -p app/{ui,controller,domain,infrastructure}
mkdir -p scripts resources/{icons,styles} tests

# 4. 실행
poetry run python main.py

# 5. 테스트
poetry run pytest tests/ -v --cov=app

# 6. 포매터
poetry run black .
```

---

## 14. Next Steps

1. [x] Plan 문서 작성 (현재 문서)
2. [x] Design 문서 확인 (`git-dashboard-design.md` 완성됨)
3. [ ] 프로젝트 초기 세팅 (Poetry, 폴더 구조, pyproject.toml)
4. [ ] Week 1 Day 1 시작: `models.py` + `git_repository.py` + `config_store.py`
5. [ ] Week 1 완료 후: `/pdca analyze git-dashboard`

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-30 | Initial draft - 전체 PDCA Plan 수립 | jypark |
| 0.2 | 2026-03-30 | Detailed plan - 파일별 체크리스트, Day-by-Day 계획, 테스트 전략, 코드 스니펫 추가 | jypark |
