# TestCase: v2 Infrastructure + UI Layer (F-13~F-17)

> Created: 2026-03-31
> Target: infrastructure/, ui/, controller/diff_controller.py
> Total cases: 172 (유닛) + 8 (화면 테스트)
> Iteration: 1 (1회 만에 100% PASS)

---

## TC List — Infrastructure Layer

| TC# | Category | Test Item | Expected | Result |
|-----|----------|-----------|----------|--------|
| TC-001~037 | KeychainService (37개) | macOS security CLI 연동 | 전체 PASS | ✅ |
| TC-038~061 | IdeIntegrationService (24개) | IntelliJ CLI 연동 | 전체 PASS | ✅ |
| TC-062~082 | FileWatcherService (21개) | .git 디렉토리 감시 | 전체 PASS | ✅ |

### KeychainService 주요 TC
| TC# | Category | Test Item | Expected | Result |
|-----|----------|-----------|----------|--------|
| TC-001 | Functional | HTTPS URL → 서비스명 생성 | "com.git-dashboard.git-credential.{host}" | ✅ |
| TC-005 | Functional | store_git_credential 성공 | True 반환 | ✅ |
| TC-009 | Functional | get_git_credential → (user, token) | (jypark, mytoken) | ✅ |
| TC-013 | Exception | 빈 token → None | None | ✅ |
| TC-021 | Functional | store_secure_setting | True | ✅ |
| TC-030 | Functional | cleanup_all → count 반환 | 1 | ✅ |
| TC-034 | Exception | FileNotFoundError → ScriptResult.failure | success=False | ✅ |
| TC-035 | Exception | TimeoutExpired → failure | "timed out" | ✅ |

### IdeIntegrationService 주요 TC
| TC# | Category | Test Item | Expected | Result |
|-----|----------|-----------|----------|--------|
| TC-038 | Functional | is_available=True | True | ✅ |
| TC-040 | Functional | detect PyCharm | "PyCharm" | ✅ |
| TC-046 | Functional | open_project → Popen 호출 | True | ✅ |
| TC-051 | Functional | open_file --line 42 | args 포함 | ✅ |
| TC-053 | Functional | setup_git_hooks 파일 생성 | 2개 hook 파일 | ✅ |
| TC-056 | Functional | shutil.which로 idea 발견 | 경로 설정 | ✅ |

### FileWatcherService 주요 TC
| TC# | Category | Test Item | Expected | Result |
|-----|----------|-----------|----------|--------|
| TC-062 | Functional | start_watching → paths 등록 | > 0 | ✅ |
| TC-063 | Functional | HEAD 파일 감시 | HEAD 경로 포함 | ✅ |
| TC-067 | Boundary | .git 없을 때 오류 없음 | no exception | ✅ |
| TC-068 | Functional | COMMIT_EDITMSG → commit_detected | emit 1회 | ✅ |
| TC-069 | Functional | HEAD → branch_changed | emit 1회 | ✅ |
| TC-073 | Functional | refs/heads → push_detected | emit 1회 | ✅ |
| TC-075 | Functional | flush → repository_changed | emit 1회 | ✅ |
| TC-080 | Functional | read HEAD branch | "develop" | ✅ |

---

## TC List — 화면 테스트 (UI 컴포넌트)

| TC# | Category | Test Item | Expected | Result |
|-----|----------|-----------|----------|--------|
| SC-001 | UI | CommitGraphView 생성 | 오류 없음 | ✅ |
| SC-002 | UI | DiffViewer 생성 | 오류 없음 | ✅ |
| SC-003 | UI | GraphRenderer graph_width(2) = 50 | 50 | ✅ |
| SC-004 | UI | SyntaxHighlighter 6개 언어 감지 | .py→python, .java→java 등 | ✅ |
| SC-005 | UI | DiffController 생성 | 오류 없음 | ✅ |
| SC-006 | UI | StashPanel 생성 | 오류 없음 | ✅ |
| SC-007 | UI | CommitGraphView hit_test | 정확한 노드 반환 | ✅ |
| SC-008 | UI | DiffViewer Inline→Side-by-Side 모드 전환 | 오류 없음 | ✅ |

---

## 최종 결과

```
✅ test-iterate complete: v2-infrastructure-ui-layer

📊 Final Results
   ┌──────────────────────────────────────────┐
   │ Iter │ PASS │ FAIL │ Rate               │
   ├──────────────────────────────────────────┤
   │  1   │ 180  │  0   │ 100% ✅            │
   └──────────────────────────────────────────┘

전체 누적: 221 pytest + 8 화면 테스트 = 229 PASS

📝 Files created:
   - app/infrastructure/keychain_service.py
   - app/infrastructure/ide_integration_service.py
   - app/infrastructure/file_watcher_service.py
   - app/ui/syntax_highlighter.py
   - app/ui/diff_viewer.py
   - app/ui/commit_graph_view.py
   - app/ui/graph_renderer.py
   - app/ui/stash_panel.py
   - app/controller/diff_controller.py
   - demo_v2.py (화면 테스트 데모)
```
