# Gap Analysis: git-dashboard-commit-workflow

> Date: 2026-04-01
> Target: F-20 ~ F-23 (CommitPanel, Push/Pull/Fetch, Branch Switch, Discard)

## Overall Score

| Category | Score | Status |
|----------|:-----:|:------:|
| Design Match | 87% | ⚠️ |
| Architecture Compliance | 85% | ⚠️ |
| Convention Compliance | 95% | ✅ |
| **Overall Match Rate** | **89%** | **⚠️ (threshold: 90%)** |

---

## 🔴 Missing (Plan O / Implementation X)

| # | Item | Plan Reference | Description |
|---|------|---------------|-------------|
| 1 | **F-22 Branch double-click checkout** | Section 3 line 122 | `dashboard_panel.py` 브랜치 목록에 `itemDoubleClicked` → `checkout_branch()` 미연결 |
| 2 | **F-22 New Branch Dialog** | Section 2 line 46 | 브랜치 생성 다이얼로그 미구현 (이름 입력 + base branch 선택) |
| 3 | **StagingManager domain class** | Section 3 line 104 | `app/domain/staging_manager.py` 미생성; CommitPanel이 Infrastructure 직접 의존 |

## 🟡 Added (Plan X / Implementation O)

| # | Item | Location |
|---|------|----------|
| 1 | `discard_file()` (F-23 구현) | `git_repository.py:420` |
| 2 | Staged 파일 우클릭 컨텍스트 메뉴 | `commit_panel.py:312` |
| 3 | `committed` pyqtSignal (post-commit refresh) | `commit_panel.py:66` |
| 4 | Design System (`design_system.py`) | `app/ui/design_system.py` |

## 🔵 Changed (Plan ≠ Implementation)

| # | Item | Plan | Implementation | Impact |
|---|------|------|----------------|--------|
| 1 | `commit()` return type | `-> bool` | `-> tuple[bool, str]` | Low — 오류 메시지 표시 가능 |
| 2 | 파일 목록 순서 | Unstaged 상단 | Staged 상단 (SourceTree 컨벤션) | Low |
| 3 | 파일별 Stage/Unstage UX | 인라인 버튼 | 우클릭 컨텍스트 메뉴만 | Medium — 발견성 낮음 |

## 🏗️ Architecture Issues

| # | File:Line | Issue | Severity |
|---|-----------|-------|----------|
| 1 | `commit_panel.py:329` | `self._repo._repo.git.log(...)` — UI가 Infrastructure 내부 `_repo` 직접 접근 (캡슐화 위반) | Medium |
| 2 | `commit_panel.py:70` | CommitPanel(Presentation) → GitRepository(Infrastructure) 직접 의존, StagingManager(Domain) 미경유 | Medium |
| 3 | `commit_panel.py:106` | Splitter handle 색상 `"#1e1e38"` 하드코딩 (Design System `C.BORDER_SUBTLE` 미사용) | Low |

---

## 90% 달성을 위한 즉시 수정 항목

### Fix 1: F-22 Branch double-click 연결
```python
# dashboard_panel.py — _local_list에 추가
self._local_list.itemDoubleClicked.connect(self._on_branch_checkout)

def _on_branch_checkout(self, item):
    branch = item.text().strip()
    self._controller.get_repository().checkout_branch(branch)
    self._controller.refresh_branch_summary()
```

### Fix 2: GitRepository 캡슐화 — get_last_commit_message() 추가
```python
# git_repository.py
def get_last_commit_message(self) -> str:
    try:
        return self._repo.git.log("-1", "--format=%s%n%n%b").strip()
    except Exception:
        return ""

# commit_panel.py:329 수정
last_msg = self._repo.get_last_commit_message()
```

### Fix 3: Splitter 하드코딩 색상 교체
```python
# commit_panel.py:106
splitter.setStyleSheet(f"QSplitter::handle{{background:{C.BORDER_SUBTLE};}}")
```

---

## 예상 수정 후 Match Rate

| 수정 | 예상 Match Rate |
|------|----------------|
| Fix 2 + Fix 3 만 적용 | ~91% ✅ |
| Fix 1 + 2 + 3 모두 적용 | ~94% ✅ |

---

## Next Step

```bash
/pdca iterate git-dashboard-commit-workflow   # 자동 수정
# 또는 수동으로 위 Fix 1~3 적용 후
/pdca report git-dashboard-commit-workflow
```
