# =====================================================================
# Kaggle 免费 GPU 跑 ComfyUI（Qwen-Image-2.1-Turbo 量化版）一键脚本
# ---------------------------------------------------------------------
# 前置：Kaggle Notebook · Settings → Accelerator = GPU T4 x2 · Internet = On
# 用法：整段粘贴到 Notebook 第 1 个 Cell → Shift+Enter 运行
#       等 5~10 分钟，输出里会出现一个 https://xxxx.trycloudflare.com 链接，
#       浏览器打开即是 ComfyUI 界面。
# 注意：每周 30 小时 GPU 额度；用完请在 Kaggle 后台 Stop Session，别挂着吃时长。
# =====================================================================
import os, re, subprocess, time, urllib.request

HOME = "/tmp"          # 大文件放 /tmp（会话盘大且不占 19.5G 持久盘）
COMFY = os.path.join(HOME, "ComfyUI")
os.chdir(HOME)

def sh(cmd, **kw):
    """跑 shell 命令，失败即抛异常，输出直接打到 cell。"""
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)

# ---------- 1) 克隆 ComfyUI + Manager + GGUF 加载器 ----------
if not os.path.exists(COMFY):
    sh(["git", "clone", "--depth", "1", "https://github.com/comfyanonymous/ComfyUI"])
    sh(["git", "clone", "--depth", "1", "https://github.com/ltdrdata/ComfyUI-Manager",
        os.path.join(COMFY, "custom_nodes", "ComfyUI-Manager")])
    sh(["git", "clone", "--depth", "1", "https://github.com/city96/ComfyUI-GGUF",
        os.path.join(COMFY, "custom_nodes", "ComfyUI-GGUF")])

# ---------- 2) 安装依赖 ----------
sh(["pip", "install", "-q", "-r", os.path.join(COMFY, "requirements.txt")])
gguf_req = os.path.join(COMFY, "custom_nodes", "ComfyUI-GGUF", "requirements.txt")
if os.path.exists(gguf_req):
    sh(["pip", "install", "-q", "-r", gguf_req])

# ---------- 3) 下载模型（走 hf-mirror，无需 HF Token）----------
# 注意：扩散模型在仓库【根目录】，text_encoder/vae 在各自子目录 —— 远程路径必须精确，
# 否则 hf-mirror 返回 404 小文件，加载时报 "safetensors header is too large"。
# 扩散模型用 FP8（README：标准 ComfyUI 加载器可直接载；GGUF/INT8 均不可用）。
REPO = "https://hf-mirror.com/abenzerps/Qwen-Image-2.1-Turbo-Quantized/resolve/main"
# (本地目录, 远程子目录, 文件名, 期望最小字节数)
FILES = [
    ("diffusion_models", "",              "qwen-image-2.1-turbo-fp8.safetensors",   7_000_000_000),
    ("text_encoders",    "text_encoders", "qwen3vl_8b_int8_convrot.safetensors",    9_000_000_000),
    ("vae",              "vae",           "qwen_image_2.1_vae_bf16.safetensors",    600_000_000),
]
for sub, remote_dir, fname, min_bytes in FILES:
    dst = os.path.join(COMFY, "models", sub, fname)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst) and os.path.getsize(dst) >= min_bytes:
        print("已存在，跳过:", fname, flush=True)
        continue
    remote = f"{REPO}/" + (f"{remote_dir}/" if remote_dir else "") + fname
    print("下载:", fname, "<-", remote, flush=True)
    sh(["curl", "-L", "-C", "-", "--retry", "5", "-sS", "-o", dst, remote])
    size = os.path.getsize(dst)
    if size < min_bytes:
        raise RuntimeError(f"{fname} 下载不完整 {size} 字节 (期望 >{min_bytes})，"
                           f"请检查远程路径: {remote}")
    print("  完成:", f"{size/1e9:.2f} GB", flush=True)

# ---------- 3.5) 超分模型（4x-UltraSharp，用于 2K/4K 输出）----------
UPSCALE_URL = "https://hf-mirror.com/lokCX/4x-Ultrasharp/resolve/main/4x-UltraSharp.pth"
up_dst = os.path.join(COMFY, "models", "upscale_models", "4x-UltraSharp.pth")
os.makedirs(os.path.dirname(up_dst), exist_ok=True)
if not (os.path.exists(up_dst) and os.path.getsize(up_dst) > 60_000_000):
    print("下载超分模型 4x-UltraSharp.pth", flush=True)
    subprocess.run(["curl", "-L", "-C", "-", "--retry", "5", "-sS", "-o", up_dst, UPSCALE_URL],
                   check=True)
    print("  完成:", f"{os.path.getsize(up_dst)/1e6:.0f} MB", flush=True)
else:
    print("超分模型已存在，跳过", flush=True)

# ---------- 4) 下载 cloudflared（免注册公网隧道）----------
CFD = "/tmp/cloudflared"
if not os.path.exists(CFD):
    sh(["wget", "-q", "https://github.com/cloudflare/cloudflared/releases/latest/download/"
        "cloudflared-linux-amd64", "-O", CFD])
os.chmod(CFD, 0o755)

# ---------- 5) 后台启动两个 ComfyUI 实例（各占一张 T4，真正并行） ----------
# 关键：第二张卡通过环境变量 CUDA_VISIBLE_DEVICES=1 限定，**不要**用 --cuda-device
# （该参数会让进程起来但不监听端口）。模型文件共享（只读），输出目录各自分开。
COMFY_INSTANCES = []
for port, dev in ((8188, 0), (8189, 1)):
    log = f"/tmp/comfyui_{port}.log"
    if os.path.exists(log):
        os.remove(log)
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(dev)     # 让该实例只看到一张卡
    p = subprocess.Popen(
        ["python", "main.py", "--listen", "0.0.0.0", "--port", str(port)],
        cwd=COMFY, env=env, stdout=open(log, "w"), stderr=subprocess.STDOUT)
    COMFY_INSTANCES.append((port, dev, p))
    print(f"ComfyUI 实例 cuda:{dev} 启动 pid={p.pid} port={port} log={log}", flush=True)

# 用 socket 探测端口（ComfyUI 新版 /system_info 返回 404，HTTP 探测会误判未就绪）
import socket

def port_open(port, timeout=2):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except Exception:
        return False

for port, dev, p in COMFY_INSTANCES:
    ready = False
    for _ in range(180):          # 每个最长 15 分钟（首次要装/编译）
        if port_open(port):
            print(f"  cuda:{dev} (port {port}) 就绪", flush=True)
            ready = True
            break
        if p.poll() is not None:
            print(f"  cuda:{dev} 进程已退出(exit {p.returncode})，日志尾部:", flush=True)
            try:
                print(open(f"/tmp/comfyui_{port}.log", errors="replace").read()[-2000:], flush=True)
            except Exception:
                pass
            break
        time.sleep(5)
    if not ready:
        print(f"  警告: cuda:{dev} 未就绪，日志尾部:", flush=True)
        try:
            print(open(f"/tmp/comfyui_{port}.log", errors="replace").read()[-2500:], flush=True)
        except Exception as e:
            print("   读取日志失败:", e, flush=True)

ready_ports = [p for p, d, proc in COMFY_INSTANCES if port_open(p)]
print(f"最终可用实例: {ready_ports}", flush=True)

# ---------- 6) 启动隧道并抓取公网链接 ----------
tunnel = subprocess.Popen(
    [CFD, "tunnel", "--url", "http://localhost:8188", "--no-autoupdate"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

url = None
deadline = time.time() + 120
while time.time() < deadline:
    line = tunnel.stdout.readline()
    if not line:
        time.sleep(0.3); continue
    m = re.search(r"https://[-a-z0-9]+\.trycloudflare\.com", line)
    if m:
        url = m.group(0); break
if not url:
    raise RuntimeError("120 秒内没拿到隧道链接，重跑本 Cell 即可（模型不会重复下载）")

# 等 ComfyUI 的 HTTP 服务就绪（最长 300 秒，首次启动要编译些东西）
for _ in range(100):
    try:
        urllib.request.urlopen("http://localhost:8188", timeout=2)
        break
    except Exception:
        time.sleep(3)

print()
print("=" * 60)
print("  ComfyUI 已就绪，浏览器打开：", url)
print("=" * 60)
print("  界面里：工作流 → 浏览模板 → 图像 → Qwen（加载对应模板）")
print("  模型选 unet/qwen-image-2.1-turbo-Q4_K_M.gguf，步数 4~8，CFG 1.0")
print("  出图结果在 ComfyUI/output；想取回本地见《Kaggle配置指南.md》")
