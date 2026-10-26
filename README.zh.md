# 拼豆图纸生成服务

根据图片、色卡注册表和目标网格生成一张带色号图例的 PNG 拼豆图纸。

设计规范见 [docs/ALGORITHM_README.zh.md](docs/ALGORITHM_README.zh.md)，面向调用方的接口文档见 [docs/README.zh.md](docs/README.zh.md)。

## 启动

需要已安装 [uv](https://docs.astral.sh/uv/)：

```powershell
uv sync --frozen
uv run uvicorn --app-dir src bead_pattern.main:app --host 127.0.0.1 --port 8000
```

## Docker 启动

Docker 镜像包含 `src/` 和其中的本地色卡，不挂载或运行时修改色卡目录：

```powershell
docker compose up --build
```

服务监听 `http://127.0.0.1:8000`。停止服务使用 `docker compose down`。

服务启动后访问 `http://127.0.0.1:8000/docs` 提交图片，或使用：

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/generate" -F "image=@C:\path\to\photo.png" -F "registry_id=perler" -F "series_id=color-chart" -F "width=50" -F "height=40" --output pattern.png
```

成功时接口返回 `image/png`。色卡位于 `src/data/registries/`，启动时会一次性校验。

当前色卡随源码交付。后续版本应由云端下发或同步色卡注册表，并沿用现有 `registry_id`、`series_id`、`code`、`name`、`hex` 结构；新色卡校验通过后才能替换当前有效色卡。

默认需要同时提供 `width` 和 `height`，服务会按该比例居中裁切图片。若要保留整张图片比例，传入可选字段 `preserve_aspect_ratio=true`，并且只提供其中一边；服务自动计算另一边且不裁切：

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/generate" -F "image=@C:\path\to\photo.png" -F "registry_id=artkal" -F "series_id=s-5mm" -F "width=100" -F "preserve_aspect_ratio=true" --output pattern.png
```

启用 `preserve_aspect_ratio=true` 时，同时提供 `width` 和 `height` 会返回 HTTP `422`。图纸上限为单边 200 格、总计 40,000 格。

## 测试

```powershell
uv run pytest -q
```
