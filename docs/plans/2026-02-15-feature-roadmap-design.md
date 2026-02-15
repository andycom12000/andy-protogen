# Protogen Feature Roadmap Design

> Date: 2026-02-15
> Status: Approved

## Overview

Protogen 面罩功能擴展路線圖，基於社群調查和現有架構分析，規劃四批功能逐步實作。

## Architecture Decision: 基底 + 效果疊層

採用雙層渲染管線（RenderPipeline）架構：

```
BaseLayer (Expression)  →  PIL Image (128×32 RGBA)
                                  ↓
EffectLayer (optional)  →  pixel transform / blend
                                  ↓
                           Final composited frame
                                  ↓
                           Display.show_image()
```

- **BaseLayer**：現有 Expression 系統，產出每幀 PIL Image
- **EffectLayer**：可選處理器，對 BaseLayer 輸出做像素級變換
- **全螢幕程序化表情**（matrix_rain、starfield 等）直接作為 BaseLayer 的一種，不經過 EffectLayer

---

## Batch 1: Foundation — 基礎強化

### 1.1 Fix blink_interval_max

**問題**：`_blink_loop()` 硬編碼 `random.uniform(3.0, 6.0)`，不讀取 `config.blink_interval_max`。

**修復**：改為 `random.uniform(self.config.blink_interval_min, self.config.blink_interval_max)`。

### 1.2 RenderPipeline

新增 `src/protogen/render_pipeline.py`：

```python
class RenderPipeline:
    """雙層渲染管線"""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.effect: EffectBase | None = None

    def set_effect(self, effect: EffectBase | None):
        self.effect = effect

    def render(self, base_frame: Image.Image) -> Image.Image:
        if self.effect is None:
            return base_frame
        return self.effect.apply(base_frame, time.monotonic())
```

整合：`AnimationEngine` 取得當前幀後，經過 `RenderPipeline.render()` 再送到 Display。

### 1.3 Expression Transition Animation

切換表情時，在 `transition_duration_ms` 時間內做 cross-fade：

```python
class TransitionRenderer:
    def render(self, old_frame: Image, new_frame: Image, progress: float) -> Image:
        return Image.blend(old_frame, new_frame, alpha=progress)
```

觸發點：`ExpressionManager.set_expression()`，過渡期間 `AnimationEngine` 每幀呼叫混合。

### 1.4 Boot Animation

程序化開機動畫：

```python
class BootAnimation:
    """掃描線 → 'PROTOGEN' 文字 → 淡出到預設表情"""
    phases = [
        ("scanline", 0.0, 0.6),
        ("text",     0.6, 1.5),
        ("fadeout",  1.5, 2.0),
    ]
```

啟動流程：`main.py` → 播放 BootAnimation → 完成後切到 `default_expression`。

### 1.5 Web UI Expression Preview Thumbnails

新增 API：

```
GET /api/expressions/{name}/thumbnail → PNG image
```

- 靜態表情：回傳原圖
- 動畫表情：回傳第一幀
- 程序化表情：回傳預設 icon 或預渲染截圖

Web UI：用 `<img>` 卡片替代純文字按鈕。

---

## Batch 2: Procedural Content — 程序化內容

### 2.1 Procedural Expression Type

擴展 `expressions/manifest.json`：

```json
{
  "matrix_rain": {
    "type": "procedural",
    "generator": "matrix_rain",
    "params": { "color": [0, 255, 70], "speed": 1.0, "density": 0.3 }
  }
}
```

新增 `ProceduralExpression` 類別和 generator 註冊機制：

```python
GENERATORS: dict[str, type[ProceduralGenerator]] = {
    "matrix_rain": MatrixRainGenerator,
    "starfield": StarfieldGenerator,
    "plasma": PlasmaGenerator,
    "scrolling_text": ScrollingTextGenerator,
}
```

### 2.2 Matrix Rain

駭客帝國風格程式碼雨。隨機落下的字元列，頭端亮白色，尾部漸淡為深綠。使用小型像素字體。

Parameters: `color`, `speed`, `density`

### 2.3 Starfield

星空飛行效果，從畫面中心向外飛散。靠近邊緣的星星更大更亮。

Parameters: `star_count`, `speed`, `color`

### 2.4 Plasma

流動電漿效果，多個 sin 函數疊加產生色彩流動。使用 numpy 向量運算確保效能。

Parameters: `palette`, `speed`

### 2.5 Scrolling Text

水平滾動文字，從右到左。使用 PIL ImageFont 渲染到長圖，每幀偏移 x 位置。支援動態更新文字內容。

Parameters: `text`, `speed`, `color`, `font_size`

### 2.6 Web UI Text Input

新增 API：

```
POST /api/text  {"text": "Hello!", "speed": 1.0, "color": [0, 255, 255]}
```

Web UI 新增文字輸入區域：文字框 + 發送按鈕 + 速度/顏色選項。發送後自動切換到 `scrolling_text` 表情。

---

## Batch 3: Effect Layer — 效果疊層

### 3.1 EffectLayer System

效果基底類別：

```python
class EffectBase(ABC):
    def __init__(self, params: dict):
        self.params = params
        self.start_time = time.monotonic()

    @abstractmethod
    def apply(self, frame: Image.Image, t: float) -> Image.Image: ...

EFFECTS: dict[str, type[EffectBase]] = {
    "rainbow_sweep": RainbowSweepEffect,
    "breathe": BreatheEffect,
    "glitch": GlitchEffect,
    "color_shift": ColorShiftEffect,
}
```

### 3.2 RainbowSweep

將非黑像素重新上色，色相隨 x 座標和時間偏移，產生流動彩虹。保留原圖亮度資訊。

### 3.3 Breathe

亮度隨時間做正弦波變化。

Parameters: `period`（呼吸週期秒數）, `amplitude`（亮度變化幅度）

### 3.4 Glitch

隨機觸發：水平像素行位移、RGB 通道錯位、隨機色塊。大部分時間正常，偶爾閃故障。

Parameters: `intensity`（頻率/強度）

### 3.5 ColorShift

整體色相隨時間緩慢旋轉。RGB → HSV，偏移 H，再轉回 RGB。

Parameters: `speed`（旋轉速度）

### 3.6 Web UI Effect Control

新增 API：

```
GET  /api/effects              → 可用效果列表
POST /api/effect/{name}        → 啟用效果 {"params": {...}}
POST /api/effect/off           → 關閉效果疊層
GET  /api/state                → 增加 current_effect 欄位
```

WebSocket 命令：

```json
{"action": "set_effect", "name": "rainbow_sweep", "params": {"speed": 1.0}}
{"action": "set_effect", "name": "off"}
```

Web UI：效果列表（按鈕組） + 「無效果」選項 + 效果參數滑桿。

---

## Batch 4: Advanced — 進階功能

### 4.1 System Status Panel

新增 API：

```
GET /api/system/status → {
    "cpu_temp": 45.2,
    "cpu_usage": 12.5,
    "memory_used": 45.0,
    "uptime": 3600,
    "wifi_signal": -45,
    "display_fps": 30.0,
    "current_expression": "happy",
    "current_effect": "rainbow_sweep",
    "brightness": 80
}
```

`SystemMonitor` 類別收集系統資訊。使用 `psutil` 套件。Windows 開發環境 CPU 溫度和 WiFi 信號回傳 `null`。

Web UI：可折疊的狀態面板，每 2 秒透過 WebSocket 更新。

### 4.2 systemd Service

提供 `systemd/protogen.service`：

```ini
[Unit]
Description=Protogen Face Controller
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/andy-protogen
ExecStart=/home/pi/andy-protogen/.venv/bin/python -m protogen.main
Restart=on-failure
RestartSec=5
WatchdogSec=30

[Install]
WantedBy=multi-user.target
```

加上 watchdog 回報和安裝腳本 `scripts/install_service.sh`。

---

## New Dependencies

| Package | Purpose | When |
|---------|---------|------|
| `psutil` | System status monitoring | Batch 4 |
| (none)  | Batches 1-3 use existing PIL/numpy | — |

## Files to Create/Modify

### New Files
- `src/protogen/render_pipeline.py` — RenderPipeline
- `src/protogen/effects/` — EffectBase + 各效果實作
- `src/protogen/generators/` — ProceduralGenerator + 各程序化表情
- `src/protogen/system_monitor.py` — SystemMonitor
- `systemd/protogen.service` — systemd 服務檔
- `scripts/install_service.sh` — 部署腳本

### Modified Files
- `src/protogen/expression_manager.py` — 整合 RenderPipeline、修復 blink_interval
- `src/protogen/expression.py` — 支援 procedural type
- `src/protogen/animation.py` — 整合 transition 和 pipeline
- `src/protogen/inputs/web.py` — 新 API endpoints
- `src/protogen/main.py` — 開機動畫、SystemMonitor 啟動
- `src/protogen/commands.py` — 新命令（set_effect, set_text）
- `src/protogen/config.py` — 新 config 區段
- `web/static/index.html` — 縮圖、文字輸入、效果控制、狀態面板
- `expressions/manifest.json` — 程序化表情定義
- `config.yaml` — 新設定項
- `pyproject.toml` — psutil dependency
