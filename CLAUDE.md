# Git Dashboard — Project CLAUDE.md
# Python 3.11+ / PyQt6 / macOS

> 설계 문서 v1.0: `git-dashboard-design.md`
> 설계 문서 v2.0: `git-dashboard-design-v2.md`
> 업데이트: 2026-03-31

---

## 1. 프로젝트 컨텍스트

| 항목 | 내용 |
|------|------|
| 목적 | Git 워크플로우 GUI 대시보드 (macOS 전용) — SourceTree 수준 시각화 + IDE 연동 |
| 스택 | Python 3.11+, PyQt6, GitPython |
| 패키징 | Poetry (`pyproject.toml`) |
| 배포 | PyInstaller → `.app` 번들 |
| Git 호스팅 | AWS CodeCommit |
| 브랜치 전략 | `develop → release/* → main` |
| IDE 연동 | IntelliJ IDEA (JetBrains 계열) |
| 인증 | macOS Keychain Services |

---

## 2. 기본 에이전트

| 상황 | 에이전트 |
|------|---------|
| PyQt6 위젯 구현 / QSS 스타일 / Design System | `pyqt-desktop-dev` ← **기본** |
| Git 도메인 로직 / 비즈니스 로직 / 데이터 처리 | `python-pro` |
| 코드 분석 / 리뷰 / 보안 검토 | `python-analyzer` |

### pyqt-desktop-dev 에이전트 (프로젝트 전용)

`~/.claude/agents/pyqt-desktop-dev.md` — PyQt6 macOS 데스크탑 앱 전문가.

- Design System 토큰 (`C`, `T`, `S`, `QSS`) 완전 숙지
- 4-Layer 아키텍처 원칙 강제
- QThread/GitWorker 비동기 패턴
- macOS 최적화 (Retina, Keychain, PyInstaller)
- 금지 폰트 목록 인지: `-apple-system`, `SF Pro`, `SF Mono`, `Fira Code`, `monospace`

---

## 3. 아키텍처 원칙 (설계 문서 준수)

- **4-Layer**: Infrastructure → Domain → Application → Presentation
- **파일 = 클래스**: 1 파일 1 클래스, 단일 책임
- **Worker Thread**: Git 작업은 반드시 `QThread`로 분리 (UI 블로킹 금지)
- **Signal/Slot**: 레이어 간 통신은 PyQt6 시그널 사용
- **Script Runner 패턴**: 기존 쉘 스크립트는 재작성 없이 subprocess로 래핑
- **Custom Painting 분리** (v2): QPainter 로직은 별도 Renderer 클래스로 분리
- **Parser 패턴** (v2): Git 출력(diff, merge conflict)은 전용 Parser 클래스로 파싱
- **Service 패턴** (v2): 외부 시스템 연동(Keychain, IDE)은 Infrastructure Service로 캡슐화

---

## 4. 개발 환경

```bash
# 의존성 설치
poetry install

# 실행
poetry run python main.py

# 테스트
poetry run pytest tests/ -v

# 포매터
poetry run black .
```

---

## 5. 주요 의존성

```toml
[tool.poetry.dependencies]
python = "^3.11"
PyQt6 = "^6.6"
GitPython = "^3.1"
# v2.0: 추가 패키지 없음 (PyQt6 내장 기능 + subprocess 활용)

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-cov = "^4.0"
black = "^24.0"
```

---

## 6. 파일 구조 (v2.0 기준)

```
git-dashboard/
├── main.py
├── pyproject.toml
├── app/
│   ├── ui/              # Presentation Layer
│   │   ├── (v1 위젯)    # main_window, dashboard_panel, repo_sidebar 등
│   │   ├── commit_graph_view.py    # F-13: 커밋 그래프 뷰
│   │   ├── graph_renderer.py       # F-13: QPainter 렌더링 엔진
│   │   ├── diff_viewer.py          # F-14: Diff 뷰어
│   │   ├── syntax_highlighter.py   # F-14: 구문 강조
│   │   ├── stash_panel.py          # F-15: Stash 관리
│   │   ├── rebase_dialog.py        # F-18: Interactive Rebase
│   │   ├── merge_editor.py         # F-19: 3-way Merge 에디터
│   │   ├── keychain_settings.py    # F-16: Keychain 설정
│   │   └── ide_panel.py            # F-17: IDE 연동
│   ├── controller/      # Application Layer
│   │   ├── (v1 컨트롤러) # workflow_controller, git_worker
│   │   ├── diff_controller.py      # F-14
│   │   ├── rebase_controller.py    # F-18
│   │   └── merge_controller.py     # F-19
│   ├── domain/          # Domain Layer
│   │   ├── (v1 도메인)   # models, branch_manager, pr_checker
│   │   ├── commit_graph_builder.py # F-13: DAG 토폴로지 계산
│   │   ├── diff_parser.py          # F-14: diff 파싱
│   │   ├── stash_manager.py        # F-15: stash CRUD
│   │   ├── rebase_orchestrator.py  # F-18: rebase 계획/실행
│   │   └── conflict_resolver.py    # F-19: 충돌 해결
│   └── infrastructure/  # Infrastructure Layer
│       ├── (v1 인프라)   # git_repository, config_store, script_runner
│       ├── keychain_service.py        # F-16: macOS Keychain
│       ├── ide_integration_service.py # F-17: IntelliJ 연동
│       └── file_watcher_service.py    # F-17: .git 변경 감지
├── scripts/         # 기존 쉘 스크립트 (수정 금지)
├── resources/       # icons, QSS 스타일
└── tests/
```

---

## 7. 개발 단계

| Phase | 기능 | ID | 상태 |
|-------|------|-----|------|
| Week 1 | 브랜치 상태, 커밋 로그, 동기화 | F-01~F-04 | ✅ 완료 |
| Week 2 | ScriptRunner, 워크플로우 UI | F-05~F-07 | ✅ 완료 |
| Week 3 | PR 체커, 메뉴바 상주 | F-05, F-08 | ✅ 완료 |
| Week 4 | 다중 저장소, 알림, 패키징 | F-09~F-12 | ✅ 완료 |
| **Week 5~6** | **커밋 그래프, Diff 뷰어, Stash** | **F-13~F-15** | 🔲 v2.0 |
| **Week 7~8** | **Keychain, IDE 연동** | **F-16~F-17** | 🔲 v2.0 |
| **Week 9~10** | **Interactive Rebase, Conflict 해결** | **F-18~F-19** | 🔲 v2.0 |

---

## 8. 주의 사항

- AWS CodeCommit 인증: 로컬 git credential 그대로 사용 (앱에서 별도 인증 불필요)
- `scripts/` 폴더 내 쉘 스크립트 **직접 수정 금지** (ScriptRunner로 래핑만)
- PyInstaller 패키징: 초기부터 빌드 테스트 필수
- **QPainter 그래프 성능**: Viewport culling 필수 (보이는 영역만 렌더링)
- **Interactive Rebase 안전장치**: 실행 전 reflog 기록, 실패 시 자동 abort
- **Keychain 접근**: 최초 접근 시 macOS 권한 팝업 처리, fallback to ConfigStore
- **FileWatcherService**: 500ms 디바운스로 이벤트 폭주 방지

---

## 9. Skill Auto-Triggers (이 프로젝트 전용)

| 상황 | 실행 |
|------|------|
| PyQt6 위젯 구현 / QSS 스타일 | `pyqt-desktop-dev` |
| Git 도메인 로직 / 데이터 처리 | `python-pro` |
| 코드 리뷰 요청 | `python-analyzer` |
| 테스트 작성/반복 | `/test-iterate` |
| Gap 분석 | `/pdca analyze git-dashboard-commit-workflow` |
| 완료 보고 | `/pdca report git-dashboard-commit-workflow` |
