#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一致性角色生成器 —— 绕过 DSH 插件的端点适配问题，直连本地网关

用法：
    # 单张
    python consistency_gen.py --ref 基准图.png --prompt "换深灰西装，盘发，微笑" --out out.png

    # 批量（同一张参考图，多个造型）
    python consistency_gen.py --ref 基准图.png --batch prompts.json --outdir ./variants

    # 指定模型与尺寸
    python consistency_gen.py --ref a.png --prompt "夏日碎花裙，户外" --model doubao-seedream-5-lite --size 1024x1024

prompts.json 格式：
    [
      {"name": "suit",     "prompt": "换深灰职业西装，盘发，微笑"},
      {"name": "casual",   "prompt": "换浅蓝牛仔衬衫，披发，大笑"},
      {"name": "hanfu",    "prompt": "换月白汉服，发髻玉簪，垂眸"}
    ]

原理：走 /v1/images/edits（multipart 上传参考图），这是本地网关接受图生图的正确格式。
      seedream 无水印；hy-image-3.5 会带 WORKBUDDY 水印。
"""
import argparse
import base64
import io
import json
import os
import re
import sys

try:
    import requests
except ImportError:
    sys.exit('需要 requests：pip install requests')

DEFAULT_DSH_CONFIG = os.path.expanduser(r'~\.dsh\profiles\desktop\cordis.patch.yml')
IDENTITY_LOCK = '保持这位人物面部特征和身份完全不变（同样的脸型、眼睛、鼻子、嘴唇、肤色、发型颜色），改为：'


def get_api_key(config_path=DEFAULT_DSH_CONFIG):
    """从 DSH 插件配置里读网关密钥（sk-a2a-...），不打印内容。"""
    if os.path.exists(config_path):
        text = io.open(config_path, encoding='utf-8', errors='replace').read()
        m = re.search(r'sk-a2a-[A-Za-z0-9]+', text)
        if m:
            return m.group(0)
    env = os.environ.get('IMAGE_GATEWAY_KEY', '').strip()
    if env:
        return env
    sys.exit('找不到网关密钥：请确认 DSH 插件已配置，或设置环境变量 IMAGE_GATEWAY_KEY')


def generate(base_url, key, ref_path, prompt, model, size, lock_identity=True, timeout=300):
    """上传参考图并生成一张变体，返回 (bytes, mime)。"""
    if not os.path.exists(ref_path):
        raise FileNotFoundError(ref_path)
    full_prompt = (IDENTITY_LOCK + prompt) if lock_identity else prompt
    with open(ref_path, 'rb') as f:
        data = f.read()
    files = {'image': (os.path.basename(ref_path), data, 'image/png')}
    form = {'model': model, 'prompt': full_prompt, 'size': size}
    r = requests.post(f'{base_url}/v1/images/edits',
                      headers={'Authorization': f'Bearer {key}'},
                      files=files, data=form, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f'HTTP {r.status_code}: {r.text[:200]}')
    payload = r.json()
    items = payload.get('data') or []
    if not items:
        raise RuntimeError('响应里没有图片数据')
    b64 = items[0].get('b64_json')
    if not b64:
        raise RuntimeError('响应缺少 b64_json 字段')
    raw = base64.b64decode(b64)
    # 识别真实格式
    head = raw[:4]
    mime = 'image/png' if head == b'\x89PNG' else ('image/jpeg' if head[:2] == b'\xff\xd8' else 'image/png')
    return raw, mime


def main():
    ap = argparse.ArgumentParser(description='一致性角色生成器（直连本地网关图生图）')
    ap.add_argument('--ref', required=True, help='参考图路径')
    ap.add_argument('--prompt', help='单张的换装/改动作描述')
    ap.add_argument('--batch', help='批量描述 JSON 文件路径')
    ap.add_argument('--out', help='单张输出路径')
    ap.add_argument('--outdir', help='批量输出目录')
    ap.add_argument('--model', default='doubao-seedream-5-lite',
                    help='模型（seedream 无水印；hy-image-3.5 有 WORKBUDDY 水印）')
    ap.add_argument('--size', default='1024x1024', help='输出尺寸，如 1024x1024')
    ap.add_argument('--base-url', default='http://127.0.0.1:3065', help='网关地址')
    ap.add_argument('--no-lock', action='store_true', help='不自动加身份锁定前缀')
    args = ap.parse_args()

    key = get_api_key()
    lock = not args.no_lock

    if args.batch:
        specs = json.load(io.open(args.batch, encoding='utf-8'))
        outdir = args.outdir or './variants'
        os.makedirs(outdir, exist_ok=True)
        total, ok = len(specs), 0
        for i, spec in enumerate(specs, 1):
            name = spec.get('name') or f'v{i}'
            prompt = spec.get('prompt', '')
            if not prompt:
                print(f'[{i}/{total}] {name}: 跳过（无 prompt）')
                continue
            try:
                raw, mime = generate(args.base_url, key, args.ref, prompt,
                                     spec.get('model', args.model),
                                     spec.get('size', args.size), lock)
                ext = '.png' if mime == 'image/png' else '.jpg'
                path = os.path.join(outdir, f'{name}{ext}')
                open(path, 'wb').write(raw)
                ok += 1
                print(f'[{i}/{total}] {name}: OK {len(raw)//1024}KB -> {path}')
            except Exception as e:
                print(f'[{i}/{total}] {name}: 失败 {e}')
        print(f'\n完成 {ok}/{total}，输出目录: {outdir}')
        return

    if not args.prompt:
        sys.exit('需要 --prompt 或 --batch')
    raw, mime = generate(args.base_url, key, args.ref, args.prompt,
                         args.model, args.size, lock)
    out = args.out or ('out.png' if mime == 'image/png' else 'out.jpg')
    open(out, 'wb').write(raw)
    print(f'OK {len(raw)//1024}KB -> {out}')


if __name__ == '__main__':
    main()
