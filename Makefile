# Git Dashboard — 빌드 및 개발 편의 명령어

.PHONY: run test build clean open

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

## 빌드된 .app 실행
open:
	open "dist/Git Dashboard.app"

## 빌드 산출물 정리
clean:
	rm -rf build/ dist/
	@echo "Cleaned build artifacts"
