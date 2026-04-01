# TestCase: v2 F-18/F-19 (Rebase + Conflict)

> Created: 2026-03-31
> Target: domain/rebase_orchestrator.py, domain/conflict_resolver.py, ui/rebase_dialog.py, ui/merge_editor.py
> Total cases: 43 (도메인) + 4 (UI 화면) = 47
> Iteration: 1 (1회 만에 100% PASS)

---

## TC List — RebaseOrchestrator (F-18 도메인)

| TC# | Category | Test Item | Expected | Result |
|-----|----------|-----------|----------|--------|
| TC-001 | Functional | prepare() → RebasePlan 반환 | isinstance(plan, RebasePlan) | ✅ |
| TC-002 | Functional | steps 모두 pick action | all action == "pick" | ✅ |
| TC-003 | Functional | steps에 올바른 hash 포함 | "aaa0001" in hashes | ✅ |
| TC-004 | Functional | steps에 message 포함 | "feat: add login" in msgs | ✅ |
| TC-005 | Exception | dirty tree → ValueError | "dirty" match | ✅ |
| TC-006 | Boundary | 빈 커밋 → 빈 plan | steps == [] | ✅ |
| TC-007 | Functional | base_commit 설정 | plan.base_commit == "HEAD~3" | ✅ |
| TC-008 | Functional | 기본 onto=HEAD~10 | plan.base_commit == "HEAD~10" | ✅ |
| TC-009 | Functional | pick 라인 포맷 | "pick aaa0001 feat: add login" in content | ✅ |
| TC-010 | Functional | squash action | "squash bbb0002" in content | ✅ |
| TC-011 | Functional | drop action | "drop ccc0003" in content | ✅ |
| TC-012 | Functional | reword → new_message 사용 | "updated msg" in content | ✅ |
| TC-013 | Exception | invalid action 스킵 | "invalid_action" not in content | ✅ |
| TC-014 | Boundary | 긴 메시지 72자 잘림 | msg_part len <= 72 | ✅ |
| TC-015 | Functional | 마지막 줄 newline | content.endswith("\n") | ✅ |
| TC-016 | Functional | multiline message → 첫줄만 | second line not in content | ✅ |
| TC-017 | Functional | abort → returncode 0 → True | result is True | ✅ |
| TC-018 | Exception | abort returncode 1 → False | result is False | ✅ |
| TC-019 | Exception | abort exception → False | result is False | ✅ |
| TC-020 | Functional | continue → "--continue" in cmd | "--continue" in cmd | ✅ |
| TC-021 | Functional | get_rebase_status → None (no rebase) | status is None | ✅ |
| TC-022 | Functional | rebase-merge 있을 때 status 반환 | step==2, total==5 | ✅ |
| TC-023 | Functional | rebase-apply 있을 때 status 반환 | step==1 | ✅ |
| TC-024 | Functional | _parse_n HEAD~5 → 5 | 5 | ✅ |
| TC-025 | Functional | _parse_n HEAD~10 → 10 | 10 | ✅ |
| TC-026 | Boundary | _parse_n 브랜치명 → 10 | 10 | ✅ |
| TC-027 | Boundary | _parse_n HEAD~abc → 10 | 10 | ✅ |
| TC-028 | Functional | _write_sequence_editor_script → 실행파일 생성 | os.access X_OK | ✅ |
| TC-029 | Functional | 스크립트 shebang 확인 | content.startswith("#!/bin/sh") | ✅ |

## TC List — ConflictResolver (F-19 도메인)

| TC# | Category | Test Item | Expected | Result |
|-----|----------|-----------|----------|--------|
| TC-030 | Functional | UU 파일 감지 | "src/main.py" in result | ✅ |
| TC-031 | Functional | AA 파일 감지 | in result | ✅ |
| TC-032 | Functional | DD 파일 감지 | in result | ✅ |
| TC-033 | Functional | AU/UA 파일 감지 | in result | ✅ |
| TC-034 | Functional | M 파일 무시 | not in result | ✅ |
| TC-035 | Boundary | 클린 상태 → [] | [] | ✅ |
| TC-036 | Exception | git 예외 → [] | [] | ✅ |
| TC-037 | Functional | 복수 충돌 파일 | len==2 | ✅ |
| TC-038 | Boundary | 짧은 라인 무시 | [] | ✅ |
| TC-039 | Functional | ConflictFile 인스턴스 반환 | isinstance | ✅ |
| TC-040 | Functional | 충돌 1개 감지 | len==1 | ✅ |
| TC-041 | Functional | total_conflicts == 1 | 1 | ✅ |
| TC-042 | Functional | ours_content 파싱 | "ours line 1" in ours | ✅ |
| TC-043 | Functional | theirs_content 파싱 | "theirs line 1" in theirs | ✅ |
| TC-044 | Functional | diff3 base_content 파싱 | "base content" in base | ✅ |
| TC-045 | Functional | diff3 없을 때 base == [] | [] | ✅ |
| TC-046 | Functional | 충돌 2개 감지 | len==2 | ✅ |
| TC-047 | Boundary | 충돌 없음 → [] | [] | ✅ |
| TC-048 | Exception | 파일 없음 → 빈 ConflictFile | conflicts==[] | ✅ |
| TC-049 | Functional | non_conflict_lines 보존 | "line before"/"line after" | ✅ |
| TC-050 | Functional | start_line < end_line | True | ✅ |
| TC-051 | Functional | resolve ours → ours 내용 | "ours line 1" in result | ✅ |
| TC-052 | Functional | resolve theirs → theirs 내용 | "theirs line 1" in result | ✅ |
| TC-053 | Functional | resolve both → 양쪽 포함 | both in result | ✅ |
| TC-054 | Functional | resolve manual → 커스텀 내용 | "custom resolution" | ✅ |
| TC-055 | Exception | invalid index → IndexError | IndexError | ✅ |
| TC-056 | Functional | 주변 라인 보존 | "line before"/"line after" | ✅ |
| TC-057 | Functional | save_resolution → 파일 저장 | new content | ✅ |
| TC-058 | Functional | save_resolution → 마커 제거 | "<<<<<<< HEAD" not in | ✅ |
| TC-059 | Functional | mark_resolved → git add 호출 | index.add 1회 | ✅ |
| TC-060 | Exception | mark_resolved 실패 → RuntimeError | "git add 실패" | ✅ |
| TC-061 | Functional | resolve_all → 모든 충돌 제거 | no markers | ✅ |
| TC-062 | Functional | resolve_all ours → a1, a2 | in result | ✅ |
| TC-063 | Functional | resolve_all theirs → b1, b2 | in result | ✅ |
| TC-064 | Boundary | resolve_all 충돌 없음 → no error | no exception | ✅ |
| TC-065 | Functional | _pick ours | ["ours\n"] | ✅ |
| TC-066 | Functional | _pick theirs | ["theirs\n"] | ✅ |
| TC-067 | Functional | _pick both | ours + theirs | ✅ |
| TC-068 | Functional | _pick manual | manual content | ✅ |
| TC-069 | Boundary | _pick manual None → ours fallback | ["ours\n"] | ✅ |
| TC-070 | Boundary | _pick unknown → ours fallback | ["ours\n"] | ✅ |
| TC-071 | Functional | manual content → ends with \n | True | ✅ |
| TC-072 | Functional | resolve markers 제거 확인 | no <<< === >>> | ✅ |

---

## TC List — 화면 테스트 (UI 컴포넌트)

| TC# | Category | Test Item | Expected | Result |
|-----|----------|-----------|----------|--------|
| SC-009 | UI | RebaseDialog 생성 + plan 로드 | steps==2 | ✅ |
| SC-010 | UI | MergeEditor 생성 | 오류 없음 | ✅ |
| SC-011 | UI | demo_v2.py 5탭 DemoWindow | count==5 | ✅ |
| SC-012 | UI | 전체 import/생성 순서 | stylesheet 오류 없음 | ✅ |

---

## 최종 결과

```
✅ test-iterate complete: v2-f18-f19

📊 Final Results
   ┌──────────────────────────────────────────┐
   │ Iter │ PASS │ FAIL │ Rate               │
   ├──────────────────────────────────────────┤
   │  1   │  47  │  0   │ 100% ✅            │
   └──────────────────────────────────────────┘

전체 누적: 293 pytest + 12 화면 테스트 = 305 PASS (v2 전체)

📝 Files created (F-18/F-19):
   - app/domain/rebase_orchestrator.py
   - app/domain/conflict_resolver.py
   - app/ui/rebase_dialog.py
   - app/ui/merge_editor.py
   - tests/test_rebase_orchestrator.py  (29 TC)
   - tests/test_conflict_resolver.py    (43 TC)
   - demo_v2.py (5탭으로 확장)
```
