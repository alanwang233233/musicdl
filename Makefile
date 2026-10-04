# =============================================================================
# musicdl 构建脚本
#
#   目标                       产物
#   ---------------------------------------------------------------------------
#   make lib                   核心库 wheel (dist/*.whl, 跨平台通用)
#   make cli                   CLI 单文件可执行 (PyInstaller, 需在目标系统上构建)
#   make gui                   桌面 GUI 应用 (flet build, 需在目标系统上构建)
#   make all                   当前系统可构建的全部目标
#
# 说明:
#   * PyInstaller 与 flet build 均不支持交叉编译, 各平台产物须在对应系统上构建;
#     三平台全量构建由 .github/workflows/build.yml 在 CI 中并行完成。
#   * flet build macos 需要: 完整版 Xcode + CocoaPods。安装 Xcode 后执行:
#         sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
#         sudo xcodebuild -runFirstLaunch
#         brew install cocoapods
# =============================================================================

# ---- 平台与工具链 ------------------------------------------------------------
ifeq ($(OS),Windows_NT)
    HOST_OS  := windows
    VENV_BIN := .venv/Scripts
    SYS_PY   := python
else
    UNAME_S := $(shell uname -s)
    ifeq ($(UNAME_S),Darwin)
        HOST_OS := macos
    else
        HOST_OS := linux
    endif
    VENV_BIN := .venv/bin
    SYS_PY   := python3
endif

# 优先使用仓库内 .venv, 否则退回系统 Python / PATH 上的 flet
ifneq ($(wildcard $(VENV_BIN)/.),)
    PY   := $(VENV_BIN)/python
    FLET := $(VENV_BIN)/flet
else
    PY   := $(SYS_PY)
    FLET := flet
endif

PIP         := $(PY) -m pip
BUILD       := $(PY) -m build
PYINSTALLER := $(PY) -m PyInstaller

.PHONY: help all install test lint typecheck clean \
        lib cli cli-macos cli-windows cli-linux \
        gui gui-macos gui-windows gui-linux

help: ## 显示本帮助
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

all: lib cli gui ## 构建当前系统支持的全部目标

install: ## 安装开发依赖 (可编辑安装 + build 工具)
	$(PIP) install -e ".[dev,cli,gui]" build

test: ## 运行测试
	$(PY) -m pytest

lint: ## ruff 检查
	$(PY) -m ruff check src/ tests/

typecheck: ## 类型检查 (需先 pip install pyright)
	$(PY) -m pyright src/musicdl_gui/

clean: ## 清理构建产物
	rm -rf build dist src/*.egg-info .pytest_cache .ruff_cache .coverage htmlcov

# ---- 核心库 ------------------------------------------------------------------
lib: ## 构建核心库 wheel (跨平台通用)
	$(BUILD) --wheel --outdir dist
	@ls -lh dist/*.whl

# ---- CLI (PyInstaller) -------------------------------------------------------
cli: cli-$(HOST_OS) ## 构建当前系统的 CLI 单文件可执行

cli-macos:
	$(if $(filter macos,$(HOST_OS)),,$(error cli-macos 只能在 macOS 上构建: PyInstaller 不支持交叉编译))
	$(PYINSTALLER) musicdl_cli.spec --noconfirm --clean
	@ls -lh dist/musicdl-cli*

cli-windows:
	$(if $(filter windows,$(HOST_OS)),,$(error cli-windows 只能在 Windows 上构建: PyInstaller 不支持交叉编译))
	$(PYINSTALLER) musicdl_cli.spec --noconfirm --clean

cli-linux:
	$(if $(filter linux,$(HOST_OS)),,$(error cli-linux 只能在 Linux 上构建: PyInstaller 不支持交叉编译))
	$(PYINSTALLER) musicdl_cli.spec --noconfirm --clean
	@ls -lh dist/musicdl-cli*

# ---- GUI (flet build) --------------------------------------------------------
gui: gui-$(HOST_OS) ## 构建当前系统的 GUI 桌面应用

gui-macos:
	$(if $(filter macos,$(HOST_OS)),,$(error gui-macos 只能在 macOS 上构建))
	$(FLET) build macos -o build/gui-macos
	@ls -d build/gui-macos/*.app

gui-windows:
	$(if $(filter windows,$(HOST_OS)),,$(error gui-windows 只能在 Windows 上构建))
	$(FLET) build windows -o build/gui-windows

gui-linux:
	$(if $(filter linux,$(HOST_OS)),,$(error gui-linux 只能在 Linux 上构建))
	$(FLET) build linux -o build/gui-linux
