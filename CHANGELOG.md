# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [v1.4.0] - 2026-02-25

Phase 4 測試覆蓋率改善。

### Added
- E2E 整合測試：完整指令流程驗證（表情切換、效果套用、亮度調整、blink toggle）
- WebSocket 訊息測試：連線、表情/效果/亮度/blink 指令、心跳、無效訊息處理
- 邊界條件測試：Config 載入、亮度範圍驗證、空 Store、動畫引擎邊界值
- 錯誤處理測試：無效 JSON、缺失檔案/type/frames_dir、無效表情類型、load_effects KeyError

### Changed
- 測試數量從 99 增加至 145（+46 個測試，涵蓋 18 個測試檔案）

## [v1.3.0] - 2026-02-25

Phase 3 架構重構。

### Changed
- 拆分 `ExpressionManager` 為三個獨立元件：
  - `ExpressionStore` — 表情資料查詢（names、get、thumbnail）
  - `BlinkController` — 眨眼邏輯與隨機間隔控制
  - `ExpressionManager` — 精簡為門面（facade），負責動畫/轉場並協調子元件
- `RenderPipeline` 從繼承 `DisplayBase` 改為組合模式，不再假裝「是一個 display」
- `main.py` 元件建立順序明確化，`ExpressionStore` 獨立建立後注入

## [v1.2.0] - 2026-02-25

### Added
- Bad Apple!! 動畫表情（3286 幀 @ 15fps，128x32 黑白）
- `scripts/generate_bad_apple.py` 自動下載影片並擷取幀
- 表情 `hidden` 屬性，blink 動畫不再出現在可選表情清單中
- CHANGELOG.md 版本變動紀錄

### Changed
- angry / very_angry 表情紅色飽和度提升

## [v1.1.0] - 2025-02-25

Phase 1 快速修正 + Phase 2 效能優化。

### Fixed
- 修正 Pillow 14 `getdata()` 棄用警告，改用 `np.asarray()`
- 修正 `Image.BILINEAR` 棄用，改用 `Image.Resampling.BILINEAR`
- 修正 `InputSource` Protocol 型態定義（`asyncio.coroutines` → `Callable`）
- 修正 `RenderPipeline` 直接存取 `FrameEffect._base_frame` 封裝違規

### Added
- 亮度範圍 0-100 參數驗證（`DisplayConfig.__post_init__`）
- `manifest.json` 結構完整性驗證（型別、檔案路徑檢查）
- 核心元件結構化日誌（DisplayBase, MockDisplay, Config, Expression, Animation, InputManager）
- angry / crying / shocked / very_angry 各自專屬的 blink 動畫
- `FrameEffect.set_base_frame()` 公開方法

### Changed
- `SET_EFFECT` + `SET_EFFECT_PARAMS` 合併為 `SET_EFFECT_WITH_PARAMS` 原子命令
- 生成器 `update_params()` 統一使用 `_param_attrs` 類別變數，消除重複邏輯
- FPS 計算從 deque 滑動窗口改為指數移動平均（EMA, α=0.1）

### Performance
- 交叉淡化使用預分配 float32 buffer + in-place NumPy 運算，減少每幀記憶體分配

## [v1.0.0] - 2025-02-24

初始功能完整版本。

### Core Architecture
- 非同步事件驅動架構（asyncio）
- `DisplayBase` ABC + `MockDisplay`（pygame-ce）+ `HUB75Display`（piomatter）
- `InputManager` 非同步事件匯流排
- `ExpressionManager` 表情狀態機
- `AnimationEngine` FPS 控制逐幀播放（loop / one-shot）
- `Expression` 模型 + `manifest.json` 載入器
- `Config` YAML dataclass 載入器
- `RenderPipeline` 顯示包裝，追蹤 last_frame

### Expressions
- 8 種靜態表情：default, happy, angry, very_angry, crying, shocked, helpless, bsod
- 3 種動畫表情：blink, loading_spinner, loading_bar
- 開機動畫（掃描線 + 文字顯示）
- 表情切換交叉淡化過渡動畫
- 表情預覽縮圖 API

### Procedural Effects
- 8 種程序化效果：matrix_rain, starfield, plasma, scrolling_text, rainbow_sweep, breathe, glitch, color_shift
- 效果與表情分離的合成管線（compositing pipeline）
- 即時效果參數調整（不重建 generator）
- 幀變換效果（breathe, color_shift, rainbow_sweep, glitch）

### Web Interface
- FastAPI + WebSocket 即時控制介面
- 賽博龐克風格 Web UI
- 表情/效果網格選擇 + 預覽縮圖
- 亮度滑桿、blink 開關、滾動文字輸入
- 效果參數滑桿即時調整
- WebSocket 指數退避重連 + 心跳
- 亮度與面板狀態 localStorage 持久化

### Hardware & Deployment
- GPIO 按鈕輸入（gpiod 邊緣偵測）
- RPi 5 HUB75 LED 矩陣驅動（piomatter）
- 系統監控（CPU 溫度/使用率、記憶體、WiFi 信號、FPS）
- systemd 服務 + 部署腳本（`scripts/deploy.sh`）
- 省電最佳化（降低閒置功耗）
- SIGTERM 優雅關閉

### Bug Fixes
- FastAPI + `from __future__ import annotations` + WebSocket 403 問題
- Windows cp950 編碼問題（強制 UTF-8）
- uvicorn websockets origin 檢查 403（改用 wsproto）
- RPi 5 gpiod 必須在 piomatter 之前初始化
- uvloop 干擾 piomatter PIO/DMA（停用 uvloop）
- MockDisplay uint8 溢位
- 滾動文字更新不即時
- 亮度滑桿未即時更新 HUB75 顯示
