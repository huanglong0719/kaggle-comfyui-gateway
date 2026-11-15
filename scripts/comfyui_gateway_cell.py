# =====================================================================
# Cell 2：OpenAI 兼容网关 —— 让 DSH「生图配置」直接接入 Kaggle ComfyUI
# ---------------------------------------------------------------------
# 本 Cell 在 Kaggle 会话里起一个网关（端口 8819），实现：
#   GET  /v1/models                  → 返回模型列表
#   POST /v1/images/generations      → OpenAI 文生图协议，内部转 ComfyUI 工作流
# 并开第二条 cloudflared 隧道专门给 DSH 用（与 Cell 1 的 UI 隧道互不干扰）。
# 先跑 Cell 1（ComfyUI + 模型），再跑本 Cell。
# =====================================================================
import base64, glob, json, os, random, re, subprocess, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

COMFY = "http://127.0.0.1:8188"
GW_PORT = 8819
TURBO_SIGMAS = "1.0, 0.978453, 0.95418, 0.926626, 0.89508, 0.845148, 0.704534, 0.414568, 0"
# 双实例端口（Cell 1 分别在 cuda:0 / cuda:1 上启动）
ALL_PORTS = [8188, 8189]

import socket as _socket

def port_alive(port, timeout=2):
    """用 socket 探测端口。注意：ComfyUI 新版 /system_info 返回 404，
    用 HTTP 探测会被 HTTPError 误判为「未就绪」。"""
    try:
        with _socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except Exception:
        return False

# ---------- 等待 ComfyUI 实例就绪，筛出可用的 ----------
PORTS = []
for _ in range(40):
    PORTS = [p for p in ALL_PORTS if port_alive(p)]
    if len(PORTS) == len(ALL_PORTS):
        break
    time.sleep(3)
if not PORTS:
    raise RuntimeError("没有可用的 ComfyUI 实例，请先跑 Cell 1")
print(f"可用 ComfyUI 实例: {PORTS}（共 {len(PORTS)} 个）", flush=True)
MAX_N = 2 if len(PORTS) == 1 else 4
print(f"批量上限 n={MAX_N}（单实例时串行，240s 内最多 2 张）", flush=True)

def comfy_json(port, path, payload=None, timeout=30):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{port}" + path, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:600]
        raise RuntimeError(f"ComfyUI:{port} {path} -> HTTP {e.code}: {body}")

# ---------- 探测节点与模型文件（以第一个实例为准）----------
OI = comfy_json(PORTS[0], "/object_info")

def find_model(patterns):
    for p in patterns:
        hits = sorted(glob.glob(p))
        if hits:
            return os.path.basename(hits[0])
    return None

UPSCALE_MODEL = find_model(["/tmp/ComfyUI/models/upscale_models/4x-UltraSharp.pth",
                           "/tmp/ComfyUI/models/upscale_models/*.pth"])

UNET = find_model(["/tmp/ComfyUI/models/diffusion_models/*.safetensors",
                   "/tmp/ComfyUI/models/diffusion_models/*.gguf",
                   "/tmp/ComfyUI/models/unet/*.gguf",
                   "/tmp/ComfyUI/models/unet/*.safetensors"])
CLIP = find_model(["/tmp/ComfyUI/models/text_encoders/qwen3vl*.safetensors",
                   "/tmp/ComfyUI/models/text_encoders/*.safetensors"])
VAE  = find_model(["/tmp/ComfyUI/models/vae/*.safetensors"])
assert UNET and CLIP and VAE, "模型文件没找到，请先跑 Cell 1"
HAS_TENC21 = "TextEncodeQwenImage21" in OI
HAS_SIGMAS = "ManualSigmas" in OI
# safetensors 用标准 UNETLoader；仅当扩散模型是 .gguf 时才用 GGUF 加载器
USE_GGUF = UNET.endswith(".gguf") and "UnetLoaderGGUF" in OI
print(f"模型: {UNET} | {CLIP} | {VAE}")
print(f"节点: TextEncodeQwenImage21={HAS_TENC21} ManualSigmas={HAS_SIGMAS}")
print(f"超分模型: {UPSCALE_MODEL or '未找到（2K/4K 不可用）'}")

def fill_defaults(graph):
    """按 object_info 补全缺失的必填参数（用节点默认值）。"""
    for nid, node in graph.items():
        spec = OI.get(node["class_type"], {})
        req = spec.get("input", {}).get("required", {})
        for k, v in req.items():
            if k in node["inputs"]:
                continue
            if isinstance(v, list) and len(v) >= 2 and isinstance(v[1], dict) and "default" in v[1]:
                node["inputs"][k] = v[1]["default"]
            elif k == "noise_seed":
                node["inputs"][k] = random.randint(0, 2**48)
    return graph

def res_for(width, height):
    """TextEncodeQwenImage21 的 resolution 参数（参考图会按它缩放）。"""
    return 1024 if max(width, height) <= 1024 else 2048

def upload_image(port, filename, data, mime="image/png"):
    """把参考图上传到 ComfyUI 的 input 目录，返回 ComfyUI 侧的引用名。"""
    boundary = "----dsh" + str(random.randint(10**9, 10**10))
    parts = []
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode())
    parts.append(f"Content-Type: {mime}\r\n\r\n".encode())
    parts.append(data)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/upload/image", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        info = json.loads(r.read())
    # ComfyUI 返回 {name, subfolder, type}
    name = info.get("name") or filename
    sub = info.get("subfolder") or ""
    return f"{sub}/{name}" if sub else name

import hashlib as _hashlib

_img_cache = {}   # (port, sha256) -> ComfyUI 里的文件名

def get_or_upload(port, data, mime="image/png"):
    """同一张参考图在同一会话内只上传一次（大图能省 1~4 秒）。"""
    h = _hashlib.sha256(data).hexdigest()
    key = (port, h)
    if key in _img_cache:
        print(f"[gateway] 参考图命中缓存 {h[:12]}", flush=True)
        return _img_cache[key]
    name = upload_image(port, f"ref_{h[:12]}.png", data, mime)
    _img_cache[key] = name
    return name

def parse_multipart(body, content_type):
    """解析 multipart/form-data，返回 {字段名: (文件名或None, 字节或文本)}。"""
    from email.parser import BytesParser
    from email.policy import default as _policy
    raw = b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + body
    msg = BytesParser(policy=_policy).parsebytes(raw)
    fields = {}
    if not msg.is_multipart():
        return fields
    for part in msg.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        fname = part.get_filename()
        payload = part.get_payload(decode=True)
        fields[name] = (fname, payload, part.get_content_type())
    return fields

def build_graph(prompt, width, height, seed=None, ref_image=None, upscale=False,
                target=None):
    """Qwen-Image-2.1-Turbo 工作流。
    ref_image 不为空时，作为参考图接入 TextEncodeQwenImage21 的 images 输入
    （用于人物一致性：同一张脸换动作/表情/场景）。
    """
    if seed is None:
        seed = random.randint(0, 2**48)
    g = {}
    if USE_GGUF:
        g["1"] = {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": UNET}}
    else:
        g["1"] = {"class_type": "UNETLoader", "inputs": {"unet_name": UNET, "weight_dtype": "default"}}
    g["2"] = {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "qwen_image"}}
    g["3"] = {"class_type": "VAELoader", "inputs": {"vae_name": VAE}}
    if HAS_TENC21:
        te_inputs = {"clip": ["2", 0], "prompt": prompt, "negative_prompt": "",
                     "resolution": res_for(width, height)}
        if ref_image:
            g["6"] = {"class_type": "LoadImage", "inputs": {"image": ref_image}}
            te_inputs["images"] = {"image_1": ["6", 0]}
        g["4"] = {"class_type": "TextEncodeQwenImage21", "inputs": te_inputs}
        pos, neg = ["4", 0], ["4", 1]
    else:
        g["4"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}}
        g["6b"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": ""}}
        pos, neg = ["4", 0], ["6b", 0]
    g["5"] = {"class_type": "EmptySD3LatentImage",
              "inputs": {"width": int(width), "height": int(height), "batch_size": 1}}
    if HAS_SIGMAS:  # 官方 Turbo 8 步调度（推荐）
        g["7"] = {"class_type": "ManualSigmas", "inputs": {"sigmas": TURBO_SIGMAS}}
        g["8"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}}
        g["9"] = {"class_type": "BasicGuider",
                  "inputs": {"conditioning": pos, "model": ["1", 0]}}
        g["10"] = {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}}
        g["11"] = {"class_type": "SamplerCustomAdvanced",
                   "inputs": {"noise": ["10", 0], "guider": ["9", 0], "sampler": ["8", 0],
                              "sigmas": ["7", 0], "latent_image": ["5", 0]}}
        g["12"] = {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}}
    else:           # 兜底：普通 KSampler（CFG=1 时负向词无效）
        g["13"] = {"class_type": "KSampler",
                   "inputs": {"model": ["1", 0], "positive": pos, "negative": neg,
                              "latent_image": ["5", 0], "seed": seed,
                              "steps": 8, "cfg": 1.0, "sampler_name": "euler",
                              "scheduler": "simple", "denoise": 1.0}}
        g["12"] = {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["3", 0]}}
    final = ["12", 0]
    if upscale and UPSCALE_MODEL:
        g["20"] = {"class_type": "UpscaleModelLoader", "inputs": {"model_name": UPSCALE_MODEL}}
        g["21"] = {"class_type": "ImageUpscaleWithModel",
                   "inputs": {"upscale_model": ["20", 0], "image": ["12", 0]}}
        final = ["21", 0]
        if target:
            # 4x 放大后再缩到目标：等效 2.5x，伪影远小于直接 4x 输出
            g["22"] = {"class_type": "ImageScale",
                       "inputs": {"image": ["21", 0], "upscale_method": "lanczos",
                                  "width": int(target[0]), "height": int(target[1]),
                                  "crop": "disabled"}}
            final = ["22", 0]
    g["14"] = {"class_type": "SaveImage", "inputs": {"images": final, "filename_prefix": "dsh"}}
    return g

import itertools as _itertools

_rr_lock = threading.Lock()
_rr_counter = _itertools.count()

def pick_port():
    """轮询选实例。DSH 插件的 count>1 会并发发出多个 n=1 请求，
    轮询分配才能让两张卡同时干活（都发第一个实例就会退化成串行）。"""
    with _rr_lock:
        return PORTS[next(_rr_counter) % len(PORTS)]

def generate_one(port, prompt, width, height, seed, timeout=900, ref_name=None, upscale=False,
                 target=None):
    """在指定 ComfyUI 实例上生成一张图，返回 PNG 字节。ref_name 为参考图名。"""
    r = comfy_json(port, "/prompt",
                   {"prompt": build_graph(prompt, width, height, seed, ref_name, upscale, target)})
    pid = r["prompt_id"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        hist = comfy_json(port, "/history/" + pid)
        entry = hist.get(pid)
        if entry:
            st = entry.get("status", {})
            if st.get("status_str") == "error":
                raise RuntimeError("ComfyUI 执行失败: " + json.dumps(
                    [m for m in st.get("messages", []) if m[0] == "execution_error"])[:500])
            imgs = [i for out in entry.get("outputs", {}).values()
                    for i in out.get("images", [])]
            if imgs:
                img = imgs[0]
                q = (f"http://127.0.0.1:{port}/view?filename={img['filename']}"
                     f"&subfolder={img.get('subfolder','')}&type={img.get('type','output')}")
                with urllib.request.urlopen(q, timeout=60) as resp:
                    return resp.read()
        time.sleep(1.5)
    raise RuntimeError(f"生成超时（{timeout}s，port {port}）")

def generate_batch(prompt, width, height, n=1, timeout=900, ref_upload=None, upscale=False,
                   target=None):
    """批量生成 n 张：按实例数均分并行，每张独立随机 seed。
    ref_upload=(filename, bytes, mime) 时先上传参考图到各实例，用于人物一致性。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    n = max(1, min(int(n), MAX_N))
    seeds = [random.randint(0, 2**48) for _ in range(n)]

    # 参考图需要上传到「每个要用到的实例」
    ref_map = {}
    if ref_upload:
        fname, data, mime = ref_upload
        for p in PORTS:
            try:
                ref_map[p] = get_or_upload(p, data, mime)
            except Exception as e:
                print(f"[gateway] 参考图上传失败 port={p}: {e}", flush=True)
        print(f"[gateway] 参考图就绪: {ref_map}", flush=True)

    if n == 1:
        # 单张请求：轮询选实例（插件并发的多个单张请求会被均匀分散到各卡）
        port = pick_port()
        return [generate_one(port, prompt, width, height, seeds[0], timeout,
                             ref_map.get(port), upscale, target)]
    # 一次要多张：按实例分桶，桶内串行、桶间并行
    buckets = {p: [] for p in PORTS}
    for i, s in enumerate(seeds):
        buckets[PORTS[i % len(PORTS)]].append(s)

    results = {}
    def run_port(port, seed_list):
        out = []
        for s in seed_list:
            out.append((s, generate_one(port, prompt, width, height, s, timeout,
                                        ref_map.get(port), upscale, target)))
        return out

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=len(PORTS)) as ex:
        futs = [ex.submit(run_port, p, sl) for p, sl in buckets.items() if sl]
        for f in as_completed(futs):
            for s, png in f.result():
                results[s] = png
    print(f"[gateway] 批量完成 {len(results)}/{n} 张 用时 {time.time()-t0:.0f}s "
          f"(实例 {list(buckets.items())})", flush=True)
    return [results[s] for s in seeds if s in results]

# ---------- HTTP 服务 ----------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        if self.path.rstrip("/").endswith("/v1/models"):
            keys = ("TextEncodeQwenImage21", "ManualSigmas", "BasicGuider",
                    "KSamplerSelect", "RandomNoise", "SamplerCustomAdvanced",
                    "EmptySD3LatentImage", "UnetLoaderGGUF", "UNETLoader",
                    "CLIPLoader", "VAELoader", "VAEDecode", "SaveImage")
            debug = {"HAS_TENC21": HAS_TENC21, "HAS_SIGMAS": HAS_SIGMAS,
                     "unet": UNET, "clip": CLIP, "vae": VAE,
                     "nodes": sorted([k for k in OI if k in keys])}
            return self._json(200, {"object": "list", "data": [
                {"id": "qwen-image-2.1-turbo", "object": "model",
                 "owned_by": "kaggle-comfyui", "debug": debug}]})
        return self._json(404, {"error": {"message": "not found: " + self.path}})
    def do_POST(self):
        if not self.path.rstrip("/").endswith("/v1/images/generations"):
            return self._json(404, {"error": {"message": "not found: " + self.path}})
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            prompt = body.get("prompt", "").strip()
            if not prompt:
                return self._json(400, {"error": {"message": "prompt is required"}})
            w, h = parse_size(body.get("size"))
            n = max(1, min(int(body.get("n") or 1), MAX_N))
            pngs = generate_batch(prompt, w, h, n)
            return self._json(200, {"created": int(time.time()),
                                    "data": [{"b64_json": base64.b64encode(p).decode()} for p in pngs]})
        except Exception as e:
            print("[gateway] 失败:", e, flush=True)
            return self._json(500, {"error": {"message": str(e)}})

# Cloudflare 免费隧道对单请求有 ~100s 上限（超时返回 524），DSH 插件侧硬超时 240s。
# 对策：① 尺寸收敛到 T4 上 ≤240s 能跑完的档位；② 启动时预热一次把模型载入显存；
#       ③ 生成期间写空格心跳（合法 JSON 前导空白），防止 CF 100s 断流。
RATIOS = {"1:1": (1024, 1024), "16:9": (1024, 576), "9:16": (576, 1024),
          "4:3": (960, 720), "3:4": (720, 960), "3:2": (1024, 680), "2:3": (680, 1024),
          "21:9": (1024, 440)}

PRESETS = {"1080p": (1920, 1080), "720p": (1280, 720), "2k": (2048, 1152),
           "4k": (3840, 2160)}

def parse_size(size, max_long=None):
    """支持比例(16:9)、像素(1920x1080)、档位(1080p/2k/4k)。
    max_long 给定时按长边等比收缩（用于批量时保证总时长）。"""
    s = str(size or "").strip().lower()
    if s in PRESETS:
        w, h = PRESETS[s]
    else:
        m = re.match(r"(\d+)\s*[x×*]\s*(\d+)", s)
        if m:
            w, h = int(m.group(1)), int(m.group(2))
        elif s in RATIOS:
            w, h = RATIOS[s]
        else:
            w, h = 640, 640
    limit = max_long if max_long else 1920   # 默认允许到 1080p
    if max(w, h) > limit:
        k = float(limit) / max(w, h)
        w, h = int(w * k) // 8 * 8, int(h * k) // 8 * 8
    return max(256, w), max(256, h)

_orig_do_post = Handler.do_POST

def _do_post_stream(self):
    """带心跳的 do_POST：生成期间保持连接活跃，绕开 CF 100s 限制。
    同时支持 /v1/images/generations（JSON）与 /v1/images/edits（multipart 参考图）。"""
    path = self.path.rstrip("/")
    is_gen = path.endswith("/v1/images/generations")
    is_edit = path.endswith("/v1/images/edits")
    if not (is_gen or is_edit):
        return _orig_do_post(self)
    ref_upload = None
    do_upscale = False
    try:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) or b""
        ctype = self.headers.get("Content-Type") or ""
        if is_edit or "multipart/form-data" in ctype:
            f = parse_multipart(raw, ctype)
            g = lambda k: (f.get(k) or (None, b"", ""))[1]
            prompt = (g("prompt") or b"").decode("utf-8", "replace").strip()
            size_raw = (g("size") or b"") or b"1024x1024"
            size_raw = size_raw.decode("utf-8", "replace") if isinstance(size_raw, bytes) else str(size_raw)
            n_raw = (g("n") or b"1")
            n = int(n_raw.decode() if isinstance(n_raw, bytes) else n_raw or 1)
            img = f.get("image") or f.get("image[]") or f.get("image_1")
            if img and img[1]:
                ref_upload = (img[0] or "ref.png", img[1], img[2] or "image/png")
            up_raw = (g("upscale") or b"").decode("utf-8", "replace")
            do_upscale = str(up_raw).lower() in ("1", "true", "yes", "4x", "on")
        else:
            body = json.loads(raw or b"{}")
            prompt = str(body.get("prompt", "")).strip()
            size_raw = body.get("size")
            n = int(body.get("n") or 1)
            do_upscale = str(body.get("upscale", "")).lower() in ("1", "true", "yes", "4x", "on")
            # 少数客户端把参考图放在 JSON 的 image 字段（data URL）
            if body.get("image"):
                m = re.match(r"data:([^;]+);base64,(.+)", str(body["image"]))
                if m:
                    ref_upload = ("ref.png", base64.b64decode(m.group(2)), m.group(1))
        if not prompt:
            return self._json(400, {"error": {"message": "prompt is required"}})
        n = max(1, min(n, MAX_N))
        auto_up = str(size_raw or "").strip().lower() in ("2k", "4k", "1080p")
        do_upscale = do_upscale or auto_up
        max_long = 3840 if (do_upscale and n == 1) else (1920 if n == 1 else (1280 if n == 2 else 640))
        tw, th = parse_size(size_raw, max_long)     # 目标尺寸
        gen_target = None
        if do_upscale and UPSCALE_MODEL:
            # 生成目标尺寸的 1/2.5，4x 超分后缩回目标（质量与速度的平衡点）
            w = max(256, int(tw / 2.5) // 8 * 8)
            h = max(256, int(th / 2.5) // 8 * 8)
            gen_target = (tw, th)
        else:
            w, h = tw, th
        print(f"[gateway] 目标 {tw}x{th} -> 生成 {w}x{h}"
              f"{' -> 超分后缩放' if gen_target else ''}", flush=True)
        up_note = " +超分" if (do_upscale and UPSCALE_MODEL) else ""
        print(f"[gateway] {'编辑' if ref_upload else '生成'} {w}x{h} x{n} 张"
              f"{' (含参考图)' if ref_upload else ''}{up_note}: {prompt[:40]}", flush=True)
    except Exception as e:
        return self._json(400, {"error": {"message": f"bad request: {e}"}})

    # 先发头，再周期性写空格保活
    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    self.end_headers()
    stop = threading.Event()

    def keepalive():
        while not stop.is_set():
            try:
                self.wfile.write(b" ")
                self.wfile.flush()
            except Exception:
                return
            stop.wait(10)

    ka = threading.Thread(target=keepalive, daemon=True)
    ka.start()
    t0 = time.time()
    try:
        pngs = generate_batch(prompt, w, h, n, ref_upload=ref_upload,
                             upscale=(do_upscale and bool(UPSCALE_MODEL)),
                             target=gen_target)
        payload = json.dumps({"created": int(time.time()),
                              "data": [{"b64_json": base64.b64encode(p).decode()} for p in pngs]})
        print(f"[gateway] 成功 {len(pngs)} 张 {w}x{h} 用时 {time.time()-t0:.0f}s", flush=True)
    except Exception as e:
        print("[gateway] 失败:", e, flush=True)
        payload = json.dumps({"error": {"message": str(e)}})
    finally:
        stop.set()
        ka.join(timeout=3)
    try:
        self.wfile.write(payload.encode())
        self.wfile.flush()
    except Exception:
        pass

Handler.do_POST = _do_post_stream

srv = ThreadingHTTPServer(("0.0.0.0", GW_PORT), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
print(f"网关已启动: http://127.0.0.1:{GW_PORT}/v1", flush=True)

# ---------- 3.5) 预热：两个实例各跑一张小图，把模型载入各自显存 ----------
try:
    _t = time.time()
    generate_batch("warmup portrait", 512, 512, n=len(PORTS), timeout=600)
    print(f"双实例预热完成，用时 {time.time()-_t:.0f}s", flush=True)
except Exception as e:
    print("预热失败（不影响后续）:", e, flush=True)

# ---------- 4) 命名隧道（固定域名 <YOUR_SUBDOMAIN>.<YOUR_DOMAIN>）----------
# 隧道凭证由 kaggle 固定地址配置时生成（tunnel_token.txt），启动后域名永远指向本会话。
CFD = "/tmp/cloudflared"
TUNNEL_TOKEN = os.environ.get("CF_TUNNEL_TOKEN", "")  # 从环境变量读取，勿硬编码
tun = subprocess.Popen([CFD, "tunnel", "run", "--token", TUNNEL_TOKEN],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
time.sleep(6)
alive = tun.poll() is None
gw_url = "https://<YOUR_SUBDOMAIN>.<YOUR_DOMAIN>"
print("命名隧道启动:", "成功" if alive else "失败(见下)", flush=True)
if not alive:
    print(tun.stdout.read()[:800], flush=True)
print()
print("=" * 66)
print("  DSH 渠道配置（设置 → 生图配置 → 新建渠道）—— 固定地址，一次配置永久有效：")
print("    名称:   kaggle")
print("    地址:   " + gw_url + "/v1")
print("    密钥:   kaggle （随便填，网关不校验）")
print("    模型:   qwen-image-2.1-turbo")
print("=" * 66)
print("  ✅ 命名隧道：会话重开后域名自动恢复，DSH 渠道地址无需再改")
