# 宸查獙璇佺殑鍏蜂綋鍙傛暟锛?026-11-15 瀹炴祴锛?
杩欏鍊煎湪鏈満璺戦€氳繃锛屽彲鐩存帴澶嶇敤銆傚叏閮ㄦ暟鎹潵鑷疄闄呰繍琛岋紝涓嶆槸鎺ㄦ祴銆?
## Cloudflare

| 椤?| 鍊?|
| --- | --- |
| 璐︽埛 ID | `<YOUR_CF_ACCOUNT_ID>` |
| Zone | `<YOUR_DOMAIN>`锛圛D `65ae50752bdb98225b7ac0d9bc8d0ac2`锛?|
| 闅ч亾鍚?| `kaggle-comfyui` |
| 闅ч亾 ID | `<YOUR_TUNNEL_ID>` |
| 鍥哄畾鍩熷悕 | `<YOUR_SUBDOMAIN>.<YOUR_DOMAIN>` |
| CNAME | `鈫?40f9030d-....cfargotunnel.com`锛坧roxied锛?|
| ingress | `<YOUR_SUBDOMAIN>.<YOUR_DOMAIN> 鈫?http://localhost:8819` |
| API Token 鏂囦欢 | `./\cf_token.txt` |
| 闅ч亾鍑瘉鏂囦欢 | `./\tunnel_token.txt`锛堜篃宸插唴宓屽湪 gateway cell锛?|

## Kaggle

| 椤?| 鍊?|
| --- | --- |
| 鐢ㄦ埛鍚?| `<YOUR_KAGGLE_USERNAME>` |
| Notebook | `<YOUR_KAGGLE_USERNAME>/comfyui-kaggle-free-gpu` |
| CLI | `C:\Python311\Scripts\kaggle.exe`锛坴2.2.5锛?|
| 鍑瘉 | `C:\Users\long\.kaggle\kaggle.json` |
| 鍚屾椂 GPU 浼氳瘽涓婇檺 | 2锛堣秴鍑烘姤 `Maximum batch GPU session count`锛?|

## 妯″瀷涓庤秴鍒?
| 椤?| 鍊?|
| --- | --- |
| 浠撳簱 | `abenzerps/Qwen-Image-2.1-Turbo-Quantized`锛坔f-mirror 闀滃儚锛?|
| 鎵╂暎妯″瀷 | `qwen-image-2.1-turbo-fp8.safetensors`锛?.13GB锛?*浠撳簱鏍圭洰褰?*锛?|
| 鏂囨湰缂栫爜鍣?| `text_encoders/qwen3vl_8b_int8_convrot.safetensors`锛?.35GB锛?|
| VAE | `vae/qwen_image_2.1_vae_bf16.safetensors`锛?75MB锛?|
| 瓒呭垎妯″瀷 | `4x-UltraSharp.pth`锛?6.9MB锛宍hf-mirror.com/lokCX/4x-Ultrasharp`锛?|
| 閲囨牱 | 8 姝ワ紝`euler`锛孋FG 1.0锛孧anualSigmas 鍥哄畾搴忓垪 |

## 瀹炴祴鑰楁椂锛圱4脳2锛孎P8锛? 姝?Turbo锛?
| 璇锋眰 | 瀹為檯杈撳嚭 | 鑰楁椂 |
| --- | --- | --- |
| `size: "1:1"` | 1024脳1024 | ~110s |
| `size: "16:9"` | 1024脳576 | ~105s |
| **`size:"1920x1080" + upscale:true`** | **1920脳1080** | **92s** |
| `size: "2k"` | 2048脳1152 | ~100s |
| `size:"1920x1080"` 涓嶈秴鍒?| 1920脳1088 | 396s锛堝お鎱紝绂佺敤锛?|
| 鐢熸垚 480 鈫?4x 鐩村嚭 | 1920脳1024 | 38s锛?*鏈夐奔楠ㄤ吉褰?*锛屽凡寮冪敤锛?|
| `n=2` 鍙屽崱骞惰锛?40脳640锛?| 2 寮?| 86s |
| 骞跺彂 2 涓?`n=1` | 2 寮?| 74s |
| `edit` 鍙傝€冨浘 | 1024脳1536 | ~103s |
| 1080p 杩炲嚭 6 寮?| 6脳1920脳1080 | 绾?9 鍒嗛挓锛?4~103s/寮狅級 |

## DSH 娓犻亾

| 椤?| 鍊?|
| --- | --- |
| 閰嶇疆鏂囦欢 | `C:\Users\long\.dsh\profiles\desktop\cordis.patch.yml` |
| 鎻掍欢 id | `imagegen`锛坢odule `@q253595422/dsh-imagegen-video`锛?|
| 閲嶈浇鐩爣 | `include:imagegen` |
| 娓犻亾 | `name: kaggle`锛宍apiUrlFull: true`锛宍protocol: images` |
| 妯″瀷鍒悕 | `kaggle-turbo` 鈫?`qwen-image-2.1-turbo` |
| 澶囦唤 | `cordis.patch.yml.bak-kaggle-20261115-145658` |

## 宸ヤ綔鐩綍

`./\`
- `comfyui_kaggle_cell.py` / `comfyui_gateway_cell.py` 鈥?涓や釜 cell 婧愭枃浠讹紙v23锛?- `comfyui_kaggle_cell.ipynb` / `kernel-metadata.json` 鈥?push 鐢ㄧ殑缁勮浠?- `comfyui_video_cell.py` 鈥?Wan2.2 鏂囩敓瑙嗛锛?21 甯э紝T4 绾?30 鍒嗛挓锛?- `wf/` 鈥?瀹樻柟宸ヤ綔娴?JSON 澶囦唤
- `video_run3/zhangxue_water_drift.mp4` 鈥?宸茬敓鎴愮殑瑙嗛鏍蜂緥
- `lqx/` 鈥?鏋楅潚闇炲叚椋庢牸 1080p 鎴愬搧
