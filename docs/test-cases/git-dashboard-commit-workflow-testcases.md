# TestCase: git-dashboard-commit-workflow

> Created: 2026-04-01
> Target: app/ui/commit_panel.py, app/infrastructure/git_repository.py, app/ui/main_window.py
> Total cases: 12

---

## TC List

| TC# | Category | Test Item | Execution | Expected | Result | Iteration |
|-----|---------|------------|---------|----------|------|------|
| TC-001 | Functional | 문법 검사 — commit_panel.py | `py_compile` | 오류 없음 | ✅ | 1 |
| TC-002 | Functional | 문법 검사 — git_repository.py | `py_compile` | 오류 없음 | ✅ | 1 |
| TC-003 | Functional | 문법 검사 — main_window.py | `py_compile` | 오류 없음 | ✅ | 1 |
| TC-004 | Functional | get_working_tree_status() 정상 동작 | python 스크립트 | list[dict] 반환, 2개 파일 | ✅ | 1 |
| TC-005 | Functional | stage_file() / unstage_file() | 임시 git 저장소 | True 반환, 상태 변경 확인 | ✅ | 1 |
| TC-006 | Functional | stage_all() / unstage_all() | 임시 git 저장소 | True 반환 | ✅ | 1 |
| TC-007 | Functional | commit() 정상 커밋 | 임시 git 저장소 | (True, msg) 반환 | ✅ | 1 |
| TC-008 | Boundary | commit() 빈 메시지 거부 | commit("") | (False, "커밋 메시지를 입력하세요.") | ✅ | 1 |
| TC-009 | Functional | discard_file() 변경사항 되돌리기 | 임시 git 저장소 | True 반환, 파일 원복 확인 | ✅ | 1 |
| TC-010 | Functional | push() 메서드 시그니처 | 코드 검사 | remote, branch 파라미터 존재 | ✅ | 1 |
| TC-011 | Integration | CommitPanel 클래스 정의 확인 | AST 파싱 | CommitPanel 클래스 존재 | ✅ | 1 |
| TC-012 | Functional | 앱 정상 시작 (4초 생존) | `poetry run python main.py &` | 프로세스 생존 | ✅ | 1 |

---

## Result Legend
- ⬜ Not run
- ✅ PASS
- ❌ FAIL
- ⏭️ SKIP (reason: ___)

---

## Issue Log

### FAIL Cases
- 없음 — Iteration 1에서 12/12 전부 PASS
