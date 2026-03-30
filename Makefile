# Git Dashboard — 빌드 및 개발 편의 명령어

.PHONY: run test build pkg clean open

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

## .pkg 인스톨러 빌드 (.app 빌드 선행 필요)
pkg:
	chmod +x installer/scripts/postinstall
	pkgbuild \
		--root "dist/Git Dashboard.app" \
		--install-location "/Applications/Git Dashboard.app" \
		--identifier "com.jypark.git-dashboard" \
		--version "0.1.0" \
		--scripts installer/scripts \
		installer/GitDashboard.pkg
	productbuild \
		--distribution installer/distribution.xml \
		--resources installer/resources \
		--package-path installer \
		"dist/GitDashboard-0.1.0.pkg"
	@echo "Installer ready: dist/GitDashboard-0.1.0.pkg"
	@ls -lh "dist/GitDashboard-0.1.0.pkg"

## 빌드된 .app 실행
open:
	open "dist/Git Dashboard.app"

## 빌드 산출물 정리
clean:
	rm -rf build/ dist/
	@echo "Cleaned build artifacts"
