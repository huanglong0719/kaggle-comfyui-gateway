# Kaggle ComfyUI Gateway

把 **Kaggle 免费 T4×2 GPU** 变成 OpenAI 兼容的生图 API，接入 DeepSeek Harness（DSH）渠道，用 **固定 Cloudflare 域名**长期复用。

A free OpenAI-compatible image-generation gateway backed by Kaggle's free T4×2 GPUs and ComfyUI.

---

## 为什么做这个

Kaggle 每周免费送 30 小时双 T4 GPU，但只能在 Notebook 里手动点。这个项目把它变成：

- **一个固定 URL** —— `https://your-subdomain.your-domain/v1/images/generations`
- **OpenAI 兼容协议** —— 任何支持 `/images/generations` 的客户端都能直接用
- **双卡并行** —— 批量出图吞吐约 2 倍
- **人物一致性** —— 同一张脸换衣着、换动作、换场景
- **1080p / 2K 高清** —— 低分生成 + AI 超分，比直生大图快 4 倍

零成本，无信用卡。

## 架构

```
客户端 / DSH 生图面板
  └─ 渠道 kaggle (OpenAI /v1/images/generations)
       └─ https://<sub>.<domain>/v1              ← Cloudflare 命名隧道（地址固定）
            └─ Kaggle 会话内网关 :8819            ← scripts/comfyui_gateway_cell.py
                 ├─ ComfyUI :8188 (CUDA_VISIBLE_DEVICES=0)
                 └─ ComfyUI :8189 (CUDA_VISIBLE_DEVICES=1)   ← 第二张卡并行用
                      └─ Qwen-Image-2.1-Turbo FP8 + 4x-UltraSharp
```

## 性能实测

| 请求 | 实际输出 | 耗时 |
| --- | --- | --- |
| 文生图 `size:"16:9"` | 1024×576 | ~105s |
| 高清 `size:"1920x1080"+upscale:true` | **1920×1080** | **92s** |
| 2K `size:"2k"` | 2048×1152 | ~100s |
| 批量 `n:2`（双卡并行） | 2 张 | ~90s |
| 人物一致性（参考图） | 1024×1536 | ~103s |

对比：直接生成 1920×1080 需要 **396 秒** —— 所以高清一律走超分路径。

## 快速开始

### 1. 前置准备

- Cloudflare 托管域名（免费二级域也可）
- Cloudflare API Token（`Account·Cloudflare Tunnel·Edit` + `Zone·DNS·Edit`，**DNS 必须是 Zone 级**）
- Kaggle 账号 + API Token

### 2. 建命名隧道

见 [`docs/verified-values.md`](docs/verified-values.md) 与 [`SKILL.md`](SKILL.md) 的「一次性准备」章节，包含完整的 PowerShell 脚本：

```powershell
# 建隧道 → 取凭证 → 配 ingress → 建 CNAME
$tid = (Invoke-RestMethod ".../cfd_tunnel" -Headers $h -Method POST -Body $body).result.id
$tk  = (Invoke-RestMethod ".../cfd_tunnel/$tid/token" -Headers $h).result
# ingress 必须配，否则 530/503
Invoke-RestMethod ".../cfd_tunnel/$tid/configurations" -Headers $h -Method PUT -Body $cfg
```

### 3. 部署到 Kaggle

把两个脚本拼成 3~4 个 cell 的 Notebook，配好 `templates/kernel-metadata.json`：

```bash
kaggle kernels push -p <目录>
# 或在 Kaggle 编辑器里点 Start session → Run All
```

**隧道凭证不要硬编码**，通过环境变量注入：

```python
TUNNEL_TOKEN = os.environ.get("CF_TUNNEL_TOKEN", "")
```

在 Kaggle Notebook 的 Add-ons → Secrets 里加 `CF_TUNNEL_TOKEN` 即可。

### 4. 接进 DSH（可选）

改 `~/.dsh/profiles/desktop/cordis.patch.yml`：

```yaml
- id: imagegen
  name: "@q253595422/dsh-imagegen-video"
  config:
    channels:
      - id: <new-uuid>
        name: kaggle
        apiUrl: https://<sub>.<domain>/v1/images/generations
        apiUrlFull: true       # 完整端点，绕过某些模型的原生协议分支
        protocol: images
        models:
          - alias: kaggle-turbo
            id: qwen-image-2.1-turbo
    channelSecrets:
      <new-uuid>: any-value    # 网关不校验
```

改完用 `plugin_manager` 重载 `include:imagegen`（停用再启用），不用重启 DSH。

## 一致性角色（同一张脸换衣着/动作/表情）

三种入口按需选，详见 [`docs/consistency-usage.md`](docs/consistency-usage.md)：

| 入口 | 适用模型 | 水印 | 速度 |
| --- | --- | --- | --- |
| DSH 面板 `edit_image` | `hy-image-3.5` | ⚠️ WORKBUDDY | ~60s |
| **`scripts/consistency_gen.py`** ⭐ | `doubao-seedream-5-lite` 等 | 无 | **~30s** |
| Kaggle 渠道 | `kaggle-turbo` | 无 | ~103s |

```bash
# 单张
python consistency_gen.py --ref 基准图.png --prompt "换深灰西装，盘发，微笑" --out out.png

# 批量（同一张脸，多个造型）
python consistency_gen.py --ref 基准图.png --batch examples/consistency_prompts.json --outdir ./variants
```

脚本会自动给 prompt 加身份锁定前缀，并走本地网关唯一接受的 `/v1/images/edits` + multipart 格式。
之所以需要这个脚本：DSH 插件对 `seedream`/`agnes` 会强制把图生图发到 `/generations`（JSON），
而本地网关要求参考图走 `/edits`，于是报 400。

## 关键实现点

这些是实际踩出来的，都在 [`docs/troubleshooting.md`](docs/troubleshooting.md) 有详细排查步骤：

| 问题 | 解法 |
| --- | --- |
| ComfyUI「未就绪」但实际在跑 | 新版 `/system_info` 返回 **404**，改用 **socket 探端口** |
| 第二张卡一直空转 | 客户端 `count>1` 会并发多个 `n=1`，网关必须**轮询选实例** |
| 第二实例起来不监听端口 | 不能用 `--cuda-device`，要用 **`CUDA_VISIBLE_DEVICES`** 环境变量 |
| Cloudflare 524 | 生成期间**写空格心跳**（合法 JSON 前导空白）|
| 上报「非 JSON 响应」 | 不是格式问题，是 **240s 超时**，body 读一半被打断 |
| 超分出鱼骨条纹 | **放大后再缩回**目标（等效 2.5x），不要 4x 直出 |
| `safetensors header too large` | 下载路径拼错，拿到 404 页面；扩散模型在**仓库根目录** |

## 显存与限制

- 模型组合 FP8(7.13GB) + int8 文本编码器(9.35GB) ≈ **16.5GB**，超过单卡 15GB，靠 ComfyUI 动态 VRAM 调度硬撑
- RAM 也会接近 Kaggle 的 30GB 上限，双实例时约 26GB
- Kaggle 会话关机即销毁，每次启动需重新下载 20GB（约 3 分钟）
- 两张 T4 **不能**合并显存或做张量并行（无 NVLink），只能跑两个独立实例

## 目录结构

```
.
├── SKILL.md                    # 完整技能文档（DSH skill 格式）
├── scripts/
│   ├── comfyui_kaggle_cell.py  # Cell 1：装 ComfyUI + 下模型 + 起双实例
│   └── comfyui_gateway_cell.py # Cell 2：OpenAI 网关 + 命名隧道
├── docs/
│   ├── troubleshooting.md      # 按现象查的故障手册
│   └── verified-values.md      # 实测参数与耗时
└── templates/
    └── kernel-metadata.json    # Kaggle push 模板
```

## 安全提示

- 隧道域名**无鉴权**，知道地址的人都能消耗你的额度，不要外传
- 本项目所有凭证都已替换为占位符（`<YOUR_...>`），请勿把真实 token 提交进仓库
- 用完在 Kaggle 后台 Stop Session，否则持续消耗每周 30 小时额度

## License

MIT
