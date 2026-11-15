# 鏁呴殰鎺掓煡鎵嬪唽

鎸夌幇璞℃煡銆傛瘡鏉￠兘鏉ヨ嚜瀹為檯韪╁潙銆?
## 鍩熷悕杩斿洖 1033

**鍚箟**锛氬煙鍚嶉厤浜?Tunnel锛屼絾 CF 鎵句笉鍒颁换浣曞湪绾胯繛鎺ュ櫒锛堟瘮 530 鏇存槑纭級銆?
鏈€甯歌鏍瑰洜涓嶆槸 CF锛岃€屾槸 **Kaggle 閲?ComfyUI 娌¤捣鏉?鈫?缃戝叧鍚姩鏃?`raise RuntimeError("娌℃湁鍙敤鐨?ComfyUI 瀹炰緥")` 鈫?Cell 2 鐩存帴澶辫触 鈫?闅ч亾浠庢湭鍚姩**銆?
璇婃柇椤哄簭锛?1. 鎷夎繍琛屾棩蹇楋細`kaggle kernels output <user>/<slug> -p <鐩綍>`锛岀湅鏈夋病鏈夈€宑uda:0 鏈氨缁€?2. 鑻ュ嚭鐜般€屾湭灏辩华銆嶏紝闂鍦?ComfyUI 鍚姩鍙傛暟锛堣涓嬫潯锛?3. 鐪?Cell 2 鏄惁鎶?`RuntimeError: 娌℃湁鍙敤鐨?ComfyUI 瀹炰緥`

## ComfyUI 璧锋潵浣嗐€屾湭灏辩华銆嶏紙绔彛涓嶇洃鍚級

### 澶村彿鍘熷洜锛氱敤 `/system_info` 鎺㈡祴灏辩华锛堝凡韪╁娆★級

**ComfyUI 0.45.0 鐨?`/system_info` 浼氳繑鍥?404**銆傜敤 `urllib.request.urlopen(".../system_info")`
鎺㈡祴鏃讹紝404 鎶?`HTTPError`锛岃 `except` 鍚炴帀鍚庡綋浣溿€屾湭灏辩华銆嶁€斺€?*浣?ComfyUI 鍏跺疄鏃╁氨姝ｅ父鍦ㄨ窇**銆?
琛ㄧ幇涓猴細cell 閲屽弽澶嶃€岃鍛? cuda:0 鏈氨缁€嶏紝闅忓悗 Cell 2 鎶?`RuntimeError: 娌℃湁鍙敤鐨?ComfyUI 瀹炰緥`锛岄毀閬撲笉鍚姩锛屽煙鍚?1033/530銆?鑰屾鏃剁敤娴忚鍣ㄦ墦寮€ cloudflared 缁欑殑 trycloudflare 閾炬帴锛孋omfyUI 棣栭〉**杩斿洖 200 姝ｅ父鏄剧ず**銆?
**姝ｇ‘鍋氭硶锛氱敤 socket 鎺㈡祴绔彛锛屼笉渚濊禆浠讳綍 HTTP 绔偣**

```python
import socket

def port_open(port, timeout=2):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except Exception:
        return False
```

缃戝叧渚ф帰娴嬪疄渚嬪悓鏍疯鐢?socket锛屼笉瑕佺敤 `/system_info`銆?
### 娆″洜锛氬惎鍔ㄥ弬鏁颁笉鍏煎

**涓嶈缁欒繖涓増鏈殑 ComfyUI 鍔?`--cuda-device` / `--output-directory`銆?*
瀹炴祴鍔犱簡涔嬪悗杩涚▼ pid 瀛樺湪浣?8188 绔彛涓嶅紑銆傚彧鐢細

```python
subprocess.Popen(["python", "main.py", "--listen", "0.0.0.0", "--port", "8188"],
                 cwd=COMFY, stdout=open(log, "w"), stderr=subprocess.STDOUT)
```

鑻ョ‘瀹為渶瑕佹寚瀹氬崱锛屾敼鐢ㄧ幆澧冨彉閲?`CUDA_VISIBLE_DEVICES=1`銆?
## 鍩熷悕杩斿洖 530

**鍚箟**锛欳loudflare 鎵句笉鍒拌繛鎺ュ櫒锛堜細璇濇病璺戯紝鎴?cloudflared 娌¤繛涓婏級銆?
妫€鏌ラ『搴忥細
1. Kaggle 浼氳瘽鏄惁鍦ㄨ窇锛歚kaggle kernels status <user>/<slug>` 鏄?`RUNNING` 杩樻槸 `COMPLETE`
2. 鏃犲ご杩愯鐨?cell 璺戝畬浼氳瘽灏遍攢姣?鈫?闅ч亾娑堝け銆傞獙璇佹椂鍔犱繚娲?cell锛岄暱鏈熶娇鐢ㄧ敤**浜や簰浼氳瘽**
3. 闅ч亾 ingress 瑙勫垯鏄惁閰嶅ソ锛坄PUT .../cfd_tunnel/<id>/configurations`锛夛紝缂轰簡浼?530/503

## 鍩熷悕杩斿洖 503

**鍚箟**锛氳繛鎺ュ櫒鍦ㄧ嚎锛屼絾娌℃湁鍙敤鐨?ingress 璺敱銆?
鈫?琛?ingress 瑙勫垯锛宍service` 蹇呴』鎸囧悜缃戝叧绔彛锛堥粯璁?`http://localhost:8819`锛夛紝鏈€鍚庝竴鏉″厹搴?`http_status:404`銆?
## 鍩熷悕杩斿洖 524

**鍚箟**锛欳loudflare 绛夋簮绔欒秴杩?~100 绉掋€?
鈫?缃戝叧蹇呴』銆屽厛鍙戝搷搴斿ご + 鐢熸垚鏈熼棿姣?10s 鍐欎竴涓┖鏍笺€嶃€傜┖鏍兼槸鍚堟硶 JSON 鍓嶅绌虹櫧锛屽鎴风 `JSON.parse` 涓嶅彈褰卞搷銆?
## DSH 鎶ャ€屼笂娓告帴鍙ｈ繑鍥炰簡闈?JSON 鍝嶅簲锛圚TTP 200锛夈€?
**杩欎笉鏄牸寮忛棶棰橈紝鏄秴鏃躲€?* 鎻掍欢 `readResponseText()` 鍦?240s 棰勭畻瓒呮椂鍚?catch 杩斿洖绌轰覆锛宍JSON.parse("")` 澶辫触锛岃璇姤鎴愰潪 JSON銆?
鎺掓煡锛?1. 鍗曞浘鑰楁椂鏄惁 > 240s锛坄UPSTREAM_TIMEOUT_MS = 24e4`锛?2. 灏哄鏄惁 >768 闀胯竟
3. 妯″瀷鏄惁鍐峰姞杞斤紙缃戝叧鍚姩鏃惰棰勭儹锛?
楠岃瘉鏂规硶锛氱粫寮€鎻掍欢鐩磋繛锛岀湅鐪熷疄鍝嶅簲锛?```bash
python -c "import requests; r=requests.post('https://<鍩熷悕>/v1/images/generations', json={'model':'kaggle-turbo','prompt':'test','size':'1:1'}, timeout=900); print(r.status_code, len(r.content), r.content[:80])"
```

## 鍔犺浇鎶?`safetensors header is too large`

**涓嶆槸鏍煎紡闂锛屾槸涓嬭浇鍒颁簡 404 椤甸潰銆?*

鎵╂暎妯″瀷鍦?HF 浠撳簱**鏍圭洰褰?*锛屼笉鍦?`diffusion_models/` 瀛愮洰褰曪細

| 鏂囦欢 | 杩滅▼璺緞 |
| --- | --- |
| 鎵╂暎妯″瀷 | `<repo>/resolve/main/qwen-image-2.1-turbo-fp8.safetensors` |
| 鏂囨湰缂栫爜鍣?| `<repo>/resolve/main/text_encoders/qwen3vl_8b_int8_convrot.safetensors` |
| VAE | `<repo>/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors` |

涓嬭浇鍚庡繀椤绘牎楠屽ぇ灏忥細fp8 7.13GB / te 9.35GB / vae 675MB銆?
## 鍔犺浇鎶?`Unknown model architecture`

鈫?鐢ㄤ簡 GGUF 鏍煎紡銆俢ity96 鐨?`UnetLoaderGGUF` 涓嶆敮鎸?Qwen-Image-2.1 鏋舵瀯銆傛敼 FP8 safetensors銆?
## ComfyUI 杩斿洖 400 `prompt_outputs_failed_validation`

璇?`node_errors` 閲屽叿浣撳摢涓妭鐐瑰摢涓瓧娈点€傚凡韪╄繃鐨勶細

| 鑺傜偣 | 瀛楁 | 姝ｇ‘鍊?|
| --- | --- | --- |
| `TextEncodeQwenImage21` | 鏂囨湰鍙傛暟鍚?| **`prompt`**锛堜笉鏄?`text`锛?|
| `TextEncodeQwenImage21` | `resolution` | **蹇呭～**锛?024 / 2048锛?|
| `ManualSigmas` | `sigmas` | 瀛楃涓?`"1.0, 0.978453, ..."` |

## 瓒呭垎鐩稿叧锛?080p/2K/4K锛?
### 浜哄儚浜斿畼鍙樺舰锛堥蓟姊佹柇瑁傘€佺溂鐫涢敊浣嶃€佹墜鎸囩矘杩烇級

**杩欐槸 AI 瓒呭垎瀵瑰皬缁撴瀯鐨勭牬鍧忥紝涓嶆槸妯″瀷鏈韩鐢婚敊銆?*

768脳432 閲屼汉鑴搁蓟瀛愬彧鍗犵害 20 鍍忕礌锛?x 瓒呭垎瑕侀潬璁粌缁忛獙鈥滅寽鈥濓紝榧绘銆佺溂鐫戙€佹墜鎸?杩欑被缁嗙粨鏋勬渶瀹规槗琚紪鎴愭柇瑁傛垨閿欎綅銆傚疄娴嬶細姘戝浗鏃楄浜哄儚鏀惧ぇ鍒?236% 鏃堕蓟姊佷腑闂存í鍚戞柇寮€銆?
**淇硶**锛氫汉鍍?*涓嶈鐢?AI 瓒呭垎**銆傛敼鎴?`size: 1024x576` 鐩寸敓锛屽啀鐢ㄦ湰鍦?lanczos 鏀惧ぇ锛?
```python
from PIL import Image
Image.open(src).resize((1920, 1080), Image.LANCZOS).save(dst)
```

鑰楁椂鐩稿綋锛?08s vs 92s锛夛紝浣嗙粨鏋勪繚鐪熴€傚彧鏈夐鏅?寤虹瓚杩欑被澶х汗鐞嗘墠閫傚悎 AI 瓒呭垎銆?
### 鍑哄浘鏈夐奔楠ㄧ姸鏉＄汗浼奖

**鍘熷洜**锛氱敓鎴愬昂瀵稿お灏忓氨 4x 鏀惧ぇ锛堝 480脳256 鈫?1920锛夛紝璁粌绾圭悊琚媺浼搁噸澶嶃€?
**淇硶**锛氱敓鎴愬埌鐩爣鐨?1/2.5锛堝 768脳432锛夛紝4x 鏀惧ぇ鍒?3072 鍚庣敤 `ImageScale`(lanczos)
缂╁洖 1920銆傜瓑鏁?2.5x 鏀惧ぇ锛屼吉褰辨秷澶便€傚疄娴?92s / 寮犮€?
### 瓒呭垎涓嶇敓鏁堬紝鍑哄浘杩樻槸灏忓昂瀵?
妫€鏌?Console 閲岀殑 `瓒呭垎妯″瀷: 4x-UltraSharp.pth` 閭ｈ锛?- 鏄剧ず銆屾湭鎵惧埌銆嶁啋 Cell 1 涓嬭浇澶辫触锛屾鏌?`models/upscale_models/4x-UltraSharp.pth` 鏄惁瀛樺湪锛堝簲 66.9MB锛?- 鏄剧ず妯″瀷鍚嶄絾灏哄娌″彉 鈫?璇锋眰娌″甫 `upscale: true`锛屾垨 `size` 涓嶆槸 `1080p/2k/4k` 妗ｄ綅鍚?
### 鐩寸敓澶у浘鐗瑰埆鎱紙396 绉掞級

杩欐槸姝ｅ父鐨勩€?920脳1088 鐨勫儚绱犻噺鏄?768脳432 鐨?6.3 鍊嶏紝鑰?T4 鏄惧瓨鏈氨鍚冪揣锛?6.5GB > 15GB锛夛紝
澶у浘璁?swap 娆℃暟婵€澧炪€?*涓嶈鐩寸敓 1080p锛屼竴寰嬭蛋瓒呭垎璺緞銆?*

### 瓒呭垎鍚庡昂瀵告槸 1920脳1024 鑰屼笉鏄?1920脳1080

鐢熸垚灏哄鍙栨暣鍒?8 鐨勫€嶆暟瀵艰嚧鐨勶紙480脳256 鈫?4x = 1920脳1024锛夈€?鐢ㄣ€岀洰鏍?1/2.5 + 缂╂斁鍥炵洰鏍囥€嶇殑鏂规灏变笉浼氭湁杩欎釜闂锛岃兘绮剧‘鍑?1920脳1080銆?
## push 鎶?`Maximum batch GPU session count of 2 reached`

鈫?Kaggle 鍚屾椂鏈€澶?2 涓?GPU 浼氳瘽锛屽厛鍋滄棫鐨勩€?
鍋滀細璇濅綅缃細Notebook **鐗堟湰椤?*锛堜笉鏄紪杈戝櫒锛夆啋 宸︿笅 `View Active Events` 鈫?姣忚 `鈰痐 鈫?`Stop Session`銆?
缂栬緫鍣ㄩ〉鍙偣 `Session options`锛堚嫯 鑿滃崟锛夆啋 `Start session`锛?*鍏抽棴浼氳瘽**鍦ㄧ増鏈〉鐨?Active Events 閲屻€?
## PowerShell 鐩稿叧

- `kernel-metadata.json` **涓嶈兘甯?BOM**锛屽惁鍒?`kaggle kernels push` 鎶?`Unexpected UTF-8 BOM`銆傜敤 Python `json.dump` 鍐欙紝鍒敤 `Set-Content -Encoding UTF8`銆?- `Invoke-RestMethod` 璇婚敊璇搷搴旀祦瀹规槗鎶?NRE锛岀敤 `try { } catch { $_.Exception.Message }` 鍗冲彲锛屽埆娣辨寲 `GetResponseStream()`銆?- 鍚庡彴鎵ц鍣ㄦ湰韬槸 pwsh锛岃剼鏈噷鍐嶅 `pwsh -File` 浼?`CommandNotFoundException`锛涚洿鎺ユ妸鍛戒护鍘熸枃浜ょ粰 `run_in_background`銆傛湭绛惧悕 `.ps1` 浼氳鎵ц绛栫暐鎸°€?
## hf-mirror 璺緞

`hf-mirror.com/<repo>/resolve/main/...` 鍙敤锛沗workflow_templates` 浠撳簱鍦?hf-mirror 杩斿洖 401锛屾敼鐢?`ghproxy.net/https://raw.githubusercontent.com/...`銆?