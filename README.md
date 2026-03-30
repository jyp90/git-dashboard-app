# Git Dashboard v1.0

macOS 전용 Git 워크플로우 GUI 대시보드.

터미널 없이 브랜치 상태 확인, 원클릭 동기화, PR 체크, Release/Hotfix 워크플로우를 관리합니다.

## 기능

| 기능 | 설명 |
|------|------|
| 브랜치 상태 시각화 | 현재 브랜치, ahead/behind, dirty 상태 실시간 표시 |
| 원클릭 동기화 | origin/develop fetch → pull 원클릭 처리 |
| 커밋 로그 | 최근 커밋 목록 (hash, 메시지, 작성자, 날짜) |
| PR 품질 체크 | 커밋 컨벤션, 변경 파일 수, TODO 잔존 검사 |
| Release 워크플로우 | `release/*` 브랜치 생성 |
| Hotfix 워크플로우 | `hotfix/*` 브랜치 생성 |
| 다중 저장소 관리 | 여러 프로젝트 사이드바에서 전환 |
| Pre-push Hook 시각화 | `.git/hooks/pre-push` 실행 결과 확인 |
| macOS 알림 | 브랜치 뒤처짐·충돌 위험 시 시스템 알림 |
| 메뉴바 상주 | 시스템 트레이 아이콘으로 상태 표시 및 빠른 액션 |

## 스택

- **Python 3.11+** / **PyQt6** / **GitPython**
- 4-Layer 아키텍처 (Infrastructure → Domain → Application → Presentation)
- Poetry 패키지 관리

## 설치

### DMG (권장)

1. [GitDashboard-0.1.0.dmg](./dist/GitDashboard-0.1.0.dmg) 다운로드
2. DMG 마운트 후 `Git Dashboard.app`을 `Applications` 폴더로 드래그

### 소스 빌드

```bash
# 의존성 설치
pip install poetry
poetry install

# 실행
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
make test    # 테스트 실행 (49개)
make clean   # 빌드 산출물 정리
```

## 프로젝트 구조

```
app/
├── infrastructure/   # GitRepository, ConfigStore, ScriptRunner
├── domain/          # BranchManager, PrChecker, Models
├── controller/      # GitWorker (QThread), WorkflowController
└── ui/              # MainWindow, DashboardPanel, RepoSidebar, MenuBarApp
tests/               # 49개 테스트 (100% 통과)
resources/styles/    # dark_theme.qss
git_dashboard.spec   # PyInstaller 빌드 스펙
```

## 요구 사항

- macOS 13 Ventura 이상
- Git 설치
- AWS CodeCommit 등 Git 호스팅 인증 설정 완료

## 설계 문서

- [`git-dashboard-design.md`](./git-dashboard-design.md) — 전체 설계
