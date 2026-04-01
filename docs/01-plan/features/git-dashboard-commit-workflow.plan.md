# Plan: git-dashboard-commit-workflow

## Executive Summary

| 관점 | 내용 |
|------|------|
| **Problem** | 현재 앱은 뷰어 수준 — diff/graph만 볼 수 있고 실제 git 작업(Stage, Commit, Push) 불가 |
| **Solution** | SourceTree 수준의 Commit Workflow Panel + Push/Pull 툴바 + Branch Switch 기능 구현 |
| **Function UX Effect** | 앱을 벗어나지 않고 전체 Git 워크플로우(Stage → Commit → Push)를 완결 |
| **Core Value** | Git Dashboard가 뷰어에서 완전한 Git 클라이언트로 격상 |

---

## 1. 배경 및 목표

| 항목 | 내용 |
|------|------|
| Feature | git-dashboard-commit-workflow |
| 작성일 | 2026-04-01 |
| 대상 앱 | Git Dashboard v2.0 (Python/PyQt6/macOS) |
| 참조 | CLAUDE.md 아키텍처 원칙, SourceTree UX 패턴 |

**현재 상태**: Diff 탭은 변경사항을 보여주지만 Stage/Commit/Push가 불가능  
**목표 상태**: SourceTree처럼 Stage → Commit → Push 전체 플로우를 앱 내에서 완결

---

## 2. 기능 범위 (MoSCoW)

### Must Have
- **F-20** Commit Workflow Panel
  - Unstaged / Staged 파일 목록 (2-section)
  - 파일 클릭 시 Diff 미리보기
  - Stage / Unstage (개별 파일)
  - Stage All / Unstage All
  - Commit message 입력 + Commit 버튼
  - Amend 체크박스 (마지막 커밋 수정)

- **F-21** Push / Pull / Fetch 툴바 버튼
  - 툴바에 Push / Pull / Fetch 버튼 추가
  - 결과 상태바 표시 (성공/실패/브랜치 정보)

### Should Have
- **F-22** Branch Switch
  - 개요 탭 또는 commit graph에서 브랜치 더블클릭 → checkout
  - 새 브랜치 생성 다이얼로그 (이름 입력 + base branch 선택)

### Could Have
- **F-23** Discard Changes
  - Unstaged 파일 우클릭 → "변경사항 되돌리기" (git checkout -- \<file\>)
- **F-24** 파일별 Hunk Stage
  - diff 뷰에서 hunk 단위로 staging (고급)

### Won't Have (v3 이후)
- Merge conflict 자동 해결 (이미 별도 탭 존재)
- Rebase GUI (이미 별도 탭 존재)
- Remote 관리 (add/remove remote)

---

## 3. 구현 계획

### F-20: Commit Workflow Panel

#### UI 레이아웃
```
┌─────────────────────────────────────────────────────────┐
│  [↻ 새로고침]                                            │
├─────────────────────┬───────────────────────────────────┤
│ Unstaged (3)  [⬆모두]│                                   │
│ ├─ M chat_svc.py ⬆ │      Diff Viewer                   │
│ ├─ M README.md   ⬆ │   (선택 파일의 변경사항)             │
│ ├─ A new_file.py ⬆ │                                   │
│─────────────────────│                                   │
│ Staged (1)    [⬇모두]│                                   │
│ └─ M config.py   ⬇ │                                   │
├─────────────────────┴───────────────────────────────────┤
│ [□ Amend]  메시지: [____________________________]  [Commit] │
└─────────────────────────────────────────────────────────┘
```

#### 필요 GitRepository 메서드 추가
```python
def get_working_tree_status(self) -> list[dict]:
    # [{"path": "...", "staged": bool, "status": "M/A/D/R/?"}]

def stage_file(self, path: str) -> bool:
    # git add <path>

def unstage_file(self, path: str) -> bool:
    # git reset HEAD <path>

def stage_all(self) -> bool:
    # git add -A

def unstage_all(self) -> bool:
    # git reset HEAD

def commit(self, message: str, amend: bool = False) -> bool:
    # git commit -m <message> [--amend]
```

#### 새 파일
- `app/ui/commit_panel.py` — CommitPanel 위젯
- `app/domain/staging_manager.py` — Stage/Unstage/Commit 도메인 로직

### F-21: Push/Pull/Fetch 툴바

#### 툴바 버튼 추가 (main_window.py)
```
[Git Dashboard]  ···  [↑ Push] [↓ Pull] [⟳ Fetch]  [⊞ 저장소 관리]
```

#### 필요 GitRepository 메서드 추가
```python
def push(self, remote: str = "origin", branch: str | None = None) -> tuple[bool, str]:
    # git push <remote> <branch>, returns (success, message)
```

### F-22: Branch Switch

#### 브랜치 목록 → 더블클릭 Checkout
- Dashboard 탭의 브랜치 섹션에 더블클릭 이벤트 연결
- `checkout_branch()` 이미 존재 → UI 연결만 필요

---

## 4. 의존성

### 기존 메서드 (수정 불필요)
- `checkout_branch()` — 브랜치 전환
- `fetch()` — git fetch
- `pull()` — git pull
- `get_raw_diff()` — diff 텍스트
- `get_status()` — dirty 여부

### 신규 메서드 필요
- `get_working_tree_status()` — 파일별 stage 상태
- `stage_file()` / `unstage_file()`
- `stage_all()` / `unstage_all()`
- `commit()` — 커밋 실행
- `push()` — 푸시 실행

---

## 5. 구현 순서

| 순서 | 작업 | 예상 시간 |
|------|------|---------|
| 1 | GitRepository 신규 메서드 추가 | 30분 |
| 2 | StagingManager 도메인 클래스 | 20분 |
| 3 | CommitPanel UI 위젯 | 60분 |
| 4 | 기존 Diff 탭을 CommitPanel로 교체 | 20분 |
| 5 | Push/Pull/Fetch 툴바 버튼 추가 | 20분 |
| 6 | Branch Switch UI 연결 | 20분 |

---

## 6. 위험 요소

| 위험 | 대응 |
|------|------|
| Push 인증 실패 (HTTPS) | 오류 메시지를 상태바/다이얼로그로 명확히 표시 |
| Commit 후 그래프/상태 미갱신 | Commit 성공 시 refresh_branch_summary() + 그래프 재로드 |
| Amend 시 history 오염 | Amend는 local-only 경고 표시 |
| 빈 메시지 커밋 시도 | Commit 버튼 disabled (메시지 없으면) |
