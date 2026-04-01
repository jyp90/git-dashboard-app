# TestCase: v2 Domain Layer (F-13, F-14, F-15)

> Created: 2026-03-31
> Target: app/domain/diff_parser.py, app/domain/stash_manager.py, app/domain/commit_graph_builder.py
> Total cases: 90
> Iteration: 1 (1회 만에 100% PASS)

---

## TC List

| TC# | Category | Test Item | Execution | Expected | Result | Iteration |
|-----|----------|-----------|-----------|----------|--------|-----------|
| TC-001~034 | DiffParser | unified diff 파싱 (34개) | pytest test_diff_parser.py | 전체 PASS | ✅ | 1 |
| TC-035~059 | StashManager | stash CRUD 및 미리보기 (25개) | pytest test_stash_manager.py | 전체 PASS | ✅ | 1 |
| TC-060~090 | CommitGraphBuilder | DAG 레이아웃/레인 할당 (31개) | pytest test_commit_graph_builder.py | 전체 PASS | ✅ | 1 |

### DiffParser 주요 TC

| TC# | Category | Test Item | Expected | Result |
|-----|----------|-----------|----------|--------|
| TC-001 | Boundary | 빈 diff 파싱 | [] 반환 | ✅ |
| TC-002 | Boundary | 공백만 있는 diff | [] 반환 | ✅ |
| TC-003 | Functional | 단순 diff 1개 파일 | FileDiff 1개 | ✅ |
| TC-007 | Functional | add/delete/context 라인 타입 | 각 type 정확 | ✅ |
| TC-014 | Functional | 멀티 파일 diff | FileDiff 2개 | ✅ |
| TC-017 | Functional | 신규 파일 (added) | status="added" | ✅ |
| TC-019 | Functional | 삭제된 파일 | status="deleted" | ✅ |
| TC-021 | Functional | 바이너리 파일 | is_binary=True | ✅ |
| TC-023 | Functional | 이름 변경 파일 | status="renamed", similarity=95 | ✅ |
| TC-025 | Functional | 멀티 hunk | 2개 hunk | ✅ |
| TC-029~032 | Integration | GitRepository 연동 (mock) | 올바른 메서드 호출 | ✅ |
| TC-033~034 | Functional | 라인 번호 정확성 | 1-indexed | ✅ |

### StashManager 주요 TC

| TC# | Category | Test Item | Expected | Result |
|-----|----------|-----------|----------|--------|
| TC-035 | Boundary | 빈 stash 목록 | [] 반환 | ✅ |
| TC-036 | Functional | stash 목록 조회 | StashEntry 리스트 | ✅ |
| TC-041 | Functional | stash 생성 성공 | StashEntry 반환 | ✅ |
| TC-042 | Exception | stash 생성 실패 | None 반환 | ✅ |
| TC-047 | Functional | stash apply (유지) | pop=False | ✅ |
| TC-049 | Functional | stash pop (삭제) | pop=True | ✅ |
| TC-052 | Functional | stash drop | True 반환 | ✅ |
| TC-055 | Functional | stash 미리보기 | FileDiff 리스트 | ✅ |
| TC-058 | Boundary | stash 개수 0 | 0 반환 | ✅ |

### CommitGraphBuilder 주요 TC

| TC# | Category | Test Item | Expected | Result |
|-----|----------|-----------|----------|--------|
| TC-060 | Boundary | 빈 저장소 | GraphLayout(nodes=[]) | ✅ |
| TC-061 | Functional | 직선 히스토리 3개 | 모두 lane 0 | ✅ |
| TC-064 | Functional | straight 엣지 타입 | "straight" | ✅ |
| TC-067 | Functional | 머지 커밋 감지 | is_merge=True | ✅ |
| TC-071 | Functional | merge_in 엣지 | 엣지에 포함 | ✅ |
| TC-072 | Functional | 분기 히스토리 | 다른 lane 할당 | ✅ |
| TC-076 | Functional | 레인 중복 없음 | A≠B lane | ✅ |
| TC-080 | Functional | 엣지 parent/child 연결 | 올바른 해시 | ✅ |
| TC-084 | Functional | 브랜치 팁 감지 | is_branch_tip=True | ✅ |
| TC-087 | Functional | 색상 팔레트 hex | #으로 시작 | ✅ |
| TC-089 | Performance | 100개 직선 커밋 | max_columns=1 | ✅ |
| TC-090 | Functional | limit 파라미터 | repo에 전달 | ✅ |

---

## Result Legend
- ⬜ Not run
- ✅ PASS
- ❌ FAIL
- ⏭️ SKIP

---

## Issue Log

### FAIL Cases
없음 — 1회 실행에 90/90 전체 PASS

---

## 최종 결과

```
✅ test-iterate complete: v2-domain-layer

📊 Final Results
   ┌──────────────────────────────────────┐
   │ Iter │ PASS │ FAIL │ Rate           │
   ├──────────────────────────────────────┤
   │  1   │  90  │  0   │ 100% ✅        │
   └──────────────────────────────────────┘

📋 TestCase Sheet: docs/test-cases/v2-domain-layer-testcases.md
📝 Files created: 5
   - app/domain/models.py (v2 모델 추가)
   - app/infrastructure/git_repository.py (v2 메서드 추가)
   - app/domain/diff_parser.py (신규)
   - app/domain/stash_manager.py (신규)
   - app/domain/commit_graph_builder.py (신규)
```
