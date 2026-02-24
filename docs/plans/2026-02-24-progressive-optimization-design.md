# 漸進式優化設計

日期：2026-02-24
狀態：已核准

## 目標

對 protogen 專案進行大型架構重構，涵蓋效能與穩定性、程式碼品質與可維護性。採用混合漸進式方案，分四個階段執行，每階段獨立驗證。

## Phase 1：快速修正 + 眨眼擴充

### 1.1 修正 Pillow 14 `getdata()` 棄用警告
- 檔案：`expression.py`, tests
- 改用 `tobytes()` 或 numpy 直接轉換
- 消除 6 項測試棄用警告

### 1.2 修正 `InputSource` Protocol 型態定義
- 檔案：`input_manager.py`
- `asyncio.coroutines` → `Callable[[Command], Awaitable[None]]`

### 1.3 修正 RenderPipeline 私有屬性存取
- 檔案：`render_pipeline.py`
- 添加 `FrameEffect.set_base_frame()` public method
- 消除直接存取 `_base_frame` 的封裝違規

### 1.4 添加參數驗證
- 檔案：`config.py`, `expression.py`
- 亮度範圍 0-100 校驗
- manifest.json 結構完整性驗證

### 1.5 WebSocket 命令合併
- 檔案：`inputs/web.py`
- SET_EFFECT + SET_EFFECT_PARAMS 合併為單一命令入隊

### 1.6 日誌記錄改善
- 檔案：DisplayBase, MockDisplay, HUB75Display, InputManager, ExpressionManager
- 核心元件加 `logging` 模組
- 關鍵操作（表情切換、亮度變更、輸入事件）記錄 info/debug

### 1.7 擴充 placeholder 腳本產生 blink 幀
- 檔案：`scripts/generate_placeholder_faces.py`
- 為 angry, crying, shocked, very_angry 各產生 7 幀眨眼動畫
- 幀序列：眼睛張開 → 閉合 → 張開，符合各表情的眼睛形狀

### 1.8 manifest.json 新增 blink 定義
- 檔案：`expressions/manifest.json`
- 新增 4 個 blink 動畫條目（angry_blink, crying_blink, shocked_blink, very_angry_blink）
- 4 個靜態表情加 `"idle_animation"` 欄位指向對應的 blink

**驗證**：85 個現有測試通過 + 無棄用警告 + 4 個新表情有眨眼

## Phase 2：效能優化

### 2.1 交叉淡化 float32 累加
- 檔案：`expression_manager.py`
- 用 float32 buffer 累加差值，最後單次 `astype(np.uint8)`
- 減少每幀的 array 複製和型別轉換

### 2.2 生成器 `update_params()` 統一
- 檔案：所有 generators
- 基類使用 dataclass 或 descriptor 自動同步參數
- 消除 4+ 個生成器的重複 `update_params()` 邏輯

### 2.3 FPS 計算改 EMA
- 檔案：`render_pipeline.py`
- 指數衰減平均取代 deque 滑動窗口
- FPS 顯示更穩定

**驗證**：效能測試比較 before/after

## Phase 3：架構重構

### 3.1 拆分 ExpressionManager
- `ExpressionStore` — 表情載入/查詢/索引管理
- `AnimationController` — 動畫播放/交叉淡化
- `BlinkController` — 眨眼邏輯/隨機間隔

### 3.2 RenderPipeline 組合模式
- 不再繼承 DisplayBase，改用組合持有 display 實例
- 更清晰的職責分離

### 3.3 依賴注入改善
- main.py 元件建立順序明確化
- 便於測試和模組替換

**驗證**：所有測試通過 + 新元件各自有獨立測試

## Phase 4：測試補強

### 4.1 端到端集成測試
- `tests/test_e2e.py`
- Input → Manager → Display 全鏈路

### 4.2 WebSocket 完整測試
- `tests/test_websocket.py`
- 長連接、斷線重連、訊息順序

### 4.3 邊界條件測試
- 參數化測試覆蓋邊界值

### 4.4 異常路徑測試
- `tests/test_error_handling.py`
- manifest 錯誤、圖片缺失、連線中斷

**驗證**：測試覆蓋率顯著提升
