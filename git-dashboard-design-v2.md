# Git Workflow GUI Dashboard
## 설계 문서 v2.0

> macOS 전용 개인 개발 생산성 도구
> Python 3.11+ / PyQt6
> 작성일: 2026-03-31
> v1.0 기반 고도화

---

## 1. 프로젝트 개요

### 1.1 v2.0 목표
v1.0의 기본 Git 워크플로우 관리 기능을 SourceTree 수준의 **시각화 도구**와
**외부 도구 통합**(Apple Keychain, IntelliJ IDEA)으로 고도화하여,
하나의 앱에서 Git 작업의 전 과정을 커버하는 **통합 Git 클라이언트**로 진화시킨다.

### 1.2 v1.0 → v2.0 변경 요약

| 영역 | v1.0 | v2.0 |
|------|------|------|
| 커밋 뷰 | 텍스트 리스트 (hash, message) | **QPainter 기반 커밋 그래프** (브랜치 라인, 머지 포인트, 컬러 코딩) |
| 인증 관리 | 로컬 git credential 의존 | **Apple Keychain 연동** (Git 자격증명 + 앱 설정 보안 저장) |
| IDE 연동 | 없음 | **IntelliJ IDEA 통합** (커밋/푸시 실시간 반영 + 터미널 연동) |
| Diff 뷰 | 없음 | **Syntax Highlighting Diff 뷰어** (인라인/사이드바이사이드) |
| Stash | 없음 | **Stash 관리 GUI** (생성, 적용, 삭제, 미리보기) |
| Rebase | 없음 | **Interactive Rebase GUI** (드래그앤드롭, squash, reword) |
| Conflict | 없음 | **3-way Merge 에디터** (충돌 해결 도구) |

### 1.3 타겟 환경 (v1.0 유지 + 추가)

| 항목 | 내용 |
|------|------|
| OS | macOS 13 Ventura 이상 |
| Git 호스팅 | AWS CodeCommit |
| 브랜치 전략 | `develop → release/* → main` |
| IDE | IntelliJ IDEA (Community / Ultimate) |
| 인증 | macOS Keychain Services |
| Python | 3.11+ |
| GUI | PyQt6 6.6+ |

---

## 2. 신규 기능 명세

### Phase 4: 시각화 고도화 (Week 5~6)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| F-13 | **커밋 그래프 뷰어** | QPainter 기반 DAG(Directed Acyclic Graph) 렌더링, 브랜치별 컬러 라인, 머지/분기 포인트 시각화 | P0 |
| F-14 | **Diff 뷰어** | 파일별 변경사항을 Syntax Highlighting과 함께 인라인/사이드바이사이드 모드로 표시 | P0 |
| F-15 | **Stash 관리** | Stash 목록 조회, 생성(메시지 입력), 적용(apply/pop), 삭제, 변경사항 미리보기 | P1 |

### Phase 5: 외부 통합 (Week 7~8)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| F-16 | **Apple Keychain 연동** | Git 자격증명(HTTPS token, SSH passphrase) 읽기/저장, 앱 설정 보안 저장 | P0 |
| F-17 | **IntelliJ IDEA 연동** | IDE에서 수행한 커밋/푸시를 FileSystemWatcher로 감지하여 실시간 반영, IDE 터미널에서 스크립트 실행 연동 | P1 |

### Phase 6: 고급 Git 기능 (Week 9~10)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| F-18 | **Interactive Rebase** | 커밋 순서 변경(드래그앤드롭), squash, reword, fixup, drop을 GUI로 지원 | P1 |
| F-19 | **Conflict 해결 도구** | 3-way merge 에디터 (BASE / OURS / THEIRS 패널), 충돌 마커 파싱, 해결 후 자동 스테이징 | P1 |

---

## 3. 아키텍처 v2.0

### 3.1 레이어 구조 (확장)

```
┌──────────────────────────────────────────────────────────┐
│                    Presentation Layer                     │
│   MainWindow / CommitGraphView / DiffViewer /            │
│   StashPanel / RebaseDialog / MergeEditor /              │
│   MenuBarApp                                             │
├──────────────────────────────────────────────────────────┤
│                    Application Layer                      │
│   WorkflowController / DiffController /                  │
│   RebaseController / MergeController / GitWorker         │
├──────────────────────────────────────────────────────────┤
│                     Domain Layer                          │
│   BranchManager / PrChecker / CommitGraphBuilder /       │
│   DiffParser / StashManager / RebaseOrchestrator /       │
│   ConflictResolver                                       │
├──────────────────────────────────────────────────────────┤
│                  Infrastructure Layer                     │
│   GitRepository / ScriptRunner / ConfigStore /            │
│   KeychainService / IdeIntegrationService /              │
│   FileWatcherService                                     │
└──────────────────────────────────────────────────────────┘
```

### 3.2 신규 설계 원칙

기존 v1.0 원칙(파일=클래스, Signal/Slot, Worker Thread, Script Runner)에 추가:

- **Custom Painting 분리**: QPainter 로직은 별도 Renderer 클래스로 분리 (예: `GraphRenderer`)
- **Parser 패턴**: Git 출력(diff, merge conflict)을 파싱하는 전용 Parser 클래스 사용
- **Service 패턴**: 외부 시스템 연동(Keychain, IDE)은 Infrastructure의 Service 클래스로 캡슐화
- **FileSystemWatcher**: IDE 연동 시 `.git` 디렉토리 변경 감지로 실시간 동기화
- **Undo/Redo**: Interactive Rebase 등 위험 작업에 실행 전 상태 저장 (reflog 활용)

---

## 4. 파일 구조 v2.0

```
git-dashboard/
├── main.py
├── pyproject.toml
├── README.md
├── git-dashboard-design.md          # v1.0 설계
├── git-dashboard-design-v2.md       # v2.0 설계 (이 파일)
│
├── app/
│   ├── __init__.py
│   │
│   ├── ui/                          # Presentation Layer
│   │   ├── main_window.py           # MainWindow (v1 → 탭/스플리터 확장)
│   │   ├── dashboard_panel.py       # DashboardPanel (v1 유지)
│   │   ├── branch_panel.py          # BranchPanel (v1 유지)
│   │   ├── commit_log_panel.py      # CommitLogPanel (v1 유지)
│   │   ├── repo_sidebar.py          # RepoSidebar (v1 유지)
│   │   ├── repo_manager_dialog.py   # RepoManagerDialog (v1 유지)
│   │   ├── menu_bar_app.py          # MenuBarApp (v1 유지)
│   │   │
│   │   │── # ─── v2.0 신규 UI ───
│   │   ├── commit_graph_view.py     # F-13: CommitGraphView (QAbstractScrollArea + QPainter)
│   │   ├── graph_renderer.py        # F-13: GraphRenderer (QPainter 렌더링 엔진)
│   │   ├── diff_viewer.py           # F-14: DiffViewer (인라인/사이드바이사이드 diff)
│   │   ├── syntax_highlighter.py    # F-14: SyntaxHighlighter (QSyntaxHighlighter 서브클래스)
│   │   ├── stash_panel.py           # F-15: StashPanel (stash 목록 + 액션 버튼)
│   │   ├── rebase_dialog.py         # F-18: RebaseDialog (드래그앤드롭 커밋 리스트)
│   │   ├── merge_editor.py          # F-19: MergeEditor (3-way 패널 에디터)
│   │   ├── keychain_settings.py     # F-16: KeychainSettingsPanel (자격증명 관리 UI)
│   │   └── ide_panel.py             # F-17: IdeBridgePanel (IDE 연동 상태/설정)
│   │
│   ├── controller/                  # Application Layer
│   │   ├── workflow_controller.py   # WorkflowController (v1 → 시그널 확장)
│   │   ├── git_worker.py            # GitWorker (v1 유지)
│   │   │
│   │   │── # ─── v2.0 신규 컨트롤러 ───
│   │   ├── diff_controller.py       # F-14: DiffController
│   │   ├── rebase_controller.py     # F-18: RebaseController
│   │   └── merge_controller.py      # F-19: MergeController
│   │
│   ├── domain/                      # Domain Layer
│   │   ├── models.py                # 데이터 모델 (v1 → 확장)
│   │   ├── branch_manager.py        # BranchManager (v1 유지)
│   │   ├── pr_checker.py            # PrChecker (v1 유지)
│   │   │
│   │   │── # ─── v2.0 신규 도메인 ───
│   │   ├── commit_graph_builder.py  # F-13: CommitGraphBuilder (DAG 토폴로지 계산)
│   │   ├── diff_parser.py           # F-14: DiffParser (unified diff 파싱)
│   │   ├── stash_manager.py         # F-15: StashManager (stash CRUD)
│   │   ├── rebase_orchestrator.py   # F-18: RebaseOrchestrator (rebase 계획 생성/실행)
│   │   └── conflict_resolver.py     # F-19: ConflictResolver (충돌 파싱 + 해결)
│   │
│   └── infrastructure/              # Infrastructure Layer
│       ├── git_repository.py        # GitRepository (v1 → API 확장)
│       ├── config_store.py          # ConfigStore (v1 유지)
│       ├── script_runner.py         # ScriptRunner (v1 유지)
│       │
│       │── # ─── v2.0 신규 인프라 ───
│       ├── keychain_service.py      # F-16: KeychainService (macOS Keychain 연동)
│       ├── ide_integration_service.py  # F-17: IdeIntegrationService (IntelliJ 연동)
│       └── file_watcher_service.py  # F-17: FileWatcherService (.git 변경 감지)
│
├── scripts/                         # 기존 쉘 스크립트 (수정 금지)
├── resources/
│   ├── icons/
│   └── styles/
│       └── dark_theme.qss           # 다크 테마 (v2 위젯 스타일 추가)
│
└── tests/
    ├── test_git_repository.py       # v1 유지
    ├── test_branch_manager.py       # v1 유지
    ├── test_config_store.py         # v1 유지
    ├── test_pr_checker.py           # v1 유지
    │── # ─── v2.0 신규 테스트 ───
    ├── test_commit_graph_builder.py # F-13 테스트
    ├── test_diff_parser.py          # F-14 테스트
    ├── test_stash_manager.py        # F-15 테스트
    ├── test_keychain_service.py     # F-16 테스트
    ├── test_rebase_orchestrator.py  # F-18 테스트
    └── test_conflict_resolver.py    # F-19 테스트
```

---

## 5. 주요 클래스 명세 (v2.0 신규)

### 5.1 F-13: 커밋 그래프 뷰어 (SourceTree 스타일)

#### `CommitGraphBuilder` (domain/commit_graph_builder.py)
```python
from dataclasses import dataclass

@dataclass
class GraphNode:
    """그래프의 한 노드 = 한 커밋"""
    commit: Commit
    column: int              # 그래프에서 x축 위치 (0-based lane)
    color_index: int         # 브랜치별 컬러 인덱스
    parents: list[str]       # 부모 커밋 해시 목록
    children: list[str]      # 자식 커밋 해시 목록
    is_merge: bool           # 머지 커밋 여부 (parents >= 2)
    is_branch_tip: bool      # 브랜치 HEAD 여부
    branch_name: str | None  # 해당 브랜치명 (감지 가능 시)

@dataclass
class GraphEdge:
    """두 노드를 잇는 간선"""
    parent_hash: str
    child_hash: str
    column_from: int
    column_to: int
    color_index: int
    edge_type: str           # "straight" | "merge_in" | "branch_out"

@dataclass
class GraphLayout:
    """전체 그래프 레이아웃 결과"""
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    max_columns: int         # 그래프 최대 너비 (lane 수)
    branch_colors: dict[int, str]  # color_index → hex color


class CommitGraphBuilder:
    """
    Git 커밋 히스토리를 DAG(Directed Acyclic Graph)로 변환하고
    각 커밋의 lane(열) 배치를 계산한다.

    알고리즘: 토폴로지 정렬 + Lane 할당
    - git log --topo-order로 커밋 순서 확보
    - 각 커밋에 lane(column)을 할당하여 교차 최소화
    - 머지 커밋은 두 lane을 연결하는 곡선으로 표현
    """

    # 브랜치별 색상 팔레트 (SourceTree 스타일)
    BRANCH_COLORS = [
        "#6366f1",  # Indigo (develop)
        "#22c55e",  # Green (main)
        "#f59e0b",  # Amber (feature)
        "#ef4444",  # Red (hotfix)
        "#06b6d4",  # Cyan (release)
        "#a855f7",  # Purple
        "#ec4899",  # Pink
        "#14b8a6",  # Teal
    ]

    def __init__(self, repository: "GitRepository"):
        self._repo = repository

    def build(self, limit: int = 200) -> GraphLayout:
        """
        커밋 히스토리를 읽어 GraphLayout을 생성한다.

        Steps:
        1. git log --topo-order --parents로 커밋+부모 정보 수집
        2. 각 커밋에 대해 lane 할당 (활성 lane 추적)
        3. 머지/분기 edge 계산
        4. GraphLayout 반환
        """
        ...

    def _assign_lanes(self, commits: list) -> dict[str, int]:
        """
        Lane 할당 알고리즘:
        - active_lanes: list[str | None] — 현재 활성 lane별 추적 중인 커밋 해시
        - 새 커밋이 어떤 lane도 차지하지 않으면 빈 lane 할당
        - 머지 시 소스 lane 해제
        - 분기 시 새 lane 생성
        """
        ...

    def _detect_branch_names(self, commits: list) -> dict[str, str]:
        """refs/heads, refs/remotes에서 브랜치명 → 커밋 해시 매핑"""
        ...
```

#### `CommitGraphView` (ui/commit_graph_view.py)
```python
class CommitGraphView(QAbstractScrollArea):
    """
    커밋 그래프를 렌더링하는 스크롤 가능한 커스텀 위젯.

    구조:
    ┌──────────────────────────────────────────────────────────┐
    │ [그래프 영역]  │  Hash  │  Message  │  Author  │  Date  │
    │  ●─────●       │ a1b2c3 │ feat: ... │ jypark  │ 1h ago │
    │  │     │       │ d4e5f6 │ fix: ...  │ jypark  │ 2h ago │
    │  ●─┬───●       │ g7h8i9 │ Merge ... │ jypark  │ 3h ago │
    │  │ │           │        │           │         │        │
    └──────────────────────────────────────────────────────────┘

    - 왼쪽: QPainter로 그린 그래프 (GraphRenderer 위임)
    - 오른쪽: 커밋 정보 테이블
    - 클릭 시 commit_selected 시그널 → DiffViewer 연동
    """

    commit_selected = pyqtSignal(str)    # 커밋 해시
    commit_range_selected = pyqtSignal(str, str)  # 범위 선택 (rebase 등)

    ROW_HEIGHT = 32          # 각 커밋 행 높이 (px)
    GRAPH_LANE_WIDTH = 16    # lane 간 간격 (px)
    GRAPH_NODE_RADIUS = 5    # 커밋 노드 반지름 (px)
    MERGE_NODE_RADIUS = 7    # 머지 노드 반지름 (px)

    def __init__(self, parent=None): ...
    def set_graph(self, layout: GraphLayout) -> None: ...
    def paintEvent(self, event: QPaintEvent) -> None: ...
    def mousePressEvent(self, event: QMouseEvent) -> None: ...
    def _hit_test(self, pos: QPoint) -> GraphNode | None: ...
```

#### `GraphRenderer` (ui/graph_renderer.py)
```python
class GraphRenderer:
    """
    QPainter 기반 커밋 그래프 렌더링 엔진.
    CommitGraphView에서 사용.

    렌더링 요소:
    1. Lane Lines: 브랜치별 세로 직선 (컬러)
    2. Nodes: 커밋 = 원, 머지 = 큰 원
    3. Edges: 부모-자식 연결선 (직선/베지어 곡선)
    4. Labels: 브랜치명 태그, HEAD 마커
    5. Selection: 선택된 커밋 하이라이트
    """

    def __init__(self): ...

    def render(self, painter: QPainter, layout: GraphLayout,
               viewport_rect: QRect, scroll_offset: int,
               selected_hash: str | None = None) -> None:
        """전체 그래프를 painter에 렌더링"""
        ...

    def _draw_edges(self, painter: QPainter, edges: list[GraphEdge],
                    row_positions: dict[str, int]) -> None:
        """
        간선 렌더링:
        - straight: 같은 lane 내 직선
        - merge_in: 다른 lane에서 들어오는 베지어 곡선
        - branch_out: 다른 lane으로 나가는 베지어 곡선
        """
        ...

    def _draw_nodes(self, painter: QPainter, nodes: list[GraphNode],
                    selected_hash: str | None) -> None:
        """
        노드 렌더링:
        - 일반 커밋: 채워진 원 (브랜치 컬러)
        - 머지 커밋: 더 큰 원 + 이중 테두리
        - 선택된 커밋: 글로우 효과
        - 브랜치 tip: 브랜치명 라벨 태그
        """
        ...

    def _draw_branch_labels(self, painter: QPainter,
                            node: GraphNode) -> None:
        """브랜치명 태그 (둥근 사각형 배지)"""
        ...

    def _bezier_curve(self, painter: QPainter,
                      start: QPoint, end: QPoint,
                      color: QColor) -> None:
        """QPainterPath를 이용한 베지어 곡선 (머지/분기 라인)"""
        ...
```

### 5.2 F-14: Diff 뷰어

#### `DiffParser` (domain/diff_parser.py)
```python
@dataclass
class DiffHunk:
    """하나의 diff hunk (@@로 시작하는 변경 블록)"""
    old_start: int           # 원본 시작 줄 번호
    old_count: int           # 원본 줄 수
    new_start: int           # 변경 후 시작 줄 번호
    new_count: int           # 변경 후 줄 수
    header: str              # @@ 헤더 전체 문자열
    lines: list["DiffLine"]  # 변경 라인 목록

@dataclass
class DiffLine:
    """diff의 한 줄"""
    type: str                # "add" | "delete" | "context" | "header"
    content: str             # 실제 내용
    old_line_no: int | None  # 원본 줄 번호 (삭제/컨텍스트)
    new_line_no: int | None  # 변경 후 줄 번호 (추가/컨텍스트)

@dataclass
class FileDiff:
    """하나의 파일에 대한 diff 결과"""
    old_path: str
    new_path: str
    status: str              # "modified" | "added" | "deleted" | "renamed"
    hunks: list[DiffHunk]
    is_binary: bool
    similarity: int | None   # rename 시 유사도 (%)


class DiffParser:
    """
    git diff 출력을 구조화된 객체로 파싱한다.

    지원 형식:
    - unified diff (git diff)
    - staged diff (git diff --cached)
    - commit diff (git diff <hash>~1 <hash>)
    - 파일 간 diff (git diff -- <path>)
    """

    def __init__(self, repository: "GitRepository"):
        self._repo = repository

    def parse_working_tree(self) -> list[FileDiff]:
        """워킹 트리 변경사항 파싱"""
        ...

    def parse_staged(self) -> list[FileDiff]:
        """스테이지된 변경사항 파싱"""
        ...

    def parse_commit(self, commit_hash: str) -> list[FileDiff]:
        """특정 커밋의 변경사항 파싱"""
        ...

    def parse_range(self, from_hash: str, to_hash: str) -> list[FileDiff]:
        """커밋 범위의 변경사항 파싱"""
        ...

    def _parse_unified_diff(self, raw_diff: str) -> list[FileDiff]:
        """unified diff 텍스트를 FileDiff 리스트로 변환"""
        ...
```

#### `DiffViewer` (ui/diff_viewer.py)
```python
class DiffViewer(QWidget):
    """
    파일 변경사항을 시각적으로 표시하는 위젯.

    모드:
    1. Inline (Unified): 단일 패널, 삭제=빨강 배경, 추가=초록 배경
    2. Side-by-Side: 좌=원본, 우=변경본, 동기 스크롤

    구조:
    ┌─────────────────────────────────────────┐
    │ [Inline ◉] [Side-by-Side ○]  📄 file.py │
    ├─────────────────────────────────────────┤
    │  10 │  10 │   def foo():                │
    │  11 │     │ - old_line = True   ← 빨강   │
    │     │  11 │ + new_line = False  ← 초록   │
    │  12 │  12 │   return result             │
    └─────────────────────────────────────────┘
    """

    class ViewMode(Enum):
        INLINE = "inline"
        SIDE_BY_SIDE = "side_by_side"

    def __init__(self, parent=None): ...
    def set_diff(self, file_diff: FileDiff) -> None: ...
    def set_view_mode(self, mode: ViewMode) -> None: ...
    def _render_inline(self, file_diff: FileDiff) -> None: ...
    def _render_side_by_side(self, file_diff: FileDiff) -> None: ...
```

#### `SyntaxHighlighter` (ui/syntax_highlighter.py)
```python
class SyntaxHighlighter(QSyntaxHighlighter):
    """
    Diff 뷰어 내 코드 구문 강조.

    지원 언어 (확장자 기반 자동 감지):
    - Python (.py)
    - Java (.java)
    - JavaScript/TypeScript (.js, .ts, .tsx)
    - SQL (.sql)
    - Shell (.sh, .bash)
    - YAML/JSON (.yml, .yaml, .json)
    - XML/HTML (.xml, .html)

    키워드, 문자열, 숫자, 주석, 함수명 등 토큰별 컬러링.
    """

    def __init__(self, document: QTextDocument, language: str = "python"): ...
    def highlightBlock(self, text: str) -> None: ...
    def _detect_language(self, file_path: str) -> str: ...
```

#### `DiffController` (controller/diff_controller.py)
```python
class DiffController(QObject):
    """
    Diff 관련 워크플로우를 조율한다.

    시그널:
    - diff_ready(list[FileDiff]): diff 파싱 완료
    - file_staged(str): 파일 스테이징 완료
    - file_unstaged(str): 파일 언스테이징 완료
    """

    diff_ready = pyqtSignal(list)
    file_staged = pyqtSignal(str)
    file_unstaged = pyqtSignal(str)

    def __init__(self, repository: "GitRepository"): ...
    def load_working_tree_diff(self) -> None: ...
    def load_staged_diff(self) -> None: ...
    def load_commit_diff(self, commit_hash: str) -> None: ...
    def stage_file(self, file_path: str) -> None: ...
    def unstage_file(self, file_path: str) -> None: ...
    def stage_hunk(self, file_path: str, hunk: DiffHunk) -> None: ...
    def discard_file(self, file_path: str) -> None: ...
```

### 5.3 F-15: Stash 관리

#### `StashManager` (domain/stash_manager.py)
```python
@dataclass
class StashEntry:
    """하나의 stash 항목"""
    index: int               # stash@{index}
    message: str             # stash 메시지
    branch: str              # stash 생성 시 브랜치
    date: datetime           # 생성 시간
    files_changed: int       # 변경된 파일 수


class StashManager:
    """
    Git stash 작업을 관리한다.
    """

    def __init__(self, repository: "GitRepository"):
        self._repo = repository

    def list_stashes(self) -> list[StashEntry]:
        """모든 stash 항목 조회"""
        ...

    def create_stash(self, message: str = "",
                     include_untracked: bool = True) -> StashEntry:
        """현재 변경사항을 stash로 저장"""
        ...

    def apply_stash(self, index: int = 0,
                    pop: bool = False) -> bool:
        """stash 적용 (apply 또는 pop)"""
        ...

    def drop_stash(self, index: int) -> bool:
        """stash 삭제"""
        ...

    def show_stash(self, index: int = 0) -> list["FileDiff"]:
        """stash 내용 미리보기 (diff 형태)"""
        ...
```

### 5.4 F-16: Apple Keychain 연동

#### `KeychainService` (infrastructure/keychain_service.py)
```python
class KeychainService:
    """
    macOS Keychain Services를 통해 자격증명과 앱 설정을 안전하게 관리한다.

    사용 기술:
    - subprocess로 `security` CLI 명령 실행
      (security add-generic-password, find-generic-password 등)
    - 서비스명 네임스페이스: "com.git-dashboard.{category}"

    보안 원칙:
    - 메모리에 자격증명을 장기 보관하지 않음
    - 필요 시에만 Keychain에서 읽고 즉시 사용
    - 앱 삭제 시 Keychain 항목 정리 옵션 제공
    """

    SERVICE_PREFIX = "com.git-dashboard"

    # 카테고리별 서비스명
    CATEGORY_GIT_CREDENTIAL = "git-credential"
    CATEGORY_APP_SETTINGS = "app-settings"

    def __init__(self): ...

    # ─── Git 자격증명 관리 ───

    def store_git_credential(self, remote_url: str,
                              username: str,
                              token: str) -> bool:
        """
        Git 리모트 자격증명을 Keychain에 저장.

        사용 예: AWS CodeCommit HTTPS 토큰, GitHub PAT
        서비스명: com.git-dashboard.git-credential.{remote_host}
        """
        ...

    def get_git_credential(self, remote_url: str) -> tuple[str, str] | None:
        """
        Keychain에서 Git 자격증명 조회.
        Returns: (username, token) 또는 None
        """
        ...

    def delete_git_credential(self, remote_url: str) -> bool:
        """Git 자격증명 삭제"""
        ...

    def list_git_credentials(self) -> list[dict]:
        """저장된 모든 Git 자격증명 목록 (토큰 마스킹)"""
        ...

    # ─── 앱 설정 보안 저장 ───

    def store_secure_setting(self, key: str, value: str) -> bool:
        """
        민감한 앱 설정을 Keychain에 저장.

        사용 예: Webhook URL, API 토큰, 암호화 키
        서비스명: com.git-dashboard.app-settings.{key}
        """
        ...

    def get_secure_setting(self, key: str) -> str | None:
        """Keychain에서 앱 설정 조회"""
        ...

    def delete_secure_setting(self, key: str) -> bool:
        """앱 설정 삭제"""
        ...

    # ─── Keychain 유틸리티 ───

    def cleanup_all(self) -> int:
        """앱 관련 모든 Keychain 항목 삭제 (앱 삭제 시)"""
        ...

    def _run_security_command(self, args: list[str]) -> "ScriptResult":
        """macOS security CLI 명령 실행"""
        ...
```

### 5.5 F-17: IntelliJ IDEA 연동

#### `IdeIntegrationService` (infrastructure/ide_integration_service.py)
```python
class IdeIntegrationService:
    """
    IntelliJ IDEA와의 양방향 통합을 관리한다.

    연동 방식:
    1. IDE → Dashboard: .git 디렉토리 감시(FileWatcherService)로
       IDE에서 수행한 커밋/푸시를 실시간 감지
    2. Dashboard → IDE: IntelliJ CLI(`idea`)를 통해
       프로젝트 열기, 터미널 명령 전달

    지원 IDE:
    - IntelliJ IDEA (Community / Ultimate)
    - WebStorm, PyCharm 등 JetBrains 계열 (동일 CLI 구조)
    """

    # JetBrains IDE CLI 탐색 경로 (macOS)
    IDE_SEARCH_PATHS = [
        "/usr/local/bin/idea",
        "/Applications/IntelliJ IDEA.app/Contents/MacOS/idea",
        "/Applications/IntelliJ IDEA CE.app/Contents/MacOS/idea",
        "~/Library/Application Support/JetBrains/Toolbox/scripts/idea",
    ]

    def __init__(self):
        self._ide_path: str | None = None
        self._discover_ide()

    def is_available(self) -> bool:
        """IntelliJ CLI가 사용 가능한지 확인"""
        ...

    def get_ide_info(self) -> dict:
        """IDE 이름, 버전, 경로 정보 반환"""
        ...

    # ─── Dashboard → IDE ───

    def open_project(self, project_path: str) -> bool:
        """IntelliJ에서 프로젝트 열기"""
        ...

    def open_file(self, file_path: str, line: int = 0) -> bool:
        """IntelliJ에서 특정 파일 열기 (줄 번호 지정 가능)"""
        ...

    def run_in_terminal(self, command: str,
                        project_path: str) -> bool:
        """
        IntelliJ 내장 터미널에서 명령 실행.

        활용 예:
        - 대시보드에서 선택한 스크립트를 IDE 터미널에서 실행
        - git 명령을 IDE 터미널로 전달

        구현: idea --command 'terminal:run:{command}'
        (또는 JetBrains REST API 활용)
        """
        ...

    # ─── IDE → Dashboard (감지) ───

    def setup_git_hooks(self, repo_path: str) -> bool:
        """
        post-commit, post-push 훅 설치.
        IDE에서 커밋/푸시 시 대시보드에 알림.

        훅 내용: 대시보드 프로세스에 시그널(USR1) 전송
        또는 로컬 소켓/파일 기반 IPC
        """
        ...

    def _discover_ide(self) -> None:
        """시스템에서 IntelliJ CLI 탐색"""
        ...
```

#### `FileWatcherService` (infrastructure/file_watcher_service.py)
```python
class FileWatcherService(QObject):
    """
    .git 디렉토리의 파일 변경을 감지하여
    IDE에서 수행한 Git 작업을 실시간으로 반영한다.

    감시 대상:
    - .git/refs/heads/*   → 브랜치 변경 감지
    - .git/HEAD           → 체크아웃 감지
    - .git/COMMIT_EDITMSG → 커밋 감지
    - .git/refs/stash     → stash 변경 감지
    - .git/MERGE_HEAD     → 머지 진행 감지
    - .git/REBASE_HEAD    → rebase 진행 감지

    사용 기술: QFileSystemWatcher (PyQt6 내장)
    """

    # 시그널
    commit_detected = pyqtSignal()          # 새 커밋 감지
    branch_changed = pyqtSignal(str)        # 브랜치 전환 감지
    push_detected = pyqtSignal()            # 푸시 감지
    stash_changed = pyqtSignal()            # stash 변경 감지
    merge_started = pyqtSignal()            # 머지 시작 감지
    rebase_started = pyqtSignal()           # rebase 시작 감지
    repository_changed = pyqtSignal()       # 일반적 저장소 변경

    def __init__(self, repo_path: str, parent=None):
        self._watcher = QFileSystemWatcher(parent=self)
        ...

    def start_watching(self) -> None:
        """감시 시작: 대상 파일/디렉토리 등록"""
        ...

    def stop_watching(self) -> None:
        """감시 중지"""
        ...

    def _on_file_changed(self, path: str) -> None:
        """파일 변경 이벤트 핸들러 — 변경 유형 분류 후 적절한 시그널 발출"""
        ...

    def _on_directory_changed(self, path: str) -> None:
        """디렉토리 변경 이벤트 핸들러"""
        ...

    def _debounce(self, signal, delay_ms: int = 500) -> None:
        """짧은 시간 내 중복 이벤트 필터링 (디바운스)"""
        ...
```

### 5.6 F-18: Interactive Rebase

#### `RebaseOrchestrator` (domain/rebase_orchestrator.py)
```python
@dataclass
class RebasePlan:
    """Interactive rebase 실행 계획"""
    base_commit: str         # rebase 기준 커밋
    steps: list["RebaseStep"]

@dataclass
class RebaseStep:
    """rebase의 각 단계"""
    action: str              # "pick" | "reword" | "squash" | "fixup" | "drop" | "edit"
    commit_hash: str
    original_message: str
    new_message: str | None  # reword/squash 시 새 메시지


class RebaseOrchestrator:
    """
    Interactive Rebase를 GUI에서 실행 가능하도록 관리한다.

    워크플로우:
    1. prepare(): 대상 커밋 범위를 분석하여 RebasePlan 초안 생성
    2. 사용자가 UI에서 plan 수정 (순서 변경, action 변경, 메시지 편집)
    3. execute(): 수정된 plan을 git rebase --interactive에 전달

    안전 장치:
    - 실행 전 현재 HEAD를 reflog로 기록
    - 실패 시 git rebase --abort 자동 실행
    - dirty working tree 시 실행 거부
    """

    def __init__(self, repository: "GitRepository"):
        self._repo = repository

    def prepare(self, onto: str = "HEAD~10") -> RebasePlan:
        """rebase 대상 커밋을 분석하여 plan 생성"""
        ...

    def execute(self, plan: RebasePlan) -> bool:
        """
        plan을 실행한다.

        구현: GIT_SEQUENCE_EDITOR 환경변수를 설정하여
        git rebase -i에 plan을 자동 전달.
        (에디터 대신 스크립트가 todo 파일을 덮어쓰는 방식)
        """
        ...

    def abort(self) -> bool:
        """진행 중인 rebase 중단"""
        ...

    def continue_rebase(self) -> bool:
        """충돌 해결 후 rebase 계속"""
        ...

    def get_rebase_status(self) -> dict | None:
        """현재 rebase 진행 상태 (진행 중이 아니면 None)"""
        ...

    def _generate_todo_script(self, plan: RebasePlan) -> str:
        """plan을 git-rebase-todo 형식 문자열로 변환"""
        ...
```

#### `RebaseDialog` (ui/rebase_dialog.py)
```python
class RebaseDialog(QDialog):
    """
    Interactive Rebase GUI.

    구조:
    ┌─────────────────────────────────────────────────┐
    │  Interactive Rebase onto: develop               │
    ├─────────────────────────────────────────────────┤
    │  Action  │  Hash   │  Message                   │
    │  [pick▾] │ a1b2c3  │ feat: add login       ↕   │
    │  [sqsh▾] │ d4e5f6  │ fix: login typo       ↕   │
    │  [pick▾] │ g7h8i9  │ feat: add dashboard   ↕   │
    │  [drop▾] │ j0k1l2  │ WIP: temp commit      ↕   │
    ├─────────────────────────────────────────────────┤
    │  [Cancel]                      [Start Rebase]   │
    └─────────────────────────────────────────────────┘

    - 각 행은 드래그앤드롭으로 순서 변경 가능
    - Action 컬럼: QComboBox (pick/reword/squash/fixup/drop)
    - reword 선택 시 메시지 편집 다이얼로그 팝업
    - squash 선택 시 결합될 커밋 시각적 그룹핑
    """

    rebase_requested = pyqtSignal(object)  # RebasePlan

    def __init__(self, plan: RebasePlan, parent=None): ...
    def _setup_drag_drop(self) -> None: ...
    def _on_action_changed(self, row: int, action: str) -> None: ...
    def _build_final_plan(self) -> RebasePlan: ...
```

### 5.7 F-19: Conflict 해결 도구

#### `ConflictResolver` (domain/conflict_resolver.py)
```python
@dataclass
class ConflictRegion:
    """하나의 충돌 영역"""
    start_line: int
    end_line: int
    base_content: list[str]     # BASE (공통 조상)
    ours_content: list[str]     # OURS (현재 브랜치)
    theirs_content: list[str]   # THEIRS (머지 대상 브랜치)

@dataclass
class ConflictFile:
    """충돌이 발생한 파일"""
    path: str
    conflicts: list[ConflictRegion]
    non_conflict_lines: list[tuple[int, int, str]]  # (start, end, content)
    total_conflicts: int


class ConflictResolver:
    """
    Git 머지 충돌을 파싱하고 해결을 지원한다.

    워크플로우:
    1. detect(): 충돌 파일 목록 조회
    2. parse(): 충돌 마커(<<<, ===, >>>)를 파싱하여 ConflictFile 생성
    3. resolve(): 사용자 선택(ours/theirs/manual)을 반영하여 파일 저장
    4. mark_resolved(): git add로 해결 완료 마킹
    """

    def __init__(self, repository: "GitRepository"):
        self._repo = repository

    def detect_conflicts(self) -> list[str]:
        """충돌 상태인 파일 경로 목록 반환"""
        ...

    def parse_conflict(self, file_path: str) -> ConflictFile:
        """
        충돌 파일을 파싱하여 ConflictFile 생성.

        파싱 대상 마커:
        <<<<<<< HEAD (또는 <<<<<<< ours_branch)
        ... ours content ...
        ||||||| base  (diff3 모드 시)
        ... base content ...
        =======
        ... theirs content ...
        >>>>>>> theirs_branch
        """
        ...

    def resolve_region(self, file_path: str,
                       region_index: int,
                       resolution: str,
                       manual_content: str | None = None) -> None:
        """
        충돌 영역 하나를 해결한다.

        resolution: "ours" | "theirs" | "both" | "manual"
        """
        ...

    def save_resolution(self, file_path: str,
                        resolved_content: str) -> None:
        """해결된 전체 내용으로 파일 저장"""
        ...

    def mark_resolved(self, file_path: str) -> None:
        """git add로 충돌 해결 완료 처리"""
        ...
```

#### `MergeEditor` (ui/merge_editor.py)
```python
class MergeEditor(QWidget):
    """
    3-Way Merge 에디터.

    구조:
    ┌──────────────────────────────────────────────────────────────┐
    │  Conflict Resolution: src/main/App.java  (3 conflicts)      │
    ├──────────────┬──────────────────┬────────────────────────────┤
    │   OURS       │   RESULT         │   THEIRS                  │
    │  (current)   │   (merged)       │   (incoming)              │
    ├──────────────┤                  ├────────────────────────────┤
    │  line 1      │  line 1          │  line 1                   │
    │  line 2  ◄── │  <<<CONFLICT>>>  │ ──► line 2'              │
    │              │  [Ours][Theirs]  │                           │
    │              │  [Both][Edit]    │                           │
    │  line 3      │  line 3          │  line 3                   │
    ├──────────────┴──────────────────┴────────────────────────────┤
    │  ◄ Prev Conflict    [2/3]    Next Conflict ►               │
    │  [Cancel]                            [Save & Mark Resolved] │
    └──────────────────────────────────────────────────────────────┘

    - 좌: OURS (현재 브랜치 내용)
    - 중: RESULT (최종 머지 결과, 편집 가능)
    - 우: THEIRS (머지 대상 브랜치 내용)
    - 충돌 영역에 [Ours] [Theirs] [Both] [Edit] 버튼
    - 세 패널 동기 스크롤
    - 충돌 영역 간 이전/다음 네비게이션
    """

    conflict_resolved = pyqtSignal(str)  # file_path

    def __init__(self, parent=None): ...
    def set_conflict(self, conflict_file: ConflictFile) -> None: ...
    def _navigate_conflict(self, direction: int) -> None: ...
    def _apply_resolution(self, region_index: int, choice: str) -> None: ...
    def _save_and_mark_resolved(self) -> None: ...
```

---

## 6. 데이터 모델 확장 (models.py 추가)

```python
# ─── v2.0 신규 모델 ───

@dataclass
class GraphNode:
    commit: Commit
    column: int
    color_index: int
    parents: list[str]
    children: list[str]
    is_merge: bool
    is_branch_tip: bool
    branch_name: str | None

@dataclass
class GraphEdge:
    parent_hash: str
    child_hash: str
    column_from: int
    column_to: int
    color_index: int
    edge_type: str  # "straight" | "merge_in" | "branch_out"

@dataclass
class GraphLayout:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    max_columns: int
    branch_colors: dict[int, str]

@dataclass
class DiffHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str
    lines: list["DiffLine"]

@dataclass
class DiffLine:
    type: str  # "add" | "delete" | "context" | "header"
    content: str
    old_line_no: int | None
    new_line_no: int | None

@dataclass
class FileDiff:
    old_path: str
    new_path: str
    status: str  # "modified" | "added" | "deleted" | "renamed"
    hunks: list[DiffHunk]
    is_binary: bool
    similarity: int | None

@dataclass
class StashEntry:
    index: int
    message: str
    branch: str
    date: datetime
    files_changed: int

@dataclass
class RebasePlan:
    base_commit: str
    steps: list["RebaseStep"]

@dataclass
class RebaseStep:
    action: str  # "pick" | "reword" | "squash" | "fixup" | "drop" | "edit"
    commit_hash: str
    original_message: str
    new_message: str | None

@dataclass
class ConflictRegion:
    start_line: int
    end_line: int
    base_content: list[str]
    ours_content: list[str]
    theirs_content: list[str]

@dataclass
class ConflictFile:
    path: str
    conflicts: list[ConflictRegion]
    non_conflict_lines: list[tuple[int, int, str]]
    total_conflicts: int
```

---

## 7. GitRepository API 확장

```python
class GitRepository:
    """v1.0 API 유지 + v2.0 신규 API 추가"""

    # ─── v2.0 신규 API ───

    # F-13: 커밋 그래프
    def get_commit_graph_data(self, limit: int = 200) -> list[dict]:
        """
        git log --topo-order --parents --decorate 결과를
        {hash, parents[], refs[]} 딕셔너리 리스트로 반환.
        CommitGraphBuilder에서 사용.
        """
        ...

    # F-14: Diff
    def get_diff_raw(self, args: list[str] = None) -> str:
        """git diff 명령의 raw 출력 반환 (DiffParser에서 파싱)"""
        ...

    def get_commit_diff_raw(self, commit_hash: str) -> str:
        """git show --format= --patch <hash> 출력 반환"""
        ...

    def stage_file(self, file_path: str) -> None:
        """git add <file>"""
        ...

    def unstage_file(self, file_path: str) -> None:
        """git restore --staged <file>"""
        ...

    def discard_changes(self, file_path: str) -> None:
        """git restore <file> (워킹 트리 변경 폐기)"""
        ...

    # F-15: Stash
    def stash_list(self) -> list[dict]:
        """git stash list --format=... 파싱 결과"""
        ...

    def stash_push(self, message: str = "",
                   include_untracked: bool = True) -> bool:
        """git stash push"""
        ...

    def stash_apply(self, index: int = 0) -> bool:
        """git stash apply stash@{index}"""
        ...

    def stash_pop(self, index: int = 0) -> bool:
        """git stash pop stash@{index}"""
        ...

    def stash_drop(self, index: int) -> bool:
        """git stash drop stash@{index}"""
        ...

    def stash_show(self, index: int = 0) -> str:
        """git stash show -p stash@{index} (diff 형태)"""
        ...

    # F-18: Rebase
    def get_rebase_commits(self, onto: str) -> list[dict]:
        """rebase 대상 커밋 목록"""
        ...

    def run_rebase_interactive(self, onto: str,
                                todo_script: str) -> bool:
        """GIT_SEQUENCE_EDITOR를 설정하여 non-interactive rebase 실행"""
        ...

    def rebase_abort(self) -> bool:
        """git rebase --abort"""
        ...

    def rebase_continue(self) -> bool:
        """git rebase --continue"""
        ...

    def is_rebasing(self) -> bool:
        """.git/rebase-merge 또는 .git/rebase-apply 존재 여부"""
        ...

    # F-19: Conflict
    def get_conflicted_files(self) -> list[str]:
        """git diff --name-only --diff-filter=U"""
        ...

    def read_file_content(self, file_path: str) -> str:
        """파일 내용 읽기 (충돌 마커 포함)"""
        ...

    def write_file_content(self, file_path: str,
                           content: str) -> None:
        """해결된 내용으로 파일 덮어쓰기"""
        ...

    def is_merging(self) -> bool:
        """.git/MERGE_HEAD 존재 여부"""
        ...
```

---

## 8. UI 레이아웃 v2.0

### 8.1 메인 윈도우 (확장)

```
┌──────────────────────────────────────────────────────────────────┐
│  🌿 Git Dashboard v2.0          [저장소: aipd ▾]  [🔑] [⚙]     │
├──────────┬───────────────────────────────────────────────────────┤
│          │  ┌─ Graph ─┬─ Changes ─┬─ Stash ─┬─ Rebase ─┐       │
│ REPOS    │  │                                           │       │
│ ● aipd   │  │  커밋 그래프 뷰 (CommitGraphView)          │       │
│ ○ comm.  │  │  ●─────●──── develop                      │       │
│ ○ citeas │  │  │     │                                   │       │
│          │  │  ●─┬───●──── feature/login                 │       │
│──────────│  │  │ │                                       │       │
│ BRANCHES │  │  ●─┘────── main                            │       │
│ develop  │  │                                            │       │
│ main     │  ├────────────────────────────────────────────┤       │
│ feature/ │  │  Diff Viewer / Commit Details               │       │
│  login   │  │  (선택된 커밋의 변경사항)                     │       │
│          │  └────────────────────────────────────────────┘       │
├──────────┴───────────────────────────────────────────────────────┤
│ ⎇ develop │ CLEAN │ ↑0 ↓0 │ IntelliJ: Connected │ 🔑 Keychain ✓│
└──────────────────────────────────────────────────────────────────┘
```

### 8.2 탭 구성

| 탭 | 내용 |
|-----|------|
| **Graph** | 커밋 그래프 (상단) + 커밋 상세/Diff (하단 스플릿) |
| **Changes** | Working Tree / Staged 파일 목록 + Diff 뷰어 |
| **Stash** | Stash 목록 + 미리보기 + 액션 버튼 |
| **Rebase** | Interactive Rebase 다이얼로그 진입점 |

### 8.3 Conflict 해결 모드

머지/리베이스 충돌 감지 시 자동으로 MergeEditor 모달 표시:

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️ Merge Conflict: src/App.java  (3 conflicts remaining)   │
├─────────────────┬─────────────────┬─────────────────────────┤
│ OURS (develop)  │ RESULT          │ THEIRS (feature/login)  │
│                 │                 │                         │
│ public void     │ public void     │ public void             │
│ login(User u) { │ ◀ CONFLICT 1 ▶ │ login(String name,      │
│   auth(u);      │ [Ours][Theirs]  │        String pass) {   │
│ }               │ [Both][Edit ✎]  │   validate(name, pass); │
│                 │                 │ }                       │
├─────────────────┴─────────────────┴─────────────────────────┤
│ ◄ Prev   [1/3]   Next ►      [Cancel]  [Save & Resolve ✓]  │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. 의존성 추가 (pyproject.toml)

```toml
[tool.poetry.dependencies]
python = "^3.11"
PyQt6 = "^6.6"
GitPython = "^3.1"
# rumps 제거 — QSystemTrayIcon으로 대체 완료 (v1.0)

# ─── v2.0 신규 의존성 ───
# (최소 의존성 원칙: 가능한 stdlib + PyQt6 내장 기능 활용)

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-cov = "^4.0"
black = "^24.0"
```

**v2.0 의존성 전략: 최소 추가 원칙**

| 기능 | 구현 방식 | 추가 라이브러리 |
|------|----------|----------------|
| 커밋 그래프 | QPainter (PyQt6 내장) | 없음 |
| Diff 뷰어 | QTextEdit + QSyntaxHighlighter (PyQt6 내장) | 없음 |
| Syntax Highlighting | QSyntaxHighlighter (PyQt6 내장) | 없음 |
| Stash 관리 | GitPython API | 없음 |
| Apple Keychain | `security` CLI (macOS 내장) via subprocess | 없음 |
| IntelliJ 연동 | `idea` CLI + QFileSystemWatcher (PyQt6 내장) | 없음 |
| Interactive Rebase | GIT_SEQUENCE_EDITOR + git CLI | 없음 |
| Conflict 해결 | QTextEdit 3-panel + git CLI | 없음 |
| 드래그앤드롭 | QListWidget DragDrop (PyQt6 내장) | 없음 |

→ **추가 pip 패키지 0개** — 기존 PyQt6 + GitPython만으로 모든 v2.0 기능 구현 가능.

---

## 10. 개발 일정 v2.0

### Phase 4: 시각화 고도화 (Week 5~6)

| 일차 | 작업 | 관련 기능 |
|------|------|----------|
| 21~22일 | CommitGraphBuilder 도메인 로직 + 테스트 | F-13 |
| 23~24일 | GraphRenderer QPainter 렌더링 엔진 | F-13 |
| 25일 | CommitGraphView 위젯 통합 + 스크롤/클릭 | F-13 |
| 26~27일 | DiffParser 도메인 로직 + 테스트 | F-14 |
| 28일 | SyntaxHighlighter 구현 | F-14 |
| 29~30일 | DiffViewer (인라인 + 사이드바이사이드) 구현 | F-14 |

### Phase 5: 외부 통합 (Week 7~8)

| 일차 | 작업 | 관련 기능 |
|------|------|----------|
| 31~32일 | KeychainService 구현 + 테스트 | F-16 |
| 33일 | KeychainSettingsPanel UI | F-16 |
| 34~35일 | StashManager + StashPanel | F-15 |
| 36~37일 | FileWatcherService + IdeIntegrationService | F-17 |
| 38~39일 | IdeBridgePanel UI + 실시간 감지 통합 | F-17 |
| 40일 | 통합 테스트 + UI 다듬기 | 전체 |

### Phase 6: 고급 Git 기능 (Week 9~10)

| 일차 | 작업 | 관련 기능 |
|------|------|----------|
| 41~42일 | RebaseOrchestrator 도메인 로직 + 테스트 | F-18 |
| 43~44일 | RebaseDialog UI (드래그앤드롭) | F-18 |
| 45~46일 | ConflictResolver 도메인 로직 + 테스트 | F-19 |
| 47~48일 | MergeEditor 3-way UI | F-19 |
| 49일 | MainWindow 탭 통합 + 전체 워크플로우 연결 | 전체 |
| 50일 | 최종 테스트, QSS 스타일 업데이트, 문서화 | 전체 |

---

## 11. WorkflowController 확장

```python
class WorkflowController(QObject):
    """v1.0 시그널 유지 + v2.0 시그널 추가"""

    # ─── v1.0 시그널 (유지) ───
    branch_summary_ready = pyqtSignal(object)
    sync_finished = pyqtSignal(object)
    branch_created = pyqtSignal(object)
    pr_check_ready = pyqtSignal(object)
    hook_result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)
    task_running = pyqtSignal(bool)

    # ─── v2.0 신규 시그널 ───
    graph_ready = pyqtSignal(object)           # GraphLayout
    stash_list_ready = pyqtSignal(list)         # list[StashEntry]
    diff_ready = pyqtSignal(list)               # list[FileDiff]
    rebase_status_changed = pyqtSignal(dict)    # rebase 진행 상태
    conflict_detected = pyqtSignal(list)        # list[str] (충돌 파일)
    ide_event = pyqtSignal(str)                 # IDE 이벤트 타입
    keychain_status = pyqtSignal(bool)          # Keychain 연결 상태

    # ─── v2.0 신규 API ───
    def load_commit_graph(self, limit: int = 200) -> None: ...
    def load_stash_list(self) -> None: ...
    def create_stash(self, message: str) -> None: ...
    def apply_stash(self, index: int, pop: bool = False) -> None: ...
    def drop_stash(self, index: int) -> None: ...
    def load_diff(self, mode: str = "working") -> None: ...
    def load_commit_diff(self, commit_hash: str) -> None: ...
    def stage_file(self, path: str) -> None: ...
    def unstage_file(self, path: str) -> None: ...
    def start_rebase(self, plan: RebasePlan) -> None: ...
    def abort_rebase(self) -> None: ...
    def open_merge_editor(self, file_path: str) -> None: ...
    def resolve_conflict(self, file_path: str, content: str) -> None: ...
    def setup_ide_integration(self) -> None: ...
    def check_keychain_status(self) -> None: ...
```

---

## 12. 비기능 요구사항 v2.0

| 항목 | v1.0 목표 | v2.0 목표 |
|------|----------|----------|
| UI 응답성 | Git 작업 중 블로킹 없음 | 동일 + 그래프 200커밋 렌더링 <500ms |
| 초기 로딩 | 3초 이내 | 동일 (그래프는 lazy loading) |
| 메모리 | 특별 제한 없음 | 그래프 데이터 500커밋 이하 캐싱 |
| Diff 성능 | N/A | 10,000줄 diff 파일 렌더링 <1초 |
| Keychain 보안 | N/A | 자격증명 메모리 잔류 시간 최소화 |
| IDE 감지 | N/A | .git 변경 감지 → UI 반영 <2초 |
| 안정성 | 에러 메시지, 크래시 없음 | 동일 + rebase/merge 실패 시 자동 복구 |

---

## 13. 리스크 & 대응 v2.0

| 리스크 | 가능성 | 대응 |
|--------|--------|------|
| QPainter 그래프 성능 (대량 커밋) | 중간 | Viewport culling — 보이는 영역만 렌더링, 가상 스크롤 |
| Interactive Rebase 데이터 손실 | 높음 | 실행 전 현재 HEAD reflog 기록, 실패 시 자동 abort, dirty tree 시 거부 |
| Keychain 접근 권한 | 중간 | 최초 접근 시 macOS 팝업 허용 안내, 권한 없을 시 ConfigStore fallback |
| IntelliJ CLI 경로 다양성 | 중간 | 여러 경로 탐색 + 사용자 수동 설정 옵션 |
| QFileSystemWatcher 이벤트 폭주 | 높음 | 500ms 디바운스 + 배치 처리 |
| 3-way merge 복잡한 충돌 | 중간 | diff3 모드 지원, 수동 편집 항상 허용, 외부 머지 도구 연동 옵션 |
| Rebase 중 추가 충돌 | 높음 | 충돌 발생 시 MergeEditor 자동 팝업, continue/abort 명확한 UI |

---

## 14. 마이그레이션 가이드 (v1.0 → v2.0)

### 14.1 하위 호환성
- v1.0의 모든 UI 컴포넌트와 기능은 **그대로 유지**
- `~/.git-dashboard/config.json` 형식 변경 없음
- 기존 tests 100% 통과 유지

### 14.2 MainWindow 변경 사항
- DashboardPanel → **탭 기반**으로 확장 (기존 Dashboard는 첫 번째 탭으로 유지)
- CommitGraphView가 메인 그래프 탭에 위치
- 상태바에 IDE 연결 상태, Keychain 상태 표시 추가

### 14.3 코드 변경 영향도

| 기존 파일 | 변경 수준 | 내용 |
|----------|----------|------|
| main.py | 소규모 | FileWatcherService 초기화 추가 |
| main_window.py | 중규모 | 탭 위젯 추가, 상태바 확장 |
| workflow_controller.py | 중규모 | v2.0 시그널/API 추가 |
| git_repository.py | 중규모 | v2.0 Git API 메서드 추가 |
| models.py | 소규모 | v2.0 dataclass 추가 |
| dark_theme.qss | 소규모 | 신규 위젯 스타일 추가 |
| 기타 v1.0 파일 | 없음 | 변경 없음 |

---

*다음 단계: Phase 4 (커밋 그래프 + Diff 뷰어) 구현 시작*
