# 一致性角色生成 · 使用指南

同一张脸换衣着 / 换动作 / 换表情 / 换场景。本文说明三种入口的差别和脚本用法。

## 三种入口怎么选

| 入口 | 一句话 | 适用模型 | 水印 | 速度 |
| --- | --- | --- | --- | --- |
| **DSH 面板 `edit_image`** | 最方便，点一下 | `hy-image-3.5` | ⚠️ WORKBUDDY | ~60s |
| **本脚本 `consistency_gen.py`** ⭐ | 无水印、可批量、可绕超时 | `doubao-seedream-5-lite`、`qwen-image-3.0-pro` 等 | 无 | ~30s |
| **Kaggle 渠道 `kaggle-turbo`** | 免费、尺寸更大 | `qwen-image-2.1-turbo` | 无 | ~103s |

### 为什么有的模型在面板里报 400

DSH 插件有一行写死的分流逻辑：

```js
request.mode === "edit" && !isSeedream(model) && !isAgnes(model)
  ? "/images/edits"        // multipart 上传参考图
  : "/images/generations"  // JSON
```

- `hy-image-3.5` 不在排除名单 → 走 `/edits` → **能成功**
- `doubao-seedream-*`、`agnes-*` 被强制走 `/generations` → 本地网关要求参考图走 `/edits` → **报 400**

本地网关本身完全支持图生图，所以脚本直接按正确格式调用即可。

## 脚本用法

### 单张

```bash
python consistency_gen.py \
  --ref 基准图.png \
  --prompt "穿深灰职业西装，盘发，微微一笑，浅灰影棚背景" \
  --out suit.png
```

### 批量（推荐）

`prompts.json`：

```json
[
  {"name": "01_suit",   "prompt": "穿深灰西装，盘发，微笑，影棚"},
  {"name": "02_casual", "prompt": "穿牛仔衬衫，披发，大笑，咖啡馆窗边"},
  {"name": "03_hanfu",  "prompt": "穿月白汉服，发髻玉簪，垂眸，园林"}
]
```

```bash
python consistency_gen.py \
  --ref 基准图.png \
  --batch prompts.json \
  --outdir ./variants
```

输出：

```
[1/3] 01_suit: OK 1160KB -> ./variants/01_suit.png
[2/3] 02_casual: OK 1873KB -> ./variants/02_casual.png
[3/3] 03_hanfu: OK 1802KB -> ./variants/03_hanfu.png

完成 3/3，输出目录: ./variants
```

### 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--ref` | 必填 | 参考图路径（清晰正脸、光线均匀效果最好） |
| `--prompt` | — | 单张的改造描述（与 `--batch` 二选一） |
| `--batch` | — | 批量描述 JSON 文件 |
| `--out` / `--outdir` | `out.png` / `./variants` | 输出位置 |
| `--model` | `doubao-seedream-5-lite` | 模型；seedream 无水印 |
| `--size` | `1024x1024` | 支持 `1024x1024`、`768x1024` 等 |
| `--base-url` | `http://127.0.0.1:3065` | 网关地址 |
| `--no-lock` | 关闭 | 不自动加身份锁定前缀（见下） |

### 身份锁定前缀

脚本默认给每条 prompt 自动加上：

> 保持这位人物面部特征和身份完全不变（同样的脸型、眼睛、鼻子、嘴唇、肤色、发型颜色），改为：

实测这句能显著提升一致性。想自己控制就传 `--no-lock`。

### 密钥

自动从 DSH 插件配置读取（`~/.dsh/profiles/desktop/cordis.patch.yml` 里的 `sk-a2a-...`）。
也可以手动指定：

```bash
set IMAGE_GATEWAY_KEY=sk-a2a-xxxx     # Windows
export IMAGE_GATEWAY_KEY=sk-a2a-xxxx  # Linux/macOS
```

## 写好 prompt 的要点

**要写**：服装材质与颜色、发型、表情、姿态、场景、光线
**不用写**：五官长相（参考图已决定，写多了反而会打架）

对比示例：

| | 效果 |
| --- | --- |
| ❌ "一个漂亮的亚洲女孩穿西装" | 脸会变，被当成新角色 |
| ✅ "穿深灰色修身职业西装外套配白衬衫，头发盘成低马尾，微微一笑，浅灰摄影棚背景，专业人像布光" | 脸保持，只换装 |

## 常见问题

**Q: 报 `参考图请通过 /v1/images/edits 上传`**
A: 这是打到了 `/generations` 端点。用本脚本（走 `/edits`）即可，或在面板里改用 `hy-image-3.5`。

**Q: 脸还是变了**
A: ① 参考图要清晰正脸、光线均匀、无遮挡；② 确认没传 `--no-lock`；③ 换装描述别写"另一个人""不同女孩"这类词。

**Q: 想要竖构图 / 更大尺寸**
A: `--size 768x1024` 或 `--size 1024x1536`。部分模型对大尺寸支持有限，失败时回退 `1024x1024`。

**Q: 想要完全免费**
A: 用 Kaggle 渠道的 `kaggle-turbo`，1024×1536、无水印，但需要 Kaggle 会话在线，约 103 秒/张。
