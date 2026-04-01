# TestCase: git-dashboard-diff-tab

> Created: 2026-04-01
> Target: app/ui/main_window.py (Diff 탭), app/domain/diff_parser.py
> Total cases: 8

---

## TC List

| TC# | Category | Test Item | Execution | Expected | Result | Iteration |
|-----|---------|------------|---------|----------|------|------|
| TC-001 | Functional | main_window.py 문법 검사 | `poetry run python -m py_compile app/ui/main_window.py` | 오류 없음 | ✅ | 1 |
| TC-002 | Functional | QListWidgetItem import 확인 | grep 검사 | import 라인에 QListWidgetItem 포함 | ✅ | 1 |
| TC-003 | Functional | DiffParser.parse_raw() 파싱 정상 | python 스크립트 | FileDiff 1개, hunk 6라인 | ✅ | 1 |
| TC-004 | Functional | 도메인 모듈 import 검사 | `python -c "from app.domain..."` | NameError 없음 | ✅ | 1 |
| TC-005 | Functional | get_raw_diff 워킹트리 diff 반환 | 임시 git 저장소 테스트 | line2 포함된 diff 반환 | ✅ | 1 |
| TC-006 | Functional | DiffParser 빈 diff 처리 | parse_raw("") | 빈 리스트 [] 반환 | ✅ | 1 |
| TC-007 | Boundary | _reset_v2_tabs 탭 수 범위 초과 | 로직 시뮬레이션 | 크래시 없이 skip | ✅ | 1 |
| TC-008 | Functional | 앱 정상 시작 (3초 생존) | `poetry run python main.py &` → PID 확인 | 프로세스 살아있음 | ✅ | 1 |

---

## Result Legend
- ⬜ Not run
- ✅ PASS
- ❌ FAIL
- ⏭️ SKIP (reason: ___)

---

## Issue Log

### FAIL Cases
- (없음 — 1회 반복으로 전체 PASS)

### Fix Summary (Iteration 1)
- TC-001/002 원인: `QListWidgetItem`이 local import에서 누락
- Fix: `app/ui/main_window.py:166` — import에 `QListWidgetItem` 추가
