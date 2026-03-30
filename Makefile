# Git Dashboard — 빌드 및 개발 편의 명령어

.PHONY: run test build dmg clean open

## 개발 실행
run:
	poetry run python main.py

## 테스트 실행
test:
	poetry run pytest tests/ -v

## .app 번들 빌드 (F-12)
build:
	poetry run pyinstaller git_dashboard.spec --noconfirm
	@echo "Build complete: dist/Git Dashboard.app"
	@du -sh "dist/Git Dashboard.app"

## .dmg 드래그 설치 이미지 빌드 (.app 빌드 선행 필요: make build)
dmg:
	create-dmg \
		--volname "Git Dashboard" \
		--window-pos 200 120 \
		--window-size 600 400 \
		--icon-size 128 \
		--icon "Git Dashboard.app" 150 185 \
		--hide-extension "Git Dashboard.app" \
		--app-drop-link 450 185 \
		--no-internet-enable \
		"dist/GitDashboard-0.1.0.dmg" \
		"dist/Git Dashboard.app"
	@echo "DMG ready: dist/GitDashboard-0.1.0.dmg"
	@ls -lh "dist/GitDashboard-0.1.0.dmg"

## 빌드된 .app 실행
open:
	open "dist/Git Dashboard.app"

## 빌드 산출물 정리
clean:
	rm -rf build/ dist/
	@echo "Cleaned build artifacts"
