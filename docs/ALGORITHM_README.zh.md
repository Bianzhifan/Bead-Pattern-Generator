# 拼豆图纸生成服务设计规范（Spec）

> 本文是项目的设计规范。服务行为、接口契约、输入校验边界、色卡注册表结构和核心算法应以本文为准；实现代码和调用文档需要与本文保持一致。

## 项目目标

用户上传图片，选择本地 color 注册表、套系和图纸尺寸。程序把图片转换为拼豆网格：计算每格平均色，从所选套系中找到最近的色号，并输出一张带色号图例的图纸图片。项目使用 Python、FastAPI 和本地 JSON 色卡文件，不使用数据库。依赖由 uv 管理，支持从源码或 Docker 启动。

## 输入与输出

输入：图片、`registry_id`、`series_id`、`width`、`height`，以及可选的 `preserve_aspect_ratio`。`width × height` 是豆子的列数和行数，例如 `50 × 40` 需要 2000 颗豆子。每个网格单元对应一颗豆子。

输出：一张 PNG 图纸，包含彩色网格、行列坐标和色号图例。服务直接返回 PNG 图片字节，同时保留把 PNG 发送给下游 HTTP 服务的传输函数。题目没有提供真实上下游地址，因此用集成测试验证两侧传输。

## 服务边界

将生成过程定义为 `generate(validated_image, palette, width, height, crop) -> png_bytes`。FastAPI 入口完成校验、图片解码、色卡选择和尺寸计算后，再把可信数据交给这个函数。生成函数不读取上传目录，也不负责长期保存文件。

FastAPI 提供上游入口 `POST /api/generate`：接收图片和参数，在入口校验后调用 `generate`，以 `image/png` 返回图纸。传输模块另提供 `send_to_downstream(client, target, png_bytes, request_id)`，以 HTTP POST 将 PNG 发送到下游；真实下游地址由调用方在集成时提供，不由本服务从用户请求中读取。本题不实现上游或下游服务本身。

集成测试中的 Mock 上游从测试目录读取图片并调用 `POST /api/generate`；Mock 下游接收 `send_to_downstream` 发出的 PNG 并检查图纸。Mock 代码和测试文件均不进入正式应用，也不暴露额外 HTTP 路由。

## 本地 color 注册表

每个注册表是 `src/data/registries/` 下的一个目录，随项目源码交付。用户在生成图纸时选择本地已有的注册表，随后从该注册表中选择套系。切换注册表只改变当前请求使用的色卡，不修改全局设置。

```text
src/data/registries/
  artkal/
    s-5mm.json
  perler/
    color-chart.json
```

单个套系文件示例：

```json
{
  "series_id": "color-chart",
  "name": "Perler Color Chart",
  "colors": [
    { "code": "P1", "name": "Evergreen", "hex": "#315545" },
    { "code": "P2", "name": "Light Grey", "hex": "#B3BAB8" }
  ]
}
```

当前已录入两份色卡：`artkal/s-5mm.json` 共 225 色，来自 [Artkal 色卡页](https://www.pixel-beads.com/zh/artkal-bead-color-chart)；`perler/color-chart.json` 共 103 色，来自 [Perler 色卡页](https://trypetrelic.com/zh/perler-bead-color-chart.html)。数据按 2026-10-10 访问到的页面保存，只保留套系 ID、名称及每色的 `code`、`name`、`hex`。Perler 页注明 `P1` 等是该站短码，并非 Perler 官方商品编号；图纸图例应按来源解释这些代码。HEX 是屏幕参考色，特殊质感豆和实物颜色可能与数值不一致。

目录名是 `registry_id`，文件名是 `series_id`。程序启动时一次性扫描并校验所有 JSON：每个套系至少有一种颜色，色号不能重复，HEX 必须有效。校验通过后构建只读色卡索引；API 只接受索引中已有的 ID，不用请求参数直接拼接文件路径。修改色卡后重启服务生效。

### 后续色卡来源

当前版本的色卡随源码交付，便于本地运行和测试。后续版本应由云端下发或同步色卡注册表；云端数据仍应使用相同的 `registry_id`、`series_id`、`code`、`name`、`hex` 结构。下载完成后先校验完整色卡，再替换本地只读索引；任一校验失败时继续使用上一份有效色卡。该演进不改变 `/api/generate` 的调用参数和颜色匹配算法。

## 程序结构

```text
project/
  pyproject.toml         # uv 项目与依赖声明
  uv.lock                # uv 生成的依赖锁文件
  Dockerfile             # 生产运行镜像
  docker-compose.yml     # 本地 Docker 启动配置
  .dockerignore
  .gitignore
  src/
    bead_pattern/
      __init__.py
      main.py             # FastAPI 路由与请求入口校验
      config.py           # 静态服务限制，不读取环境变量
      registry.py         # 启动时校验色卡，构建只读索引
      image_processing.py # 图片预处理、分格、平均色
      color_matching.py  # 最近色号计算
      rendering.py       # 绘制带色号图例的 PNG 图纸
      generator.py       # 编排色卡读取、匹配和绘图，返回 PNG 字节
      transport.py       # 将 PNG 通过 HTTP 发送给下游
      schemas.py         # 请求与响应数据结构
    data/
      registries/        # 随源码交付的色卡文件
        artkal/s-5mm.json
        perler/color-chart.json
  tests/
    integration/
      mock_file_store.py # 模拟上游上传与下游接收
      test_generate.py   # 调用真实 FastAPI 接口
      fixtures/          # 固定的测试输入图片
        624f790ab7fb4fdbb516375c8dbd648f.png
      output/            # 测试运行产物，不提交
```

### 路径与交付边界

不从环境变量读取文件路径。`registry.py` 用 `Path(__file__).resolve().parents[1] / "data" / "registries"` 定位同级的 `src/data/registries/`，不依赖当前工作目录。以源码目录启动时，`bead_pattern/` 与 `data/` 保持同级；色卡缺失时启动失败。用户只能通过请求中的 `registry_id` 和 `series_id` 选择已有色卡，不能指定服务器文件路径。`config.py` 仅集中定义静态请求限制，不读取环境变量。

正式交付包含 `src/bead_pattern/`、`src/data/registries/`、`pyproject.toml`、`uv.lock`、`Dockerfile`、`docker-compose.yml`、`.dockerignore` 和 README。`tests/integration/` 用来验证交付，其中的 Mock 上下游代码不进入 Docker 镜像。`tests/integration/output/` 加入 `.gitignore`。正式服务不负责图片持久化或结果文件托管；下游 HTTP 地址和鉴权信息由集成方提供，不写入色卡或请求参数。

在 `pyproject.toml` 中声明依赖，运行 `uv lock` 生成并提交 `uv.lock`；本地用 `uv sync --frozen` 安装。启动命令通过 `--app-dir src` 从源码导入 `bead_pattern`。锁文件应由 uv 生成，不手工编写。

## 从源码启动与提交图片

初版在项目根目录运行，不需要构建安装包：

```powershell
uv sync --frozen
uv run uvicorn --app-dir src bead_pattern.main:app --host 127.0.0.1 --port 8000
```

## Docker 启动

```powershell
docker compose up --build
```

Dockerfile 先按 `uv.lock` 安装生产依赖，再复制 `src/` 并以 `0.0.0.0:8000` 启动 Uvicorn。镜像包含 `src/data/registries/`；`.dockerignore` 排除测试、开发虚拟环境、原始输入图片和生成结果。色卡更新需要重新构建镜像。

启动后可访问 `http://127.0.0.1:8000/docs`，在 `POST /api/generate` 中选择本地图片并填写 `registry_id`、`series_id`、`width`、`height`。也可以使用 PowerShell 中的 `curl.exe`；下面使用本地图片和已录入的 `perler/color-chart`：

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/generate" -F "image=@C:\path\to\photo.png" -F "registry_id=perler" -F "series_id=color-chart" -F "width=50" -F "height=40" --output pattern.png
```

`image` 是 `multipart/form-data` 中的文件字段，传入的是图片文件内容，不是服务器上的图片路径。服务成功时返回 HTTP 200、`Content-Type: image/png` 和 `Content-Disposition: attachment; filename="pattern.png"`，响应体就是完整的 PNG 字节。上例中的 `--output pattern.png` 将响应保存为本地图片。输入错误时返回相应 HTTP 错误码和 JSON 错误信息，不返回 PNG。

默认必须同时提供 `width` 和 `height`，图片会按目标比例居中裁切。若希望保留整张图片比例，额外传入 `preserve_aspect_ratio=true`，并且只传入 `width` 或 `height` 其中之一；服务按图片比例计算缺失边长且不裁切。该字段启用时同时提供宽和高会返回 422。

```powershell
# 保持原图比例，按横向 100 颗豆子计算纵向颗数
curl.exe -X POST "http://127.0.0.1:8000/api/generate" -F "image=@C:\path\to\photo.png" -F "registry_id=artkal" -F "series_id=s-5mm" -F "width=100" -F "preserve_aspect_ratio=true" --output pattern.png
```

### 上下游传输约定

- **上游调用本服务**：`POST /api/generate`，以 `multipart/form-data` 传入图片字节和参数；本服务直接在 HTTP 响应体返回 PNG 字节。
- **本服务发送给下游**：`transport.py` 的 `send_to_downstream` 用注入的 HTTP 客户端向已配置的下游目标发送 `POST`，请求体为同一份 PNG 字节，`Content-Type: image/png`，并传递 `request_id` 方便追踪。发送函数只负责传输，不能重新绘图或改写图片。
- 下游地址、鉴权和客户端由调用该函数的集成层提供。题目未给出真实下游，因此源码启动的 `/api/generate` 只返回图片，不自行向未知地址发送。下游返回非成功状态或连接失败时，传输函数报告发送失败；不会把失败当作图纸生成成功。

处理链路：

```text
图片字节与图纸参数
  → FastAPI 校验并解码图片、解析尺寸和色卡 ID
  → 从已校验的只读索引取得色卡
  → 图片标准化并分成 width × height 网格
  → 计算每格平均色
  → 匹配最近色号，得到色号矩阵
  → 统计图例中使用的色号及颗数
  → 绘制带网格和色号图例的 PNG
  → FastAPI 返回 PNG 图片字节
```

### 集成测试中的上传与下载 Mock

1. `tests/integration/test_generate.py` 使用内存测试图片和 `fixtures/624f790ab7fb4fdbb516375c8dbd648f.png`，模拟上游提供图片字节。
2. 测试通过 FastAPI `TestClient` 将图片作为 `multipart/form-data` 发送给真实的 `/api/generate`。
3. 测试把响应 PNG 交给 `send_to_downstream`，使用 Mock HTTP 下游接收并保存到 `tests/integration/output/`，检查传输前后字节一致、图片尺寸、网格和色号图例。

这里“上传”指模拟上游调用真实接口，“下载”指上游取得 PNG 响应；另用 Mock 下游验证主动发送 PNG 的传输函数。正式服务不保存上传图片或生成文件。

### 数据合法性边界

业务数据合法性校验只发生在两个入口：

1. **应用启动入口**：校验 `src/data/registries/` 下全部注册表 JSON，构建只读色卡索引；任何文件无效就启动失败。处理请求时不再重复校验色号和 HEX。
2. **HTTP 请求入口**：校验 `registry_id`、`series_id` 是否存在。默认模式下，`width`、`height` 均为正整数且网格面积在上限内；`preserve_aspect_ratio=true` 时只允许一边，由入口按图片比例计算另一边。入口还校验上传字节大小、图片是否可解码、解码后像素数及输出 PNG 的预计画布尺寸，应用 EXIF 方向并把图片转换到 sRGB；无效 ICC 配置也在这里处理。入口统一把错误转成 HTTP 响应。

入口通过后，生成模块收到已解码图片、已校验色卡和有效尺寸。`image_processing.py`、`color_matching.py`、`rendering.py` 不再重复进行合法性检查，也不处理 HTTP 错误。出站 `transport.py` 只检查下游 HTTP 传输是否成功，不重新校验 PNG 的业务内容。内部计算异常仍作为程序错误记录，不伪装成用户输入错误。

## 核心算法

### 1. 图片预处理与分格

入口层用 Pillow 解码图片并读取尺寸、像素数；超过上限或解码失败时直接返回错误。它还完成 EXIF 方向和 ICC 到 sRGB 的转换；无 ICC 配置时按 sRGB 解释。通过入口校验后，图像处理模块只接收已标准化图片，不重复检查格式、尺寸或参数合法性。

1. 将 sRGB 转成线性 RGB；带透明通道的图片在线性 RGB 中与白色背景合成，避免半透明边缘变暗。
2. 默认模式下，按目标 `width / height` 居中裁切到相同比例。`preserve_aspect_ratio=true` 时跳过裁切，使用整张标准化图片。
3. 按最终 `width × height` 做面积平均；每个输出格子是对应子窗的线性 RGB 平均色。

### 2. 最近色号

将网格平均色和色卡 HEX 转换到相同的 CIE Lab 定义：sRGB 原色、D65 白点。色卡 HEX 先按 sRGB 解码为线性 RGB；网格平均色已经在线性 RGB 中，不再重复解码。对每个格子，计算它与所选套系所有颜色的 CIEDE2000 色差，取色差最小的色号：

`code(i, j) = argmin_color ΔE00(grid(i, j), color)`

若色差相同，按色号排序后取第一个，保证结果稳定。匹配只在所选套系内进行。得到的 `height × width` 色号矩阵是绘制图纸的唯一数据来源。

这个匹配结果依赖色卡 HEX 的准确性；若色卡值与实体豆的观感不一致，最近色号也可能看起来不准。默认模式的居中裁切会丢掉边缘内容；启用 `preserve_aspect_ratio=true` 可避免裁切。平均色会抹平小于单格的细节。这些是当前算法的明确取舍。

### 3. PNG 图纸

每格填充匹配到的颜色，绘制网格线和行列坐标。每个格子印一个简短标记（例如按色号排序后的编号），使用黑色或白色文字中对比度较高的一种。图纸旁边或下方绘制色号图例：标记、色块、完整色号、颜色名称及使用颗数。图例只列出本图实际使用的颜色，颗数之和必须等于 `width × height`。图例条目较多时增加画布高度；格子边长和最大画布尺寸需设上限，避免文字无法阅读或生成超大 PNG。生成结果只有这一张 PNG 图片。

## FastAPI 接口

| 接口 | 功能 |
| --- | --- |
| `GET /api/registries` | 列出本地注册表 |
| `GET /api/registries/{registry_id}/series` | 列出注册表中的套系 |
| `POST /api/generate` | 直接接收图片并返回图纸 PNG |

`POST /api/generate` 使用 `multipart/form-data`，字段为 `image`、`registry_id`、`series_id`、`width`、`height`，可选字段为 `preserve_aspect_ratio`。默认模式必须提供宽和高；传入 `preserve_aspect_ratio=true` 后只能提供其中一边。响应类型为 `image/png`。上述输入限制在接口入口统一执行；无效图片、无效 ID 或无效尺寸返回清晰的错误信息。调用方直接从响应中取得图纸图片；正式服务不提供按 ID 下载文件的接口。

当前图纸尺寸上限为单边 200 格、总计 40,000 格；因此 `200 × 200` 合法。

## 核心伪代码

```python
def generate(validated_image, palette, width, height, crop):
    pixels = normalize_and_crop(validated_image, width, height, crop=crop)
    grid_rgb = area_average_in_linear_rgb(pixels, width, height)
    grid_lab = linear_rgb_to_lab_d65(grid_rgb)
    codes = nearest_palette_codes(grid_lab, palette)  # CIEDE2000
    counts = count_codes(codes)
    return render_png(codes, counts, palette)
```

## 验收检查

- 单色图片的所有格子映射到同一最近色号。
- 结果矩阵为 `height × width`，图例颗数总和为 `width × height`。
- 选择不同注册表时，匹配只使用对应注册表的颜色。
- 非整除尺寸图片的边缘像素参与平均色计算。
- 带透明边缘和 ICC 配置的图片经过标准化后颜色正确；网格大于原图时没有空格子。
- PNG 图纸的网格、色号标记和图例与同一色号矩阵一致。
- 最长色号与最多图例条目仍能读清，超过画布上限的请求被明确拒绝。
- 集成测试可用 Mock 上游上传图片，Mock 下游接收 `/api/generate` 返回的 PNG。
- 下游 HTTP Mock 收到的 PNG 字节与接口响应一致，发送失败能被传输函数明确报告。
- 从源码启动时能读取同级的 `src/data/registries/`，集成测试的 Mock 代码不被正式应用导入。
