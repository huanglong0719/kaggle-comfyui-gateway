---
name: kaggle-comfyui-gateway
description: 在 Kaggle 免费 GPU（T4×2）上搭 ComfyUI 并暴露成 OpenAI 兼容生图接口，接入 DSH「生图配置」渠道，用固定 Cloudflare 域名长期复用；当用户要在 Kaggle 跑生图/生视频模型、想把免费 GPU 接进 DSH、需要固定域名隧道、或排查该链路的 524/超时/模型加载错误时使用。
---

# Kaggle 免费 GPU + ComfyUI + 固定域名 DSH 网关

把 Kaggle 免费 T4×2 变成 DSH 可直接调用的生图后端。**全部免费**（Kaggle 每周 30 小时 GPU 额度）。

## 链路总览

```
DSH 生图面板
  └─ 渠道 kaggle (OpenAI /v1/images/generations)
       └─ https://<子域>.<你的域>/v1        ← Cloudflare 命名隧道（固定）
            └─ Kaggle 会话内网关 :8819      ← Cell 2
                 ├─ ComfyUI :8188 (cuda:0)
                 └─ ComfyUI :8189 (cuda:1)  ← 批量时并行用第二张卡
```

## 一次性准备（只做一次）

1. **Cloudflare 托管域名**（免费二级域也可，如 `xxx.cc.cd`）
2. **CF API Token**：My Profile → API Tokens → Custom Token
   - `Account · Cloudflare Tunnel · Edit`
   - `Zone · DNS · Edit`（**必须是 Zone 级**，Account 级 DNS 权限无效！）
   - 不要设 TTL / IP 白名单
3. **Kaggle API Token**：Kaggle → Settings → API → Create New Token → `kaggle.json`
   放 `~/.kaggle/kaggle.json`

### 建命名隧道 + CNAME

```powershell
# 存 token，别贴聊天里
[IO.File]::WriteAllText("$PWD/cf_token.txt", 'cfat_...')

$t = (Get-Content cf_token.txt -Raw).Trim()
$h = @{ "Authorization" = "Bearer $t"; "Content-Type" = "application/json" }

# 1) 取账户 / zone
$acc  = (Invoke-RestMethod "https://api.cloudflare.com/client/v4/accounts" -Headers $h).result[0].id
$zone = (Invoke-RestMethod "https://api.cloudflare.com/client/v4/zones" -Headers $h).result |
        Where-Object name -eq '你的域名' | Select-Object -ExpandProperty id

# 2) 建隧道
$body = '{"name":"kaggle-comfyui","config_src":"cloudflare"}'
$tid = (Invoke-RestMethod "https://api.cloudflare.com/client/v4/accounts/$acc/cfd_tunnel" `
        -Headers $h -Method POST -Body $body).result.id

# 3) 取隧道运行凭证（注意：GET，result 直接是 token 字符串）
$tk = (Invoke-RestMethod "https://api.cloudflare.com/client/v4/accounts/$acc/cfd_tunnel/$tid/token" `
       -Headers $h).result

# 4) ingress 规则（命名隧道必须有，否则 530/503）
$cfg = @{ config = @{ ingress = @(
  @{ hostname = "comfyui.你的域名"; service = "http://localhost:8819" },
  @{ service = "http_status:404" }) } } | ConvertTo-Json -Depth 6
Invoke-RestMethod "https://api.cloudflare.com/client/v4/accounts/$acc/cfd_tunnel/$tid/configurations" `
  -Headers $h -Method PUT -Body $cfg

# 5) CNAME 指向隧道
$dns = @{ type="CNAME"; name="comfyui"; content="$tid.cfargotunnel.com"; proxied=$true } | ConvertTo-Json
Invoke-RestMethod "https://api.cloudflare.com/client/v4/zones/$zone/dns_records" `
  -Headers $h -Method POST -Body $dns
```

把 `$tk` 填进 `scripts/comfyui_gateway_cell.py` 的 `TUNNEL_TOKEN`，`$tid` 记下来。

## 每次启动（约 10 分钟）

1. 把 `scripts/comfyui_kaggle_cell.py`、`scripts/comfyui_gateway_cell.py` 组装成 3~4 个 cell 的 ipynb，
   配 `templates/kernel-metadata.json`（改 `id` 为 `<用户名>/<slug>`）
2. `kaggle kernels push -p <目录>`（会排队运行；**排队不等于运行**，要确认状态）
3. 或在 Kaggle 编辑器里点 **Start session → Run All**
4. 等 `https://<子域>.<你的域>/v1/models` 返回 200

**探测节奏**：启动阶段（装 ComfyUI + 下 20GB 模型 + 起双实例）至少要 8~10 分钟，
不要一开始就高频轮询——先等 5 分钟，之后每 30 秒探一次即可。域名在会话就绪前
依次经历 `530`（无连接器）→ `502`（连接器断开）→ `200`（就绪）。

### 刷新网页 ≠ 关机会话

- **刷新网页（F5）**：后端 kernel 仍在跑，域名照样通。编辑器会显示 `Draft Session off`，
  那只是页面连接断了——**此时千万别点 Run All**，否则会新建会话并重下 20GB。
- **Stop Session / 关机**：容器销毁，`/tmp` 与 `/kaggle/working` 全部清空，必须重跑。

判断要不要重启，看域名而不是看页面：

```powershell
# 200 = 会话活着，什么都别动；530/502 = 已死，才需要重新 Run All
Invoke-RestMethod "https://<YOUR_SUBDOMAIN>.<YOUR_DOMAIN>/v1/models"
```

## DSH 渠道配置

改 `~/.dsh/profiles/desktop/cordis.patch.yml`（**不是 settings.yaml**）：

```yaml
- id: imagegen
  name: "@q253595422/dsh-imagegen-video"
  config:
    channels:
      # ... 已有渠道 ...
      - id: <新UUID>
        preset: ""
        name: kaggle
        apiUrl: https://comfyui.你的域名/v1/images/generations
        apiUrlFull: true          # 完整端点，绕过 qwen-* 的 DashScope 原生分支
        watermark: true
        protocol: images
        models:
          - alias: kaggle-turbo
            id: qwen-image-2.1-turbo
    channelSecrets:
      <新UUID>: kaggle             # 网关不校验，随便填
```

**改完必须重载插件**（不用重启 DSH）：
```
plugin_manager set_plugin target="include:imagegen" enabled=false
plugin_manager set_plugin target="include:imagegen" enabled=true
```

## 硬限制（全部实测踩过）

| 限制 | 数值 | 表现 | 对策 |
| --- | --- | --- | --- |
| Cloudflare 单请求 | ~100s | HTTP **524** | 网关先发头 + 每 10s 写空格心跳 |
| DSH 插件上游超时 | **240s**（`UPSTREAM_TIMEOUT_MS`） | 误报「非 JSON 响应（HTTP 200）」 | 按「实测耗时总表」选尺寸 + 启动预热 |
| Kaggle 并发 GPU 会话 | 2 | push 报 `Maximum batch GPU session count` | 先停旧会话 |
| 免费隧道 | 每次随机域名 | 地址变 | 用**命名隧道**固定 |
| 无头运行 | cell 跑完即销毁 | 隧道消失 | 加保活 cell，或改用交互会话 |

## ⚠️ 版本切换纪律（最容易翻车的地方）

**同一个命名隧道可以被多个会话同时连接，Cloudflare 会把请求随机分发给任意一个连接器。**

后果：你以为在测新代码，实际请求被打到了还在跑的旧版本会话上——症状是「新功能好像没生效」，
但日志/代码怎么看都对。实测时曾出现 3 个会话（交互会话 + v13 + v14）同时在线，
`n=4` 的批量请求只返回 1 张，因为路由到了旧代码。

**每次推送或启动新版本，必须先清干净旧会话：**

1. 打开 Notebook 的**版本页**（`/code/<user>/<slug>`，不是 `/edit`）
2. 左下角 `View Active Events`（数字 = 当前活动会话数）
3. 逐行点 `⋯` → `Stop Session`，除了要保留的那一个
4. 确认数字降到 1，再做下一步

另外注意：**编辑器页面的代码在你 push 之后不会自动更新**。push 后要在浏览器里
**刷新页面**，编辑器的 Draft Session 才会加载新代码，否则 Run All 跑的仍是旧代码。

停完会话后域名会先返回 502/530（连接器断开），新会话起来后自动恢复，不用改 DSH。

## 模型选择（Qwen-Image-2.1-Turbo 量化版）

| 格式 | 结果 | 原因 |
| --- | --- | --- |
| FP8 safetensors | ✅ **可用** | 标准 UNETLoader 可直接加载 |
| GGUF (Q4/Q8) | ❌ | city96 GGUF 加载器不认该架构（Unknown model architecture） |
| INT8 ConvRot | ❌ | header 过大，标准加载器拒收 |

**下载路径陷阱**：扩散模型在 HF 仓库**根目录**，`text_encoders/` 和 `vae/` 才在子目录。
拼错会拿到 15 字节 404 页面，加载时报 `safetensors header is too large`（极易误判为格式问题）。
必须在下载后校验文件大小（fp8 7.13GB / te 9.35GB / vae 675MB）。

## 人物一致性（参考图 / 换衣着换表情）

通过 `/v1/images/edits` 实现，已在 DSH 的 `edit_image` 工具上验证通过（同一张脸换 5 套造型五官完全一致）。

**工作流接线**：

```
参考图 ──LoadImage──► TextEncodeQwenImage21.images ──┐
                                                    ├─► 采样 ─► 出图
描述文字（衣服/动作/表情/场景）─────────────────────┘
```

`TextEncodeQwenImage21` 的 `images` 支持 **1~16 张**（`image_1` … `image_16`），是官方原生能力，不需要 IP-Adapter。

**网关侧要做三件事**：
1. 解析 `multipart/form-data`（用 `email.parser.BytesParser`，`cgi` 模块在 Python 3.13 已移除）
2. 把参考图 `POST /upload/image` 上传到**每个要用到的** ComfyUI 实例，拿到返回的文件名
3. 工作流里加 `LoadImage` 节点，把 `te_inputs["images"] = {"image_1": ["6", 0]}` 接上

**prompt 写法很关键**——开头必须明确锁定身份：

> 保持这位女性的面部特征和身份完全不变（同样的脸型、眼睛、鼻子、嘴唇、皮肤），改为：<新衣着>，<新动作/表情>，<新场景>

编辑路径输出的尺寸由 `resolution` 决定（1024 档 → 1024×1536）。

## 高清输出（1080p / 2K / 4K）

**核心策略：低分生成 → 4x-UltraSharp 超分 → lanczos 缩回目标**

```
目标 1920×1080 → 生成 768×432（约 75s）→ 4x 放大到 3072×1728 → 缩回 1920×1080（约 17s）
                                                                  合计约 92 秒
```

为什么不能直接生成大图（实测数据）：

| 做法 | 耗时 | 画质 |
| --- | --- | --- |
| 直生 1920×1080 | **396 秒** | 无伪影，但太慢（6 张要 40 分钟） |
| 生成 480 → 4x 直出 1920 | 38 秒 | ❌ 山体/皮肤出现鱼骨条纹（4x 纹理拉伸） |
| **生成 768 → 4x → 缩回 1920** | **92 秒** | ✅ 干净，等效 2.5x 放大 |

**关键**：先放大再**缩回**。4x 模型放大到 3072 后用 `ImageScale`(lanczos) 缩到 1920，
相当于让 4x 模型干 2.5x 的活，纹理不会被拉伸失真。

工作流片段：

```python
g["20"] = {"class_type": "UpscaleModelLoader", "inputs": {"model_name": "4x-UltraSharp.pth"}}
g["21"] = {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["20",0], "image": ["12",0]}}
g["22"] = {"class_type": "ImageScale", "inputs": {"image": ["21",0], "method": "lanczos",
           "width": target_w, "height": target_h, "crop": "disabled"}}
```

超分模型：`4x-UltraSharp.pth`（66.9MB），放 `models/upscale_models/`，
下载源 `https://hf-mirror.com/lokCX/4x-Ultrasharp/resolve/main/4x-UltraSharp.pth`。

**触发方式**：请求带 `upscale: true`，或 `size` 用档位名 `1080p` / `2k` / `4k`（自动启用）。

## 实测耗时总表（T4×2，FP8，8 步 Turbo）

| 请求 | 实际输出 | 耗时 | 备注 |
| --- | --- | --- | --- |
| `size: "1:1"` | 1024×1024 | ~110s | 默认比例档 |
| `size: "16:9"` | 1024×576 | ~105s | 默认比例档 |
| **`size:"1920x1080", upscale:true`** | **1920×1080** | **92s** | ⭐ 推荐高清路径 |
| `size: "2k"` | 2048×1152 | ~100s | 自动超分 |
| `size:"1920x1080"`（不超分） | 1920×1088 | 396s | ❌ 太慢，禁用 |
| 批量 `n=2`（双卡） | 2 张同尺寸 | ≈ 单张 +5s | 双实例并行 |
| 编辑（参考图） | 1024×1536 | ~103s | resolution=1024 档 |

**批量尺寸自动收敛**：`n=1` 允许到 1920 长边；`n=2` 收到 1280；`n≥3` 收到 640 —— 保证总时长仍在 DSH 的 240s 内。

## 参考图缓存

同一张参考图在同一会话内重复使用时，按 `sha256` 命中缓存直接复用 ComfyUI 里的文件，免去重新上传（2MB 大图能省 1~4 秒/次）。跨会话失效（容器销毁即清空），逻辑无副作用。

## 双卡说明

两张 T4 **不能**合并成 32GB 或 2× 单卡算力（无 NVLink，ComfyUI 不支持张量并行）。
但**可以**用两个独立实例让两张卡各干各的活 —— 已验证有效：

```python
for port, dev in ((8188, 0), (8189, 1)):
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(dev)   # 关键：用环境变量隔离，不要用 --cuda-device
    subprocess.Popen(["python", "main.py", "--listen", "0.0.0.0", "--port", str(port)],
                     cwd=COMFY, env=env, stdout=open(log,"w"), stderr=subprocess.STDOUT)
```

**实测数据（Qwen-Image-2.1-Turbo FP8，测试时用 640×640）**：

| 场景 | 单实例串行 | 双实例并行 |
| --- | --- | --- |
| 2 张 | ~170s | **86s（约 2×）** |
| 1 张 | ~80s | ~80s（无差别） |

> 另有并发验证：同时发 2 个 `n=1` 请求 → **74 秒**完成（证明网关轮询把两个请求分到了两张卡）。

注意点：
- `--cuda-device` 会让进程起来但不监听端口，**必须**改用 `CUDA_VISIBLE_DEVICES` 环境变量
- 两个实例共享 `models/`（只读安全），输出目录各自独立避免重名
- 显存：每个实例都要 16.5GB（FP8 7.13 + TE 9.35）> 单卡 15GB，各自 swap；RAM 也会吃紧（Kaggle 上限 30GB，会接近满载）
- 网关侧 `MAX_N = 2 if len(PORTS) == 1 else 4`，按实际实例数调整批量上限

## 相关文件

- `scripts/comfyui_kaggle_cell.py` — Cell 1：装 ComfyUI + 下模型 + 启双实例 + UI 隧道
- `scripts/comfyui_gateway_cell.py` — Cell 2：OpenAI 网关（双卡轮询/心跳/超分/参考图缓存）+ 命名隧道
- `references/troubleshooting.md` — 故障排查手册（按现象查）
- `references/verified-values.md` — 已验证的具体参数值（隧道 ID、域名、模型地址、实测耗时）

## 能力清单（v23 已验证）

| 能力 | 入口 | 实测 |
| --- | --- | --- |
| 文生图（比例档） | `size: 1:1 / 16:9 / 9:16 …` | 1024 级，约 105~110s |
| 高清文生图 | `size: 1920x1080 + upscale: true` | 1920×1080，92s |
| 2K | `size: "2k"` | 2048×1152，~100s |
| 批量 | `n: 2`（双卡并行） | 2 张约 90s |
| 人物一致性 + 换装 | `POST /v1/images/edits` | 1024×1536，~103s |

## 安全提醒

- 隧道域名**无鉴权**，知道地址的人都能消耗你的 GPU 额度，别外传
- CF Token、Kaggle Token 存文件，不要贴进对话
- 用完在 Kaggle 后台 **Stop Session**，否则持续消耗每周 30 小时额度
