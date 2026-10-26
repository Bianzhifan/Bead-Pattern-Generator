# 服务调用文档

服务行为、算法与边界以 [设计规范（Spec）](ALGORITHM_README.zh.md) 为准；本文仅说明如何调用已定义的接口。

## 启动

在项目根目录执行：

```powershell
uv sync --frozen
uv run uvicorn --app-dir src bead_pattern.main:app --host 127.0.0.1 --port 8000
```

交互式接口页面为 `http://127.0.0.1:8000/docs`。

也可使用 Docker：

```powershell
docker compose up --build
```

镜像内含 `src/data/registries/` 色卡文件；运行时不挂载该目录。

## 注册表查询

### 获取全部注册表

```http
GET /api/registries
```

返回每个 `registry_id` 及其套系列表。当前包含：

- `artkal` / `s-5mm`
- `perler` / `color-chart`

### 获取某注册表的套系

```http
GET /api/registries/{registry_id}/series
```

未知注册表返回 `404`。

## 生成图纸

```http
POST /api/generate
Content-Type: multipart/form-data
```

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `image` | 是 | 图片文件内容。 |
| `registry_id` | 是 | 色卡注册表，例如 `artkal`。 |
| `series_id` | 是 | 套系 ID，例如 `s-5mm`。 |
| `width` | 默认模式必填 | 图纸横向豆子数。 |
| `height` | 默认模式必填 | 图纸纵向豆子数。 |
| `preserve_aspect_ratio` | 否 | 传入 `true` 时保留原图比例。 |

默认模式中必须同时提供 `width` 和 `height`，服务会对图片居中裁切，再生成对应尺寸的网格。

当 `preserve_aspect_ratio=true` 时，只能提供 `width` 或 `height` 其中一项。服务根据已经完成 EXIF 方向校正的图片比例计算另一边，不进行裁切。

成功时响应为：

```http
200 OK
Content-Type: image/png
Content-Disposition: attachment; filename="pattern.png"
```

响应体为完整的 PNG 图纸。图纸包含颜色网格、格内编号、行列坐标和色号图例。

### 默认裁切示例

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/generate" -F "image=@C:\path\to\photo.png" -F "registry_id=artkal" -F "series_id=s-5mm" -F "width=50" -F "height=40" --output pattern.png
```

### 保留图片比例示例

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/generate" -F "image=@C:\path\to\photo.png" -F "registry_id=artkal" -F "series_id=s-5mm" -F "width=100" -F "preserve_aspect_ratio=true" --output pattern.png
```

## 限制与错误

限制值集中定义在 `src/bead_pattern/config.py`；修改该文件后需要重启服务，并同步更新本节。

- 最大上传大小：10 MiB。
- 最大解码像素数：16,000,000。
- 图纸最大尺寸：单边 200 格，总计 40,000 格。
- 不存在的注册表或套系返回 `404`。
- 无效表单、不可解码图片、非法尺寸，或保留比例模式下同时提供宽和高，返回 `422`。

错误响应使用 JSON：

```json
{
  "code": "invalid_input",
  "message": "..."
}
```
