# Performance & Frontend Enhancement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace polling preview with MJPEG streaming, optimize render pipeline caching, and improve frontend offline/error UX.

**Architecture:** Add `get_jpeg()` cache to RenderPipeline, add MJPEG `StreamingResponse` endpoint to web.py, replace frontend canvas polling with `<img>` tag pointing at the stream, and add CSS-based offline state + image error fallbacks.

**Tech Stack:** Python (FastAPI StreamingResponse, PIL, numpy), vanilla JS/HTML/CSS

---

### Task 1: Add JPEG cache to RenderPipeline

**Files:**
- Modify: `src/protogen/render_pipeline.py:24-43` (add attributes to `__init__`)
- Modify: `src/protogen/render_pipeline.py` (add `get_jpeg()` method)
- Test: `tests/test_render_pipeline.py`

**Step 1: Write the failing tests**

Add to `tests/test_render_pipeline.py`:

```python
def test_get_jpeg_returns_none_without_frame():
    """get_jpeg returns None when no frame has been displayed."""
    display = MockDisplay(width=128, height=32)
    pipeline = RenderPipeline(display)
    assert pipeline.get_jpeg() is None


def test_get_jpeg_returns_valid_jpeg():
    """get_jpeg returns JPEG bytes after a frame is displayed."""
    display = MockDisplay(width=128, height=32)
    pipeline = RenderPipeline(display)
    pipeline.show_image(Image.new("RGB", (128, 32), (255, 0, 0)))
    data = pipeline.get_jpeg()
    assert data is not None
    assert data[:2] == b'\xff\xd8'  # JPEG magic bytes


def test_get_jpeg_caches_result():
    """get_jpeg returns cached bytes when the frame hasn't changed."""
    display = MockDisplay(width=128, height=32)
    pipeline = RenderPipeline(display)
    img = Image.new("RGB", (128, 32), (0, 255, 0))
    pipeline.show_image(img)
    first = pipeline.get_jpeg()
    second = pipeline.get_jpeg()
    assert first is second  # same object, not re-encoded


def test_get_jpeg_re_encodes_on_new_frame():
    """get_jpeg re-encodes when last_displayed_frame changes."""
    display = MockDisplay(width=128, height=32)
    pipeline = RenderPipeline(display)
    pipeline.show_image(Image.new("RGB", (128, 32), (255, 0, 0)))
    first = pipeline.get_jpeg()
    pipeline.show_image(Image.new("RGB", (128, 32), (0, 0, 255)))
    second = pipeline.get_jpeg()
    assert first is not second
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_render_pipeline.py::test_get_jpeg_returns_none_without_frame tests/test_render_pipeline.py::test_get_jpeg_returns_valid_jpeg tests/test_render_pipeline.py::test_get_jpeg_caches_result tests/test_render_pipeline.py::test_get_jpeg_re_encodes_on_new_frame -v`

Expected: FAIL — `AttributeError: 'RenderPipeline' object has no attribute 'get_jpeg'`

**Step 3: Implement get_jpeg with caching**

In `src/protogen/render_pipeline.py`, add to `__init__` after `self._effect_active = asyncio.Event()`:

```python
        # JPEG cache for preview endpoints
        self._jpeg_cache: bytes | None = None
        self._jpeg_frame_id: int | None = None
```

Add `import io` at top of file (after `import asyncio`).

Add method after `get_fps()`:

```python
    def get_jpeg(self, quality: int = 60) -> bytes | None:
        """Return JPEG bytes of last_displayed_frame, cached until frame changes."""
        frame = self.last_displayed_frame
        if frame is None:
            return None
        fid = id(frame)
        if fid != self._jpeg_frame_id:
            buf = io.BytesIO()
            frame.save(buf, format="JPEG", quality=quality)
            self._jpeg_cache = buf.getvalue()
            self._jpeg_frame_id = fid
        return self._jpeg_cache
```

Also invalidate the JPEG cache in `clear()` by adding after `self._last_composited_bytes = None`:

```python
        self._jpeg_cache = None
        self._jpeg_frame_id = None
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_render_pipeline.py -v`

Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/protogen/render_pipeline.py tests/test_render_pipeline.py
git commit -m "feat: add JPEG cache to RenderPipeline"
```

---

### Task 2: Add numpy base array caching to _push_composited

**Files:**
- Modify: `src/protogen/render_pipeline.py:24-43` (add attributes)
- Modify: `src/protogen/render_pipeline.py:105-126` (`_push_composited`)
- Test: `tests/test_render_pipeline.py`

**Step 1: Write the failing test**

Add to `tests/test_render_pipeline.py`:

```python
def test_base_array_cached_across_composites():
    """_push_composited caches base array when base frame doesn't change."""
    display = MockDisplay(width=128, height=32)
    pipeline = RenderPipeline(display)

    base = Image.new("RGB", (128, 32), (50, 50, 50))
    pipeline.show_image(base)
    pipeline.set_effect("matrix_rain", {})

    # First composite
    pipeline._effect_frame = Image.new("RGB", (128, 32), (0, 100, 0))
    pipeline._push_composited()
    first_arr = pipeline._base_arr

    # Second composite with same base, different effect frame
    pipeline._effect_frame = Image.new("RGB", (128, 32), (0, 200, 0))
    pipeline._last_composited_bytes = None  # force push
    pipeline._push_composited()
    second_arr = pipeline._base_arr

    assert first_arr is second_arr  # same cached array object
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_render_pipeline.py::test_base_array_cached_across_composites -v`

Expected: FAIL — `AttributeError: 'RenderPipeline' object has no attribute '_base_arr'`

**Step 3: Implement the caching**

In `__init__`, add after the new JPEG cache attributes:

```python
        # Cached numpy array for base frame in compositing
        self._base_arr: np.ndarray | None = None
        self._last_base_arr_id: int | None = None
```

Replace the compositing section in `_push_composited()` (lines 112-118):

```python
        base = self.last_frame
        if base is None:
            base = self._black_frame
        # Cache base array conversion — only recompute when base frame changes
        base_id = id(base)
        if base_id != self._last_base_arr_id:
            self._base_arr = np.asarray(base)
            self._last_base_arr_id = base_id
        effect_arr = np.asarray(self._effect_frame)
        composited_arr = np.maximum(self._base_arr, effect_arr)
```

Also invalidate the base array cache where the existing `self._last_base_id = None` resets happen:
- In `set_effect()`: add `self._last_base_arr_id = None` after `self._last_base_id = None`
- In `clear_effect()`: add `self._last_base_arr_id = None` after `self._last_base_id = None`
- In `clear()`: add `self._base_arr = None` and `self._last_base_arr_id = None`

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_render_pipeline.py -v`

Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/protogen/render_pipeline.py tests/test_render_pipeline.py
git commit -m "perf: cache numpy base array in compositing loop"
```

---

### Task 3: Add MJPEG stream endpoint

**Files:**
- Modify: `src/protogen/inputs/web.py:1-5` (add imports)
- Modify: `src/protogen/inputs/web.py:19-32` (change `get_last_frame` param to `get_jpeg`)
- Modify: `src/protogen/inputs/web.py:135-148` (update preview endpoint)
- Modify: `src/protogen/inputs/web.py` (add stream endpoint)
- Modify: `src/protogen/inputs/web.py:184-233` (update WebInput class)
- Modify: `src/protogen/main.py:99` (wire get_jpeg)
- Test: `tests/test_web_api.py`

**Step 1: Write the failing test**

Add to `tests/test_web_api.py`:

```python
def test_preview_stream_returns_mjpeg():
    """Preview stream endpoint returns multipart MJPEG content."""
    frame = Image.new("RGB", (128, 32), (255, 0, 0))
    jpeg_cache = [None]

    def get_jpeg(quality=60):
        if jpeg_cache[0] is None:
            buf = io.BytesIO()
            frame.save(buf, format="JPEG", quality=quality)
            jpeg_cache[0] = buf.getvalue()
        return jpeg_cache[0]

    commands = []

    async def put(cmd: Command) -> None:
        commands.append(cmd)

    app = _create_app(
        expression_names=["happy"],
        put=put,
        get_blink_state=lambda: False,
        get_current_expression=lambda: "happy",
        get_brightness=lambda: 100,
        get_display_fps=lambda: 30.0,
        get_jpeg=get_jpeg,
    )
    client = TestClient(app)
    # Stream endpoint returns multipart content
    with client.stream("GET", "/api/preview/stream") as response:
        assert response.status_code == 200
        content_type = response.headers["content-type"]
        assert "multipart/x-mixed-replace" in content_type
        # Read first chunk — should contain JPEG data
        chunk = b""
        for part in response.iter_bytes():
            chunk += part
            if b"\xff\xd8" in chunk:
                break
        assert b"\xff\xd8" in chunk


def test_preview_stream_no_jpeg_returns_204():
    """Preview stream returns 204 when get_jpeg is not provided."""
    commands = []

    async def put(cmd: Command) -> None:
        commands.append(cmd)

    app = _create_app(
        expression_names=["happy"],
        put=put,
        get_blink_state=lambda: False,
        get_current_expression=lambda: "happy",
        get_brightness=lambda: 100,
        get_display_fps=lambda: 30.0,
    )
    client = TestClient(app)
    response = client.get("/api/preview/stream")
    assert response.status_code == 204
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_web_api.py::test_preview_stream_returns_mjpeg tests/test_web_api.py::test_preview_stream_no_jpeg_returns_204 -v`

Expected: FAIL

**Step 3: Implement the MJPEG stream endpoint**

In `src/protogen/inputs/web.py`:

1. Add `import asyncio` to the imports at top.

2. Add `from fastapi.responses import FileResponse, Response, StreamingResponse` (add `StreamingResponse` to the existing import).

3. Change the `_create_app` signature: replace `get_last_frame: Callable[[], Image.Image | None] | None = None` with `get_jpeg: Callable[[int], bytes | None] | None = None`.

4. Update the existing `preview()` endpoint to use `get_jpeg`:

```python
    @app.get("/api/preview")
    async def preview():
        if get_jpeg is None:
            return Response(status_code=204)
        data = get_jpeg(60)
        if data is None:
            return Response(status_code=204)
        return Response(
            content=data,
            media_type="image/jpeg",
            headers={"Cache-Control": "no-store"},
        )
```

5. Add the MJPEG stream endpoint after the preview endpoint:

```python
    @app.get("/api/preview/stream")
    async def preview_stream():
        if get_jpeg is None:
            return Response(status_code=204)

        async def generate():
            while True:
                data = get_jpeg(60)
                if data is not None:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n"
                        + data + b"\r\n"
                    )
                await asyncio.sleep(0.1)

        return StreamingResponse(
            generate(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )
```

6. Update the `WebInput` class: change `get_last_frame` parameter to `get_jpeg`:

In `__init__` signature, replace:
```python
        get_last_frame: Callable[[], Image.Image | None] | None = None,
```
with:
```python
        get_jpeg: Callable[[int], bytes | None] | None = None,
```

In `__init__` body, replace:
```python
        self._get_last_frame = get_last_frame
```
with:
```python
        self._get_jpeg = get_jpeg
```

In `run()`, replace:
```python
            get_last_frame=self._get_last_frame,
```
with:
```python
            get_jpeg=self._get_jpeg,
```

7. In `src/protogen/main.py` line 99, replace:
```python
            get_last_frame=lambda: pipeline.last_displayed_frame,
```
with:
```python
            get_jpeg=pipeline.get_jpeg,
```

8. Update existing preview tests in `tests/test_web_api.py`:

Update `test_preview_returns_jpeg` — change `get_last_frame=lambda: frame` to use `get_jpeg`:

```python
def test_preview_returns_jpeg():
    """Preview endpoint returns JPEG when a frame is available."""
    frame = Image.new("RGB", (128, 32), (255, 0, 0))
    buf = io.BytesIO()
    frame.save(buf, format="JPEG", quality=60)
    jpeg_bytes = buf.getvalue()
    commands = []

    async def put(cmd: Command) -> None:
        commands.append(cmd)

    app = _create_app(
        expression_names=["happy"],
        put=put,
        get_blink_state=lambda: False,
        get_current_expression=lambda: "happy",
        get_brightness=lambda: 100,
        get_display_fps=lambda: 30.0,
        get_jpeg=lambda quality=60: jpeg_bytes,
    )
    client = TestClient(app)
    response = client.get("/api/preview")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "no-store"
    assert response.content[:2] == b'\xff\xd8'
```

Update `test_preview_no_frame_returns_204`:

```python
def test_preview_no_frame_returns_204():
    """Preview endpoint returns 204 when get_jpeg returns None."""
    commands = []

    async def put(cmd: Command) -> None:
        commands.append(cmd)

    app = _create_app(
        expression_names=["happy"],
        put=put,
        get_blink_state=lambda: False,
        get_current_expression=lambda: "happy",
        get_brightness=lambda: 100,
        get_display_fps=lambda: 30.0,
        get_jpeg=lambda quality=60: None,
    )
    client = TestClient(app)
    response = client.get("/api/preview")
    assert response.status_code == 204
```

`test_preview_no_callback_returns_204` stays the same (no `get_jpeg` passed = 204).

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_web_api.py -v`

Expected: ALL PASS

**Step 5: Run full test suite to check for regressions**

Run: `pytest -v`

Expected: ALL PASS

**Step 6: Commit**

```bash
git add src/protogen/inputs/web.py src/protogen/main.py tests/test_web_api.py
git commit -m "feat: add MJPEG stream endpoint, refactor preview to use get_jpeg"
```

---

### Task 4: Frontend — replace canvas with MJPEG img + offline state

**Files:**
- Modify: `web/static/index.html`

**Step 1: Update CSS — replace `.preview-card canvas` with `.preview-card img` and add offline styles**

In the `<style>` section, replace:

```css
        .preview-card canvas {
            width: 100%;
            image-rendering: pixelated;
            aspect-ratio: 4 / 1;
            border-radius: 4px;
        }
```

with:

```css
        .preview-card img {
            width: 100%;
            image-rendering: pixelated;
            aspect-ratio: 4 / 1;
            border-radius: 4px;
            display: block;
        }
```

Add offline CSS before the responsive media queries (before `/* 寬螢幕響應式 */`):

```css
        /* Offline state */
        body.offline .expressions button,
        body.offline .effects-grid button,
        body.offline .text-input-row button,
        body.offline .toggle-switch,
        body.offline input[type="range"] {
            pointer-events: none;
            opacity: 0.4;
        }
```

**Step 2: Update HTML — replace canvas with img**

Replace:

```html
        <div class="card preview-card">
            <canvas id="preview" width="128" height="32"></canvas>
        </div>
```

with:

```html
        <div class="card preview-card">
            <img id="preview" src="/api/preview/stream" alt="Live preview" width="128" height="32">
        </div>
```

**Step 3: Update JavaScript — remove polling, add offline toggle, add MJPEG recovery and thumbnail fallbacks**

In the `<script>` section, make these changes:

1. Remove the canvas/preview variables and functions. Delete:
```js
        const previewCanvas = document.getElementById('preview');
        const previewCtx = previewCanvas.getContext('2d');
        let previewTimer = null;

        function startPreview() {
            if (previewTimer) return;
            previewTimer = setInterval(fetchPreview, 200);
        }

        function stopPreview() {
            if (previewTimer) { clearInterval(previewTimer); previewTimer = null; }
        }

        async function fetchPreview() {
            try {
                const res = await fetch('/api/preview');
                if (res.status === 204) return;
                const blob = await res.blob();
                const bmp = await createImageBitmap(blob);
                previewCtx.drawImage(bmp, 0, 0, 128, 32);
                bmp.close();
            } catch (_) {}
        }
```

2. Add MJPEG stream recovery. Replace the deleted block with:
```js
        /* MJPEG preview recovery */
        const previewImg = document.getElementById('preview');
        let previewRetryTimer = null;
        function startPreview() {
            if (previewRetryTimer) { clearTimeout(previewRetryTimer); previewRetryTimer = null; }
            previewImg.src = '/api/preview/stream?' + Date.now();
        }
        function stopPreview() {
            previewImg.src = '';
        }
        previewImg.onerror = () => {
            if (previewRetryTimer) return;
            previewRetryTimer = setTimeout(() => {
                previewRetryTimer = null;
                if (ws && ws.readyState === WebSocket.OPEN) {
                    previewImg.src = '/api/preview/stream?' + Date.now();
                }
            }, 2000);
        };
```

3. Add offline class toggle. In the `connect()` function:

In `ws.onopen`, add after `reconnectDelay = 2000;`:
```js
                document.body.classList.remove('offline');
```

In `ws.onclose`, add after `statusEl.className = 'status disconnected';`:
```js
                document.body.classList.add('offline');
```

4. Add thumbnail fallback SVG. After the `displayName` function, add:
```js
        const PLACEHOLDER_SVG = 'data:image/svg+xml,' + encodeURIComponent(
            '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="32" viewBox="0 0 128 32">' +
            '<rect width="128" height="32" fill="#1a1a2e"/>' +
            '<text x="64" y="20" text-anchor="middle" fill="#64748b" font-size="10">?</text></svg>'
        );
```

5. Add `onerror` to thumbnail images. In both `loadExpressions()` and `loadEffects()`, after each `img.loading = 'lazy';` line, add:
```js
                    img.onerror = function() { this.src = PLACEHOLDER_SVG; this.onerror = null; };
```

6. Remove the standalone `startPreview();` call near the bottom (the one at line 1144), since `startPreview()` is already called from `ws.onopen`.

**Step 4: Verify by running existing tests (no frontend test framework, manual verification)**

Run: `pytest tests/test_web_api.py -v`

Expected: ALL PASS (backend tests still pass)

**Step 5: Commit**

```bash
git add web/static/index.html
git commit -m "feat: replace canvas polling with MJPEG stream, add offline UI state"
```

---

### Task 5: Run full test suite and verify

**Step 1: Run full test suite**

Run: `pytest -v`

Expected: ALL PASS (145+ tests)

**Step 2: Manual smoke test (optional)**

Run: `python -m protogen.main`

Verify:
- Mock display window opens
- Open browser to `http://localhost:8080`
- Preview shows MJPEG stream (not polling)
- Disconnect WebSocket (stop server) → UI greys out
- Reconnect → UI restores
- Thumbnail fallback works for missing expressions

**Step 3: Final commit if any fixups needed**

If no fixups needed, skip this step.
