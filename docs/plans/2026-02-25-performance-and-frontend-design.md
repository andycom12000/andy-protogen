# Performance & Frontend Enhancement Design

Date: 2026-02-25

## Goals

1. Replace polling-based preview with MJPEG streaming
2. Optimize render pipeline (JPEG caching, numpy conversion caching)
3. Enhance frontend UX (offline state, error fallbacks, stream recovery)

## A. MJPEG Stream Endpoint

### Backend: `GET /api/preview/stream`

Add a new streaming endpoint in `web.py` using FastAPI's `StreamingResponse`:

```python
@app.get("/api/preview/stream")
async def preview_stream():
    async def generate():
        last_frame_id = None
        cached_jpeg = b""
        while True:
            frame = get_last_frame()
            if frame is not None:
                fid = id(frame)
                if fid != last_frame_id:
                    buf = io.BytesIO()
                    frame.save(buf, format="JPEG", quality=60)
                    cached_jpeg = buf.getvalue()
                    last_frame_id = fid
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + cached_jpeg + b"\r\n"
                )
            await asyncio.sleep(0.1)  # 10 fps cap
    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
```

Key decisions:
- 10 fps cap (128x32 panel doesn't need more for a small preview)
- Frame change detection via `id(frame)` — skip JPEG re-encoding when unchanged
- Keep existing `GET /api/preview` for backward compatibility

### Frontend

Replace `<canvas>` with `<img src="/api/preview/stream">`. Remove all polling code (`startPreview`, `stopPreview`, `fetchPreview`).

## B. Render Pipeline Optimization

### B1. JPEG Cache in RenderPipeline

Add cached JPEG bytes to `RenderPipeline` so both MJPEG stream and single-frame preview benefit:

```python
# New attributes in __init__:
self._jpeg_cache: bytes | None = None
self._jpeg_frame_id: int | None = None

def get_jpeg(self, quality: int = 60) -> bytes | None:
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

Impact: JPEG encoding goes from "once per HTTP request" to "once per frame change".

### B2. Numpy Array Caching in `_push_composited()`

Cache `np.asarray(base)` and only recompute when the base frame changes:

```python
# New attributes in __init__:
self._base_arr: np.ndarray | None = None
self._last_base_arr_id: int | None = None

# In _push_composited():
base = self.last_frame or self._black_frame
base_id = id(base)
if base_id != self._last_base_arr_id:
    self._base_arr = np.asarray(base)
    self._last_base_arr_id = base_id
effect_arr = np.asarray(self._effect_frame)
composited_arr = np.maximum(self._base_arr, effect_arr)
```

Impact: When expression is static (most of the time), base array conversion drops from once-per-frame to zero.

## C. Frontend Experience Enhancement

### C1. Offline UI State

Add `offline` class to body on WebSocket disconnect. Use CSS to disable all interactive elements:

```css
body.offline .expressions button,
body.offline .effects-grid button,
body.offline .text-input-row button,
body.offline input[type="range"] {
    pointer-events: none;
    opacity: 0.4;
}
```

Toggle class in `ws.onopen` / `ws.onclose`.

### C2. MJPEG Preview (replaces Canvas polling)

- `<canvas>` → `<img>` with `src="/api/preview/stream"`
- Keep `image-rendering: pixelated` and `aspect-ratio: 4/1`
- Adjust CSS for img vs canvas differences

### C3. Thumbnail Load Fallback

On `onerror`, replace with inline SVG placeholder:

```js
img.onerror = () => {
    img.src = 'data:image/svg+xml,...'; // grey placeholder
    img.onerror = null; // prevent infinite loop
};
```

### C4. MJPEG Stream Recovery

On img error (stream disconnects), retry with cache-bust:

```js
previewImg.onerror = () => {
    setTimeout(() => {
        previewImg.src = '/api/preview/stream?' + Date.now();
    }, 2000);
};
```

## Files to Modify

| File | Changes |
|------|---------|
| `src/protogen/inputs/web.py` | Add MJPEG stream endpoint, wire `get_jpeg` |
| `src/protogen/render_pipeline.py` | Add JPEG cache, numpy array cache |
| `web/static/index.html` | Replace canvas with img, add offline CSS, fallbacks |
| `tests/test_web_api.py` | Add MJPEG stream endpoint test |
| `tests/test_render_pipeline.py` | Add JPEG cache and numpy cache tests |

## Non-Goals

- Full numpy-ization of expression loading (too invasive for this iteration)
- WebSocket-based frame push (unnecessary with MJPEG)
- Canvas overlay/HUD (can revisit later)
