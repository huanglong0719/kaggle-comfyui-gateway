# 已验证的具体参数（2026-11-15 实测）

这套值在本机跑通过，可直接复用。全部数据来自实际运行，不是推测。

## Cloudflare

| 项 | 值 |
| --- | --- |
| 账户 ID | `<YOUR_CF_ACCOUNT_ID>` |
| Zone | `<YOUR_DOMAIN>`（ID `65ae50752bdb98225b7ac0d9bc8d0ac2`） |
| 隧道名 | `kaggle-comfyui` |
| 隧道 ID | `<YOUR_TUNNEL_ID>` |
| 固定域名 | `<YOUR_SUBDOMAIN>.<YOUR_DOMAIN>` |
| CNAME | `→ 40f9030d-....cfargotunnel.com`（proxied） |
| ingress | `<YOUR_SUBDOMAIN>.<YOUR_DOMAIN> → http://localhost:8819` |
| API Token 文件 | `./\cf_token.txt` |
| 隧道凭证文件 | `./\tunnel_token.txt`（也已内嵌在 gateway cell） |

## Kaggle

| 项 | 值 |
| --- | --- |
| 用户名 | `<YOUR_KAGGLE_USERNAME>` |
| Notebook | `<YOUR_KAGGLE_USERNAME>/comfyui-kaggle-free-gpu` |
| CLI | `C:\Python311\Scripts\kaggle.exe`（v2.2.5） |
| 凭证 | `C:\Users\long\.kaggle\kaggle.json` |
| 同时 GPU 会话上限 | 2（超出报 `Maximum batch GPU session count`） |

## 模型与超分

| 项 | 值 |
| --- | --- |
| 仓库 | `abenzerps/Qwen-Image-2.1-Turbo-Quantized`（hf-mirror 镜像） |
| 扩散模型 | `qwen-image-2.1-turbo-fp8.safetensors`（7.13GB，**仓库根目录**） |
| 文本编码器 | `text_encoders/qwen3vl_8b_int8_convrot.safetensors`（9.35GB） |
| VAE | `vae/qwen_image_2.1_vae_bf16.safetensors`（675MB） |
| 超分模型 | `4x-UltraSharp.pth`（66.9MB，`hf-mirror.com/lokCX/4x-Ultrasharp`） |
| 采样 | 8 步，`euler`，CFG 1.0，ManualSigmas 固定序列 |

## 实测耗时（T4×2，FP8，8 步 Turbo）

| 请求 | 实际输出 | 耗时 |
| --- | --- | --- |
| `size: "1:1"` | 1024×1024 | ~110s |
| `size: "16:9"` | 1024×576 | ~105s |
| **`size:"1920x1080" + upscale:true`** | **1920×1080** | **92s** |
| `size: "2k"` | 2048×1152 | ~100s |
| `size:"1920x1080"` 不超分 | 1920×1088 | 396s（太慢，禁用） |
| 生成 480 → 4x 直出 | 1920×1024 | 38s（**有鱼骨伪影**，已弃用） |
| `n=2` 双卡并行（640×640） | 2 张 | 86s |
| 并发 2 个 `n=1` | 2 张 | 74s |
| `edit` 参考图 | 1024×1536 | ~103s |
| 1080p 连出 6 张 | 6×1920×1080 | 约 9 分钟（84~103s/张） |

## DSH 渠道

| 项 | 值 |
| --- | --- |
| 配置文件 | `C:\Users\long\.dsh\profiles\desktop\cordis.patch.yml` |
| 插件 id | `imagegen`（module `@q253595422/dsh-imagegen-video`） |
| 重载目标 | `include:imagegen` |
| 渠道 | `name: kaggle`，`apiUrlFull: true`，`protocol: images` |
| 模型别名 | `kaggle-turbo` → `qwen-image-2.1-turbo` |
| 备份 | `cordis.patch.yml.bak-kaggle-20261115-145658` |

## 工作目录

`./\`
- `comfyui_kaggle_cell.py` / `comfyui_gateway_cell.py` — 两个 cell 源文件（v23）
- `comfyui_kaggle_cell.ipynb` / `kernel-metadata.json` — push 用的组装件
- `comfyui_video_cell.py` — Wan2.2 文生视频（121 帧，T4 约 30 分钟）
- `wf/` — 官方工作流 JSON 备份
- `video_run3/zhangxue_water_drift.mp4` — 已生成的视频样例
- `lqx/` — 林青霞六风格 1080p 成品
