# andy-protogen

Protogen 電子面罩系統：Raspberry Pi 5 + HUB75 LED 矩陣（128×32），使用 Python asyncio 架構。

## 安裝

需要 Python >= 3.12。

```bash
# 開發環境（Windows，含 mock display + 測試 + Web 控制）
pip install -e ".[mock,dev,web]"

# RPi 5 部署
pip install -e ".[rpi,web]"
```

## 啟動

```bash
# 開發模式（pygame 模擬視窗 + Web 控制介面）
python -m protogen.main

# Web 控制介面預設在 http://localhost:8080
```

設定檔為 `config.yaml`：
- `display.mock: true` — 開發模式（pygame-ce 視窗）
- `display.mock: false` — RPi 部署模式（HUB75 LED）
- `input.web_enabled: true` — 啟用 Web 控制（預設 port 8080）

## 測試

```bash
pytest              # 全部測試
pytest -v           # 詳細輸出
pytest tests/test_animation.py            # 單一檔案
pytest tests/test_animation.py::test_name # 單一測試
```

## 表情系統

表情定義在 `expressions/manifest.json`，支援：
- **static** — 單張 PNG 圖片
- **animation** — `frame_*.png` 幀序列，可設定 fps 和是否循環

產生佔位表情圖片：
```bash
python scripts/generate_placeholder_faces.py
```
