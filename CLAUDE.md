# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language

Always respond in **繁體中文台灣用語**。

## Project Overview

Protogen 電子面罩系統：Raspberry Pi 5 + HUB75 LED 矩陣（128×32），使用 Python asyncio 架構。Windows 開發用 pygame-ce MockDisplay，RPi 部署用 PioMatter HUB75Display。

## Commands

```bash
# 安裝（開發環境，含 mock display + 測試工具）
pip install -e ".[mock,dev,web]"

# 安裝（RPi 部署）
pip install -e ".[rpi,web]"

# 執行
python -m protogen.main

# 測試
pytest              # 全部測試
pytest -v           # 詳細輸出
pytest tests/test_animation.py            # 單一檔案
pytest tests/test_animation.py::test_name # 單一測試

# 產生佔位表情圖片
python scripts/generate_placeholder_faces.py
```

## Architecture

**非同步事件驅動架構**，核心流程：

```
Input Sources → InputManager (asyncio.Queue) → handle_commands() → ExpressionManager → Display
```

### 核心元件

- **DisplayBase** (`display/base.py`) — ABC 抽象介面，兩個實作：
  - `MockDisplay` (`display/mock.py`) — pygame-ce 視窗，開發用
  - `HUB75Display` (`display/hub75.py`) — piomatter 驅動，RPi 5 用
- **InputManager** (`input_manager.py`) — 非同步事件匯流排，`add_source()` 註冊輸入插件
- **ExpressionManager** (`expression_manager.py`) — 表情狀態機，管理 current expression index
- **AnimationEngine** (`animation.py`) — FPS 控制的逐幀播放，支援 loop 與 one-shot
- **Expression** (`expression.py`) — 從 `expressions/manifest.json` 載入 PNG 靜態圖或動畫幀序列
- **Config** (`config.py`) — YAML dataclass 載入器，設定檔為 `config.yaml`

### 輸入來源（插件式）

- **ButtonInput** (`inputs/button.py`) — GPIO 邊緣偵測（gpiod），僅 RPi
- **WebInput** (`inputs/web.py`) — FastAPI 伺服器 + WebSocket，REST API 與即時控制

### Web API

- `GET /api/expressions` — 列出所有表情
- `POST /api/expression/{name}` — 設定表情
- `POST /api/brightness/{value}` — 設定亮度
- `WebSocket /ws` — 即時雙向控制

### Expression Manifest 格式

`expressions/manifest.json` 定義表情，支援 `static`（單張 PNG）和 `animation`（frame_*.png 目錄，按 glob 排序）。

## Key Technical Notes

### Python 環境
- Python 3.14 環境使用 **pygame-ce**（非 pygame，pygame 不支援 3.14）
- `pyproject.toml` 指定 `python_requires = ">=3.12"`

### 已知陷阱

1. **FastAPI + `from __future__ import annotations` + WebSocket = 403**
   `from __future__ import annotations` 讓型別註解變字串。若 `WebSocket` 在函式內 lazy import 但用於巢狀路由的 type hint，FastAPI 無法解析 → 403。**必須在模組層級 import `FastAPI`、`WebSocket`。**

2. **Windows cp950 編碼**
   `open(path)` 在 Windows 預設 cp950（Big5），含非 ASCII 的檔案（如 YAML 中文註解）會失敗。**所有 `open()` 都要加 `encoding="utf-8"`。**

3. **uvicorn WebSocket origin 檢查**
   `websockets>=14` 預設做 origin 檢查 → 403。**在 `uvicorn.Config` 中使用 `ws="wsproto"`。**

### 測試

- 使用 pytest-asyncio，`asyncio_mode = "auto"`
- `tests/conftest.py` 提供 `mock_display` fixture
- 測試不需要實體硬體，全部透過 MockDisplay

### 設定檔 (`config.yaml`)

- `display.mock: true` — 開發模式（pygame-ce 視窗）
- `display.mock: false` — RPi 部署模式
- `display.mock_scale: 8` — 開發視窗的像素縮放倍率
- `input.web_enabled: true` — 啟用 FastAPI 伺服器（預設 port 8080）
