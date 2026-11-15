# 故障排查手册

按现象查。每条都来自实际踩坑。

## 域名返回 1033

**含义**：域名配了 Tunnel，但 CF 找不到任何在线连接器（比 530 更明确）。

最常见根因不是 CF，而是 **Kaggle 里 ComfyUI 没起来 → 网关启动时 `raise RuntimeError("没有可用的 ComfyUI 实例")` → Cell 2 直接失败 → 隧道从未启动**。

诊断顺序：
1. 拉运行日志：`kaggle kernels output <user>/<slug> -p <目录>`，看有没有「cuda:0 未就绪」
2. 若出现「未就绪」，问题在 ComfyUI 启动参数（见下条）
3. 看 Cell 2 是否抛 `RuntimeError: 没有可用的 ComfyUI 实例`

## ComfyUI 起来但「未就绪」（端口不监听）

### 头号原因：用 `/system_info` 探测就绪（已踩多次）

**ComfyUI 0.45.0 的 `/system_info` 会返回 404**。用 `urllib.request.urlopen(".../system_info")`
探测时，404 抛 `HTTPError`，被 `except` 吞掉后当作「未就绪」——**但 ComfyUI 其实早就正常在跑**。

表现为：cell 里反复「警告: cuda:0 未就绪」，随后 Cell 2 抛
`RuntimeError: 没有可用的 ComfyUI 实例`，隧道不启动，域名 1033/530。
而此时用浏览器打开 cloudflared 给的 trycloudflare 链接，ComfyUI 首页**返回 200 正常显示**。

**正确做法：用 socket 探测端口，不依赖任何 HTTP 端点**

```python
import socket

def port_open(port, timeout=2):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except Exception:
        return False
```

网关侧探测实例同样要用 socket，不要用 `/system_info`。

### 次因：启动参数不兼容

**不要给这个版本的 ComfyUI 加 `--cuda-device` / `--output-directory`。**
实测加了之后进程 pid 存在但 8188 端口不开。只用：

```python
subprocess.Popen(["python", "main.py", "--listen", "0.0.0.0", "--port", "8188"],
                 cwd=COMFY, stdout=open(log, "w"), stderr=subprocess.STDOUT)
```

若确实需要指定卡，改用环境变量 `CUDA_VISIBLE_DEVICES=1`。

## 域名返回 530

**含义**：Cloudflare 找不到连接器（会话没跑，或 cloudflared 没连上）。

检查顺序：
1. Kaggle 会话是否在跑：`kaggle kernels status <user>/<slug>` 是 `RUNNING` 还是 `COMPLETE`
2. 无头运行的 cell 跑完会话就销毁 → 隧道消失。验证时加保活 cell，长期使用用**交互会话**
3. 隧道 ingress 规则是否配好（`PUT .../cfd_tunnel/<id>/configurations`），缺了会 530/503

## 域名返回 503

**含义**：连接器在线，但没有可用的 ingress 路由。

→ 补 ingress 规则，`service` 必须指向网关端口（默认 `http://localhost:8819`），最后一条兜底 `http_status:404`。

## 域名返回 524

**含义**：Cloudflare 等源站超过 ~100 秒。

→ 网关必须「先发响应头 + 生成期间每 10s 写一个空格」。空格是合法 JSON 前导空白，客户端 `JSON.parse` 不受影响。

## DSH 报「上游接口返回了非 JSON 响应（HTTP 200）」

**这不是格式问题，是超时。** 插件 `readResponseText()` 在 240s 预算超时后 catch 返回空串，`JSON.parse("")` 失败，被误报成非 JSON。

排查：
1. 单图耗时是否 > 240s（`UPSTREAM_TIMEOUT_MS = 24e4`）
2. 尺寸是否 >768 长边
3. 模型是否冷加载（网关启动时要预热）

验证方法：绕开插件直连，看真实响应：
```bash
python -c "import requests; r=requests.post('https://<域名>/v1/images/generations', json={'model':'kaggle-turbo','prompt':'test','size':'1:1'}, timeout=900); print(r.status_code, len(r.content), r.content[:80])"
```

## 加载报 `safetensors header is too large`

**不是格式问题，是下载到了 404 页面。**

扩散模型在 HF 仓库**根目录**，不在 `diffusion_models/` 子目录：

| 文件 | 远程路径 |
| --- | --- |
| 扩散模型 | `<repo>/resolve/main/qwen-image-2.1-turbo-fp8.safetensors` |
| 文本编码器 | `<repo>/resolve/main/text_encoders/qwen3vl_8b_int8_convrot.safetensors` |
| VAE | `<repo>/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors` |

下载后必须校验大小：fp8 7.13GB / te 9.35GB / vae 675MB。

## 加载报 `Unknown model architecture`

→ 用了 GGUF 格式。city96 的 `UnetLoaderGGUF` 不支持 Qwen-Image-2.1 架构。改 FP8 safetensors。

## ComfyUI 返回 400 `prompt_outputs_failed_validation`

读 `node_errors` 里具体哪个节点哪个字段。已踩过的：

| 节点 | 字段 | 正确值 |
| --- | --- | --- |
| `TextEncodeQwenImage21` | 文本参数名 | **`prompt`**（不是 `text`） |
| `TextEncodeQwenImage21` | `resolution` | **必填**（1024 / 2048） |
| `ManualSigmas` | `sigmas` | 字符串 `"1.0, 0.978453, ..."` |

## 超分相关（1080p/2K/4K）

### 出图有鱼骨状条纹伪影

**原因**：生成尺寸太小就 4x 放大（如 480×256 → 1920），训练纹理被拉伸重复。

**修法**：生成到目标的 1/2.5（如 768×432），4x 放大到 3072 后用 `ImageScale`(lanczos)
缩回 1920。等效 2.5x 放大，伪影消失。实测 92s / 张。

### 超分不生效，出图还是小尺寸

检查 Console 里的 `超分模型: 4x-UltraSharp.pth` 那行：
- 显示「未找到」→ Cell 1 下载失败，检查 `models/upscale_models/4x-UltraSharp.pth` 是否存在（应 66.9MB）
- 显示模型名但尺寸没变 → 请求没带 `upscale: true`，或 `size` 不是 `1080p/2k/4k` 档位名

### 直生大图特别慢（396 秒）

这是正常的。1920×1088 的像素量是 768×432 的 6.3 倍，而 T4 显存本就吃紧（16.5GB > 15GB），
大图让 swap 次数激增。**不要直生 1080p，一律走超分路径。**

### 超分后尺寸是 1920×1024 而不是 1920×1080

生成尺寸取整到 8 的倍数导致的（480×256 → 4x = 1920×1024）。
用「目标 1/2.5 + 缩放回目标」的方案就不会有这个问题，能精确出 1920×1080。

## push 报 `Maximum batch GPU session count of 2 reached`

→ Kaggle 同时最多 2 个 GPU 会话，先停旧的。

停会话位置：Notebook **版本页**（不是编辑器）→ 左下 `View Active Events` → 每行 `⋯` → `Stop Session`。

编辑器页可点 `Session options`（⋮ 菜单）→ `Start session`；**关闭会话**在版本页的 Active Events 里。

## PowerShell 相关

- `kernel-metadata.json` **不能带 BOM**，否则 `kaggle kernels push` 报 `Unexpected UTF-8 BOM`。用 Python `json.dump` 写，别用 `Set-Content -Encoding UTF8`。
- `Invoke-RestMethod` 读错误响应流容易抛 NRE，用 `try { } catch { $_.Exception.Message }` 即可，别深挖 `GetResponseStream()`。
- 后台执行器本身是 pwsh，脚本里再套 `pwsh -File` 会 `CommandNotFoundException`；直接把命令原文交给 `run_in_background`。未签名 `.ps1` 会被执行策略挡。

## hf-mirror 路径

`hf-mirror.com/<repo>/resolve/main/...` 可用；`workflow_templates` 仓库在 hf-mirror 返回 401，改用 `ghproxy.net/https://raw.githubusercontent.com/...`。
