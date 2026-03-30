# Git Dashboard Visual Plan

> Mermaid 다이어그램 기반 프로젝트 시각화
>
> **Project**: git-dashboard
> **Date**: 2026-03-30
> **Reference**: `git-dashboard-plan.md`, `git-dashboard-design.md`

---

## A. Project Timeline (Gantt Chart)

```mermaid
gantt
    title Git Dashboard - 4-Week Development Timeline
    dateFormat  YYYY-MM-DD
    axisFormat  %m/%d

    section Phase 1: MVP
    프로젝트 세팅 + models.py              :done, d1, 2026-03-31, 1d
    GitRepository 구현 + 테스트             :d2, after d1, 1d
    ConfigStore + BranchManager             :d3, after d2, 1d
    MainWindow + BranchPanel + CommitLog UI :d4, after d3, 1d
    GitWorker 통합 + MVP 마무리             :d5, after d4, 1d

    section Phase 2: Workflow
    ScriptRunner 래핑 (4개 스크립트)        :d6, after d5, 2d
    PrChecker 도메인 + 테스트               :d8, after d6, 1d
    CommitLogPanel 완성 + PrCheckPanel UI   :d9, after d8, 1d
    ReleaseManager + WorkflowPanel          :d10, after d9, 2d

    section Phase 3: Menu + Polish
    PrChecker 고도화 + 통합 테스트          :d12, after d10, 1d
    QSystemTrayIcon 메뉴바 구현             :d13, after d12, 2d
    다크 테마 QSS + UI 폴리싱               :d15, after d13, 2d
    Gap 분석 + 개선                         :d17, after d15, 1d

    section Phase 4: Package
    ConfigStore 확장 + 다중 저장소           :d18, after d17, 2d
    알림 + Pre-push Hook                    :d20, after d18, 1d
    PyInstaller 패키징                      :d21, after d20, 2d
    최종 QA + 보고서                        :d23, after d21, 1d

    section Milestones
    MVP 완료                                :milestone, m1, after d5, 0d
    Workflow 완료                           :milestone, m2, after d10, 0d
    UI 완성                                 :milestone, m3, after d17, 0d
    릴리스                                  :milestone, m4, after d23, 0d
```

---

## B. 4-Layer Architecture Diagram

```mermaid
graph TB
    subgraph Presentation["Presentation Layer (app/ui/)"]
        MW[MainWindow<br/>QMainWindow]
        BP[BranchStatusPanel<br/>QWidget]
        CLP[CommitLogPanel<br/>QWidget]
        WP[WorkflowPanel<br/>QWidget]
        PCP[PrCheckPanel<br/>QWidget]
        MBA[MenuBarApp<br/>QSystemTrayIcon]
    end

    subgraph Application["Application Layer (app/controller/)"]
        WC[WorkflowController<br/>QObject]
        GW[GitWorker<br/>QThread]
    end

    subgraph Domain["Domain Layer (app/domain/)"]
        M[models.py<br/>dataclasses]
        BM[BranchManager]
        CA[CommitAnalyzer]
        PC[PrChecker]
        RM[ReleaseManager]
    end

    subgraph Infrastructure["Infrastructure Layer (app/infrastructure/)"]
        GR[GitRepository<br/>GitPython]
        SR[ScriptRunner<br/>subprocess]
        CS[ConfigStore<br/>JSON]
    end

    subgraph External["External Systems"]
        GP[GitPython<br/>Library]
        SS[Shell Scripts<br/>scripts/]
        CF[Config File<br/>~/.git-dashboard/]
        GIT[Git Repository<br/>AWS CodeCommit]
    end

    %% Presentation -> Application
    MW --> WC
    BP --> WC
    CLP --> WC
    WP --> WC
    PCP --> WC
    MBA --> WC

    %% Application -> Domain
    WC --> BM
    WC --> CA
    WC --> PC
    WC --> RM
    GW -.->|QThread| WC

    %% Domain -> Infrastructure
    BM --> GR
    BM --> SR
    CA --> GR
    PC --> GR
    RM --> GR
    RM --> SR

    %% Infrastructure -> External
    GR --> GP
    SR --> SS
    CS --> CF
    GP --> GIT

    %% Domain uses Models
    BM --> M
    CA --> M
    PC --> M
    RM --> M

    %% Styling
    style Presentation fill:#4a9eff,stroke:#2d7cd6,color:#fff
    style Application fill:#ff9f43,stroke:#d68836,color:#fff
    style Domain fill:#2ed573,stroke:#26b85f,color:#fff
    style Infrastructure fill:#a55eea,stroke:#8844cc,color:#fff
    style External fill:#576574,stroke:#444,color:#fff
```

---

## C. Data Flow Diagram (Sequence)

### C.1 브랜치 상태 조회 흐름

```mermaid
sequenceDiagram
    actor User
    participant UI as BranchStatusPanel
    participant WC as WorkflowController
    participant GW as GitWorker (QThread)
    participant BM as BranchManager
    participant GR as GitRepository
    participant Git as Git (GitPython)

    User->>UI: 앱 실행 / Refresh 클릭
    UI->>WC: refresh_branch_status()
    WC->>WC: loading_started.emit()
    WC->>GW: GitWorker(branch_manager.get_branch_summary)
    activate GW
    Note over GW: 별도 스레드에서 실행<br/>(UI 블로킹 방지)
    GW->>BM: get_branch_summary()
    BM->>GR: get_current_branch()
    GR->>Git: repo.active_branch.name
    Git-->>GR: "feature/ai-reader-fix"
    GR-->>BM: "feature/ai-reader-fix"
    BM->>GR: get_ahead_behind("develop")
    GR->>Git: iter_commits()
    Git-->>GR: ahead=2, behind=0
    GR-->>BM: (2, 0)
    BM->>GR: get_status()
    GR->>Git: repo.is_dirty()
    Git-->>GR: RepoStatus
    GR-->>BM: RepoStatus
    BM->>GR: get_branches(remote=True)
    GR-->>BM: ["origin/develop", "origin/main", ...]
    BM-->>GW: BranchSummary
    deactivate GW
    GW->>WC: result_ready.emit(BranchSummary)
    WC->>WC: loading_finished.emit()
    WC->>UI: branch_updated.emit(BranchSummary)
    UI->>UI: update_branch_info(summary)
    UI-->>User: 브랜치 상태 표시 완료
```

### C.2 develop 동기화 흐름

```mermaid
sequenceDiagram
    actor User
    participant UI as BranchStatusPanel
    participant WC as WorkflowController
    participant GW as GitWorker (QThread)
    participant BM as BranchManager
    participant GR as GitRepository
    participant SR as ScriptRunner
    participant SH as branch_sync.sh

    User->>UI: "Sync Develop" 버튼 클릭
    UI->>WC: sync_develop()
    WC->>WC: loading_started.emit()
    WC->>GW: GitWorker(branch_manager.sync_develop)
    activate GW
    Note over GW: QThread 실행

    alt ScriptRunner 사용 (기존 스크립트 래핑)
        GW->>BM: sync_develop()
        BM->>SR: run("branch_sync.sh", ["develop"])
        SR->>SH: subprocess.run(["bash", "branch_sync.sh", "develop"])
        SH-->>SR: ScriptResult(success=True, stdout="...")
        SR-->>BM: ScriptResult
    else GitPython 직접 사용
        GW->>BM: sync_develop()
        BM->>GR: fetch()
        GR-->>BM: OK
        BM->>GR: pull("develop")
        GR-->>BM: OK
    end

    BM-->>GW: SyncResult(success=True, commits_pulled=3)
    deactivate GW
    GW->>WC: result_ready.emit(SyncResult)
    WC->>WC: loading_finished.emit()
    WC->>UI: sync_completed.emit(SyncResult)
    UI->>UI: on_sync_completed(result)
    UI-->>User: "Sync 완료: 3 commits pulled"
```

### C.3 PR 품질 체크 흐름

```mermaid
sequenceDiagram
    actor User
    participant UI as PrCheckPanel
    participant WC as WorkflowController
    participant GW as GitWorker (QThread)
    participant PC as PrChecker
    participant GR as GitRepository

    User->>UI: base=develop, head=feature/xxx 선택
    User->>UI: "Check PR" 클릭
    UI->>WC: run_pr_check("develop", "feature/xxx")
    WC->>GW: GitWorker(pr_checker.check)
    activate GW

    GW->>PC: check("develop", "feature/xxx")

    par 병렬 검사
        PC->>PC: check_commit_convention()
        PC->>GR: get_commit_log()
        GR-->>PC: commits
    and
        PC->>PC: check_file_changes(threshold=20)
        PC->>GR: get_file_diff("develop", "feature/xxx")
        GR-->>PC: changed_files
    and
        PC->>PC: check_todo_comments()
        PC->>GR: get_file_diff()
        GR-->>PC: diff_content
    end

    PC->>PC: _build_summary(items)
    PC-->>GW: PrCheckReport(passed=False, items=[...])
    deactivate GW

    GW->>WC: result_ready.emit(PrCheckReport)
    WC->>UI: pr_check_completed.emit(PrCheckReport)
    UI->>UI: update_result(report)
    UI-->>User: 검사 결과 표시 (pass/fail 항목)
```

---

## D. Critical Path Diagram (Flowchart)

```mermaid
flowchart LR
    subgraph CP["Critical Path"]
        direction LR
        GR[git_repository.py<br/>Infrastructure]
        BM[branch_manager.py<br/>Domain]
        GW[git_worker.py<br/>Application]
        BP[branch_panel.py<br/>Presentation]
        MW[main_window.py<br/>Presentation]
    end

    subgraph SP["Support Path"]
        direction LR
        CS[config_store.py<br/>Infrastructure]
        MD[models.py<br/>Domain]
        WC[workflow_controller.py<br/>Application]
    end

    GR ==>|"Day 1-2"| BM
    BM ==>|"Day 3"| GW
    GW ==>|"Day 4"| BP
    BP ==>|"Day 4-5"| MW

    CS -.->|"Day 2"| MW
    MD -.->|"Day 1"| BM
    MD -.->|"Day 1"| GR
    WC -.->|"Day 4"| GW

    style GR fill:#ff6b6b,stroke:#c44,color:#fff
    style BM fill:#ff6b6b,stroke:#c44,color:#fff
    style GW fill:#ff6b6b,stroke:#c44,color:#fff
    style BP fill:#ff6b6b,stroke:#c44,color:#fff
    style MW fill:#ff6b6b,stroke:#c44,color:#fff
    style CS fill:#48dbfb,stroke:#0984e3,color:#000
    style MD fill:#48dbfb,stroke:#0984e3,color:#000
    style WC fill:#48dbfb,stroke:#0984e3,color:#000
```

### D.2 전체 프로젝트 의존성 그래프

```mermaid
flowchart TD
    MP[main.py] --> MW[main_window.py]
    MP --> MBA[menu_bar_app.py]
    MP --> CS[config_store.py]
    MP --> WC[workflow_controller.py]

    MW --> BP[branch_panel.py]
    MW --> CLP[commit_log_panel.py]
    MW --> WP[workflow_panel.py]
    MW --> PCP[pr_check_panel.py]

    BP --> WC
    CLP --> WC
    WP --> WC
    PCP --> WC
    MBA --> WC

    WC --> GW[git_worker.py]
    WC --> BM[branch_manager.py]
    WC --> CA[commit_analyzer.py]
    WC --> PC[pr_checker.py]
    WC --> RM[release_manager.py]

    BM --> GR[git_repository.py]
    BM --> SR[script_runner.py]
    CA --> GR
    PC --> GR
    RM --> GR
    RM --> SR

    BM --> MD[models.py]
    CA --> MD
    PC --> MD
    RM --> MD
    GR --> MD
    SR --> MD
    CS --> MD

    GR --> GP((GitPython))
    SR --> SH((Shell Scripts))
    CS --> JF((JSON File))

    style MP fill:#ffd32a,stroke:#c4a000,color:#000
    style MW fill:#4a9eff,stroke:#2d7cd6,color:#fff
    style BP fill:#4a9eff,stroke:#2d7cd6,color:#fff
    style CLP fill:#4a9eff,stroke:#2d7cd6,color:#fff
    style WP fill:#4a9eff,stroke:#2d7cd6,color:#fff
    style PCP fill:#4a9eff,stroke:#2d7cd6,color:#fff
    style MBA fill:#4a9eff,stroke:#2d7cd6,color:#fff
    style WC fill:#ff9f43,stroke:#d68836,color:#fff
    style GW fill:#ff9f43,stroke:#d68836,color:#fff
    style BM fill:#2ed573,stroke:#26b85f,color:#fff
    style CA fill:#2ed573,stroke:#26b85f,color:#fff
    style PC fill:#2ed573,stroke:#26b85f,color:#fff
    style RM fill:#2ed573,stroke:#26b85f,color:#fff
    style MD fill:#2ed573,stroke:#26b85f,color:#fff
    style GR fill:#a55eea,stroke:#8844cc,color:#fff
    style SR fill:#a55eea,stroke:#8844cc,color:#fff
    style CS fill:#a55eea,stroke:#8844cc,color:#fff
```

---

## E. Class Diagram

```mermaid
classDiagram
    class GitRepository {
        -Repo _repo
        -str _path
        +__init__(repo_path: str)
        +get_current_branch() str
        +get_branches(remote: bool) list~str~
        +get_commit_log(limit: int) list~Commit~
        +get_status() RepoStatus
        +get_ahead_behind(branch: str) tuple~int, int~
        +fetch() None
        +pull(branch: str) bool
        +get_diff_stat(base: str, head: str) DiffStat
        +get_file_diff(base: str, head: str) list~str~
    }

    class ScriptRunner {
        -Path _scripts_dir
        +__init__(scripts_dir: str)
        +run(script_name: str, args: list, timeout: int) ScriptResult
        +run_async(script_name: str, callback: Callable) None
        +list_scripts() list~str~
        +validate_script(script_name: str) bool
    }

    class ConfigStore {
        -Path _config_path
        -dict _data
        +__init__(config_path: Path)
        +get_repositories() list~RepoConfig~
        +add_repository(path: str, name: str) None
        +remove_repository(path: str) None
        +get_active_repo() RepoConfig
        +set_active_repo(path: str) None
        +get_theme() str
        +set_theme(theme: str) None
    }

    class BranchManager {
        -GitRepository _git_repo
        -ScriptRunner _script_runner
        +__init__(git_repo: GitRepository)
        +get_branch_summary() BranchSummary
        +sync_develop() SyncResult
        +create_release_branch(version: str) BranchResult
        +create_hotfix_branch(issue_id: str) BranchResult
        +get_branch_tree() dict
        +is_branch_mergeable(source: str, target: str) bool
    }

    class CommitAnalyzer {
        -GitRepository _git_repo
        +__init__(git_repo: GitRepository)
        +get_recent_commits(limit: int) list~Commit~
        +check_commit_convention(commit: Commit) CheckItem
        +get_commit_stats(days: int) dict
        +search_commits(keyword: str) list~Commit~
    }

    class PrChecker {
        -GitRepository _git_repo
        +__init__(git_repo: GitRepository)
        +check(base: str, head: str) PrCheckReport
        +check_commit_convention(base: str, head: str) list~CheckItem~
        +check_file_changes(base: str, head: str, threshold: int) CheckItem
        +check_todo_comments(base: str, head: str) list~CheckItem~
        +check_large_files(base: str, head: str) CheckItem
    }

    class ReleaseManager {
        -GitRepository _git_repo
        -ScriptRunner _script_runner
        -BranchManager _branch_manager
        +__init__(git_repo, script_runner, branch_manager)
        +start_release(version: str) BranchResult
        +finish_release(version: str) BranchResult
        +start_hotfix(issue_id: str) BranchResult
        +finish_hotfix(issue_id: str) BranchResult
        +get_release_history() list~ReleaseInfo~
        +validate_version(version: str) bool
    }

    class GitWorker {
        <<QThread>>
        +pyqtSignal result_ready
        +pyqtSignal error_occurred
        +pyqtSignal progress
        -Callable _task
        +__init__(task: Callable)
        +run() None
    }

    class WorkflowController {
        <<QObject>>
        +pyqtSignal branch_updated
        +pyqtSignal sync_completed
        +pyqtSignal commit_log_updated
        +pyqtSignal pr_check_completed
        +pyqtSignal error_occurred
        +pyqtSignal loading_started
        +pyqtSignal loading_finished
        -BranchManager _branch_manager
        -CommitAnalyzer _commit_analyzer
        -PrChecker _pr_checker
        -ReleaseManager _release_manager
        -GitWorker _active_worker
        +refresh_branch_status() None
        +sync_develop() None
        +load_commit_log(limit: int) None
        +run_pr_check(base: str, head: str) None
        +start_release(version: str) None
        +start_hotfix(issue_id: str) None
    }

    class MainWindow {
        <<QMainWindow>>
        -WorkflowController _controller
        +__init__(controller: WorkflowController)
        -_setup_ui() None
        -_setup_tabs() None
        -_setup_toolbar() None
        -_connect_signals() None
    }

    class BranchStatusPanel {
        <<QWidget>>
        -WorkflowController _controller
        +update_branch_info(summary: BranchSummary) None
        +on_sync_clicked() None
        +on_sync_completed(result: SyncResult) None
    }

    class CommitLogPanel {
        <<QWidget>>
        -WorkflowController _controller
        +update_commits(commits: list) None
        +on_commit_selected(row: int) None
    }

    class WorkflowPanel {
        <<QWidget>>
        -WorkflowController _controller
        +on_release_start() None
        +on_release_finish() None
        +on_hotfix_start() None
        +on_hotfix_finish() None
    }

    class PrCheckPanel {
        <<QWidget>>
        -WorkflowController _controller
        +on_check_clicked() None
        +update_result(report: PrCheckReport) None
    }

    class MenuBarApp {
        <<QSystemTrayIcon>>
        -WorkflowController _controller
        +update_branch_info(summary: BranchSummary) None
        +show_notification(title: str, message: str) None
    }

    %% Domain Models
    class BranchSummary {
        <<dataclass>>
        +str current
        +int ahead
        +int behind
        +bool is_dirty
        +list~str~ local_branches
        +list~str~ remote_branches
    }

    class Commit {
        <<dataclass>>
        +str hash
        +str short_hash
        +str message
        +str author
        +datetime date
    }

    class RepoStatus {
        <<dataclass>>
        +bool is_dirty
        +list~str~ untracked_files
        +list~str~ changed_files
        +list~str~ staged_files
    }

    class PrCheckReport {
        <<dataclass>>
        +bool passed
        +list~CheckItem~ items
        +str summary
    }

    class ScriptResult {
        <<dataclass>>
        +bool success
        +str stdout
        +str stderr
        +int return_code
    }

    %% Relationships
    BranchManager --> GitRepository : uses
    BranchManager --> ScriptRunner : uses
    CommitAnalyzer --> GitRepository : uses
    PrChecker --> GitRepository : uses
    ReleaseManager --> GitRepository : uses
    ReleaseManager --> ScriptRunner : uses
    ReleaseManager --> BranchManager : uses

    WorkflowController --> BranchManager : orchestrates
    WorkflowController --> CommitAnalyzer : orchestrates
    WorkflowController --> PrChecker : orchestrates
    WorkflowController --> ReleaseManager : orchestrates
    WorkflowController --> GitWorker : creates

    MainWindow --> BranchStatusPanel : contains
    MainWindow --> CommitLogPanel : contains
    MainWindow --> WorkflowPanel : contains
    MainWindow --> PrCheckPanel : contains

    MainWindow --> WorkflowController : signals
    BranchStatusPanel --> WorkflowController : signals
    CommitLogPanel --> WorkflowController : signals
    WorkflowPanel --> WorkflowController : signals
    PrCheckPanel --> WorkflowController : signals
    MenuBarApp --> WorkflowController : signals

    BranchManager ..> BranchSummary : returns
    CommitAnalyzer ..> Commit : returns
    PrChecker ..> PrCheckReport : returns
    GitRepository ..> RepoStatus : returns
    ScriptRunner ..> ScriptResult : returns
```

---

## F. Feature-Phase Mapping

```mermaid
graph LR
    subgraph W1["Week 1: MVP"]
        F01[F-01: 브랜치 상태]
        F02[F-02: 브랜치 동기화]
        F03[F-03: 커밋 로그]
        F04[F-04: 브랜치 목록]
    end

    subgraph W2["Week 2-3: Workflow"]
        F05[F-05: PR 체커]
        F06[F-06: Release]
        F07[F-07: Hotfix]
        F08[F-08: 메뉴바]
    end

    subgraph W3["Week 4: Polish"]
        F09[F-09: 다중 저장소]
        F10[F-10: Hook 시각화]
        F11[F-11: 알림]
        F12[F-12: .app 패키징]
    end

    F01 --> F02
    F01 --> F03
    F01 --> F04
    F02 --> F06
    F02 --> F07
    F03 --> F05
    F06 --> F09
    F08 --> F11
    F09 --> F12

    style F01 fill:#ff6b6b,stroke:#c44,color:#fff
    style F02 fill:#ff6b6b,stroke:#c44,color:#fff
    style F03 fill:#ff9f43,stroke:#d68,color:#fff
    style F04 fill:#ff9f43,stroke:#d68,color:#fff
    style F05 fill:#ffd32a,stroke:#c4a000,color:#000
    style F06 fill:#ffd32a,stroke:#c4a000,color:#000
    style F07 fill:#48dbfb,stroke:#0984e3,color:#000
    style F08 fill:#ffd32a,stroke:#c4a000,color:#000
    style F09 fill:#2ed573,stroke:#26b85f,color:#fff
    style F10 fill:#48dbfb,stroke:#0984e3,color:#000
    style F11 fill:#48dbfb,stroke:#0984e3,color:#000
    style F12 fill:#ff6b6b,stroke:#c44,color:#fff
```

---

## G. PDCA Cycle Flow

```mermaid
flowchart TD
    START([프로젝트 시작]) --> PLAN

    subgraph PLAN["PLAN"]
        P1[Plan 문서 작성]
        P2[Design 문서 확인]
        P1 --> P2
    end

    PLAN --> DO

    subgraph DO["DO (Week 1~4)"]
        D1[Week 1: MVP<br/>F-01~F-04]
        D2[Week 2-3: Workflow<br/>F-05~F-08]
        D3[Week 4: Polish<br/>F-09~F-12]
        D1 --> D2 --> D3
    end

    DO --> CHECK

    subgraph CHECK["CHECK"]
        C1[pytest 테스트 실행]
        C2[Gap 분석<br/>/pdca analyze]
        C3{Match Rate?}
        C1 --> C2 --> C3
    end

    C3 -->|">= 90%"| REPORT
    C3 -->|"70~89%"| ACT
    C3 -->|"< 70%"| REDESIGN

    subgraph ACT["ACT"]
        A1[pdca-iterator<br/>자동 수정]
        A2[재테스트]
        A1 --> A2
    end

    ACT --> CHECK

    REDESIGN[설계 재검토<br/>/nuri design] --> DO

    subgraph REPORT["REPORT"]
        R1[완료 보고서 생성<br/>/pdca report]
        R2[Archive]
        R1 --> R2
    end

    REPORT --> END([프로젝트 완료])

    style PLAN fill:#4a9eff,stroke:#2d7cd6,color:#fff
    style DO fill:#2ed573,stroke:#26b85f,color:#fff
    style CHECK fill:#ff9f43,stroke:#d68836,color:#fff
    style ACT fill:#ff6b6b,stroke:#c44,color:#fff
    style REPORT fill:#a55eea,stroke:#8844cc,color:#fff
```

---

## H. Signal/Slot Communication Map

```mermaid
flowchart LR
    subgraph UI["UI Layer (Slots)"]
        BP_UBI["BranchPanel<br/>.update_branch_info()"]
        BP_OSC["BranchPanel<br/>.on_sync_completed()"]
        CLP_UC["CommitLogPanel<br/>.update_commits()"]
        PCP_UR["PrCheckPanel<br/>.update_result()"]
        MW_OLS["MainWindow<br/>.on_loading_started()"]
        MW_OLF["MainWindow<br/>.on_loading_finished()"]
        MW_OE["MainWindow<br/>.on_error()"]
    end

    subgraph Signals["WorkflowController Signals"]
        S_BU[/"branch_updated<br/>(BranchSummary)"/]
        S_SC[/"sync_completed<br/>(SyncResult)"/]
        S_CLU[/"commit_log_updated<br/>(list)"/]
        S_PCC[/"pr_check_completed<br/>(PrCheckReport)"/]
        S_LS[/"loading_started<br/>()"/]
        S_LF[/"loading_finished<br/>()"/]
        S_EO[/"error_occurred<br/>(str)"/]
    end

    subgraph Worker["GitWorker Signals"]
        W_RR[/"result_ready<br/>(object)"/]
        W_EO[/"error_occurred<br/>(str)"/]
    end

    W_RR --> S_BU
    W_RR --> S_SC
    W_RR --> S_CLU
    W_RR --> S_PCC
    W_EO --> S_EO

    S_BU --> BP_UBI
    S_SC --> BP_OSC
    S_CLU --> CLP_UC
    S_PCC --> PCP_UR
    S_LS --> MW_OLS
    S_LF --> MW_OLF
    S_EO --> MW_OE

    style UI fill:#4a9eff,stroke:#2d7cd6,color:#fff
    style Signals fill:#ff9f43,stroke:#d68836,color:#fff
    style Worker fill:#2ed573,stroke:#26b85f,color:#fff
```

---

## I. Deployment Architecture

```mermaid
graph TB
    subgraph Bundle[".app Bundle (PyInstaller)"]
        MAIN[main.py<br/>Entry Point]
        APP[app/<br/>4-Layer Source]
        RES[resources/<br/>icons, QSS]
        SCR[scripts/<br/>Shell Scripts]
        LIB[Library/<br/>PyQt6, GitPython]
    end

    subgraph System["macOS System"]
        TRAY[Menu Bar<br/>QSystemTrayIcon]
        NOTIF[Notification Center<br/>macOS 알림]
        FS[File System<br/>~/.git-dashboard/]
    end

    subgraph Repos["Git Repositories"]
        R1[aipd<br/>AWS CodeCommit]
        R2[community<br/>AWS CodeCommit]
        R3[citeasy<br/>AWS CodeCommit]
    end

    MAIN --> APP
    APP --> RES
    APP --> SCR
    APP --> LIB

    Bundle --> TRAY
    Bundle --> NOTIF
    Bundle --> FS

    FS -->|"config.json"| Bundle
    Bundle -->|"GitPython / subprocess"| R1
    Bundle -->|"GitPython / subprocess"| R2
    Bundle -->|"GitPython / subprocess"| R3

    style Bundle fill:#2ed573,stroke:#26b85f,color:#fff
    style System fill:#4a9eff,stroke:#2d7cd6,color:#fff
    style Repos fill:#ff9f43,stroke:#d68836,color:#fff
```

---

*이 문서의 다이어그램은 Mermaid 렌더러가 필요합니다. GitHub, GitLab, VS Code (Mermaid Extension) 등에서 확인 가능합니다.*
