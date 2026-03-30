# Git Dashboard — Project CLAUDE.md
# Python 3.11+ / PyQt6 / macOS

> 설계 문서: `git-dashboard-design.md`
> 업데이트: 2026-03-30

---

## 1. 프로젝트 컨텍스트

| 항목 | 내용 |
|------|------|
| 목적 | Git 워크플로우 GUI 대시보드 (macOS 전용) |
| 스택 | Python 3.11+, PyQt6, rumps, GitPython |
| 패키징 | Poetry (`pyproject.toml`) |
| 배포 | PyInstaller → `.app` 번들 |
| Git 호스팅 | AWS CodeCommit |
| 브랜치 전략 | `develop → release/* → main` |

---

## 2. 기본 에이전트

Python 파일(`*.py`, `pyproject.toml`) 감지 시 → `python-pro` 사용
코드 분석/리뷰 요청 시 → `python-analyzer` 사용

---

## 3. 아키텍처 원칙 (설계 문서 준수)

- **4-Layer**: Infrastructure → Domain → Application → Presentation
- **파일 = 클래스**: 1 파일 1 클래스, 단일 책임
- **Worker Thread**: Git 작업은 반드시 `QThread`로 분리 (UI 블로킹 금지)
- **Signal/Slot**: 레이어 간 통신은 PyQt6 시그널 사용
- **Script Runner 패턴**: 기존 쉘 스크립트는 재작성 없이 subprocess로 래핑

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
rumps = "^0.4"
GitPython = "^3.1"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
black = "^24.0"
```

---

## 6. 파일 구조 (설계 문서 기준)

```
git-dashboard/
├── main.py
├── pyproject.toml
├── app/
│   ├── ui/          # Presentation Layer (PyQt6 Widgets)
│   ├── controller/  # Application Layer (WorkflowController, GitWorker)
│   ├── domain/      # Domain Layer (BranchManager, PrChecker 등)
│   └── infrastructure/  # Infrastructure Layer (GitRepository, ScriptRunner, ConfigStore)
├── scripts/         # 기존 쉘 스크립트 (수정 금지)
├── resources/       # icons, QSS 스타일
└── tests/
```

---

## 7. 개발 단계 (MVP 우선)

| Phase | 기능 | ID |
|-------|------|-----|
| Week 1 | 브랜치 상태, 커밋 로그, 동기화 | F-01~F-04 |
| Week 2 | ScriptRunner, 워크플로우 UI | F-05~F-07 |
| Week 3 | PR 체커, 메뉴바 상주 | F-05, F-08 |
| Week 4 | 다중 저장소, 알림, 패키징 | F-09~F-12 |

---

## 8. 주의 사항

- `rumps` + `PyQt6` 동시 실행 시 이벤트 루프 충돌 위험 → **SystemTray 대체 검토**
- AWS CodeCommit 인증: 로컬 git credential 그대로 사용 (앱에서 별도 인증 불필요)
- `scripts/` 폴더 내 쉘 스크립트 **직접 수정 금지** (ScriptRunner로 래핑만)
- PyInstaller 패키징: 초기부터 빌드 테스트 필수

---

## 9. Skill Auto-Triggers (이 프로젝트 전용)

| 상황 | 실행 |
|------|------|
| PyQt6 위젯 구현 | `python-pro` |
| Git 도메인 로직 | `python-pro` |
| 코드 리뷰 요청 | `python-analyzer` |
| 테스트 작성/반복 | `/test-iterate` |
| Gap 분석 | `/pdca analyze git-dashboard` |
| 완료 보고 | `/pdca report git-dashboard` |
