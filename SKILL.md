---
name: kaggle-comfyui-gateway
description: 鍦?Kaggle 鍏嶈垂 GPU锛圱4脳2锛変笂鎼?ComfyUI 骞舵毚闇叉垚 OpenAI 鍏煎鐢熷浘鎺ュ彛锛屾帴鍏?DSH銆岀敓鍥鹃厤缃€嶆笭閬擄紝鐢ㄥ浐瀹?Cloudflare 鍩熷悕闀挎湡澶嶇敤锛涘綋鐢ㄦ埛瑕佸湪 Kaggle 璺戠敓鍥?鐢熻棰戞ā鍨嬨€佹兂鎶婂厤璐?GPU 鎺ヨ繘 DSH銆侀渶瑕佸浐瀹氬煙鍚嶉毀閬撱€佹垨鎺掓煡璇ラ摼璺殑 524/瓒呮椂/妯″瀷鍔犺浇閿欒鏃朵娇鐢ㄣ€?---

# Kaggle 鍏嶈垂 GPU + ComfyUI + 鍥哄畾鍩熷悕 DSH 缃戝叧

鎶?Kaggle 鍏嶈垂 T4脳2 鍙樻垚 DSH 鍙洿鎺ヨ皟鐢ㄧ殑鐢熷浘鍚庣銆?*鍏ㄩ儴鍏嶈垂**锛圞aggle 姣忓懆 30 灏忔椂 GPU 棰濆害锛夈€?
## 閾捐矾鎬昏

```
DSH 鐢熷浘闈㈡澘
  鈹斺攢 娓犻亾 kaggle (OpenAI /v1/images/generations)
       鈹斺攢 https://<瀛愬煙>.<浣犵殑鍩?/v1        鈫?Cloudflare 鍛藉悕闅ч亾锛堝浐瀹氾級
            鈹斺攢 Kaggle 浼氳瘽鍐呯綉鍏?:8819      鈫?Cell 2
                 鈹溾攢 ComfyUI :8188 (cuda:0)
                 鈹斺攢 ComfyUI :8189 (cuda:1)  鈫?鎵归噺鏃跺苟琛岀敤绗簩寮犲崱
```

## 涓€娆℃€у噯澶囷紙鍙仛涓€娆★級

1. **Cloudflare 鎵樼鍩熷悕**锛堝厤璐逛簩绾у煙涔熷彲锛屽 `xxx.cc.cd`锛?2. **CF API Token**锛歁y Profile 鈫?API Tokens 鈫?Custom Token
   - `Account 路 Cloudflare Tunnel 路 Edit`
   - `Zone 路 DNS 路 Edit`锛?*蹇呴』鏄?Zone 绾?*锛孉ccount 绾?DNS 鏉冮檺鏃犳晥锛侊級
   - 涓嶈璁?TTL / IP 鐧藉悕鍗?3. **Kaggle API Token**锛欿aggle 鈫?Settings 鈫?API 鈫?Create New Token 鈫?`kaggle.json`
   鏀?`~/.kaggle/kaggle.json`

### 寤哄懡鍚嶉毀閬?+ CNAME

```powershell
# 瀛?token锛屽埆璐磋亰澶╅噷
[IO.File]::WriteAllText("$PWD/cf_token.txt", 'cfat_...')

$t = (Get-Content cf_token.txt -Raw).Trim()
$h = @{ "Authorization" = "Bearer $t"; "Content-Type" = "application/json" }

# 1) 鍙栬处鎴?/ zone
$acc  = (Invoke-RestMethod "https://api.cloudflare.com/client/v4/accounts" -Headers $h).result[0].id
$zone = (Invoke-RestMethod "https://api.cloudflare.com/client/v4/zones" -Headers $h).result |
        Where-Object name -eq '浣犵殑鍩熷悕' | Select-Object -ExpandProperty id

# 2) 寤洪毀閬?$body = '{"name":"kaggle-comfyui","config_src":"cloudflare"}'
$tid = (Invoke-RestMethod "https://api.cloudflare.com/client/v4/accounts/$acc/cfd_tunnel" `
        -Headers $h -Method POST -Body $body).result.id

# 3) 鍙栭毀閬撹繍琛屽嚟璇侊紙娉ㄦ剰锛欸ET锛宺esult 鐩存帴鏄?token 瀛楃涓诧級
$tk = (Invoke-RestMethod "https://api.cloudflare.com/client/v4/accounts/$acc/cfd_tunnel/$tid/token" `
       -Headers $h).result

# 4) ingress 瑙勫垯锛堝懡鍚嶉毀閬撳繀椤绘湁锛屽惁鍒?530/503锛?$cfg = @{ config = @{ ingress = @(
  @{ hostname = "comfyui.浣犵殑鍩熷悕"; service = "http://localhost:8819" },
  @{ service = "http_status:404" }) } } | ConvertTo-Json -Depth 6
Invoke-RestMethod "https://api.cloudflare.com/client/v4/accounts/$acc/cfd_tunnel/$tid/configurations" `
  -Headers $h -Method PUT -Body $cfg

# 5) CNAME 鎸囧悜闅ч亾
$dns = @{ type="CNAME"; name="comfyui"; content="$tid.cfargotunnel.com"; proxied=$true } | ConvertTo-Json
Invoke-RestMethod "https://api.cloudflare.com/client/v4/zones/$zone/dns_records" `
  -Headers $h -Method POST -Body $dns
```

鎶?`$tk` 濉繘 `scripts/comfyui_gateway_cell.py` 鐨?`TUNNEL_TOKEN`锛宍$tid` 璁颁笅鏉ャ€?
## 姣忔鍚姩锛堢害 10 鍒嗛挓锛?
1. 鎶?`scripts/comfyui_kaggle_cell.py`銆乣scripts/comfyui_gateway_cell.py` 缁勮鎴?3~4 涓?cell 鐨?ipynb锛?   閰?`templates/kernel-metadata.json`锛堟敼 `id` 涓?`<鐢ㄦ埛鍚?/<slug>`锛?2. `kaggle kernels push -p <鐩綍>`锛堜細鎺掗槦杩愯锛?*鎺掗槦涓嶇瓑浜庤繍琛?*锛岃纭鐘舵€侊級
3. 鎴栧湪 Kaggle 缂栬緫鍣ㄩ噷鐐?**Start session 鈫?Run All**
4. 绛?`https://<瀛愬煙>.<浣犵殑鍩?/v1/models` 杩斿洖 200

**鎺㈡祴鑺傚**锛氬惎鍔ㄩ樁娈碉紙瑁?ComfyUI + 涓?20GB 妯″瀷 + 璧峰弻瀹炰緥锛夎嚦灏戣 8~10 鍒嗛挓锛?涓嶈涓€寮€濮嬪氨楂橀杞鈥斺€斿厛绛?5 鍒嗛挓锛屼箣鍚庢瘡 30 绉掓帰涓€娆″嵆鍙€傚煙鍚嶅湪浼氳瘽灏辩华鍓?渚濇缁忓巻 `530`锛堟棤杩炴帴鍣級鈫?`502`锛堣繛鎺ュ櫒鏂紑锛夆啋 `200`锛堝氨缁級銆?
### 鍒锋柊缃戦〉 鈮?鍏虫満浼氳瘽

- **鍒锋柊缃戦〉锛團5锛?*锛氬悗绔?kernel 浠嶅湪璺戯紝鍩熷悕鐓ф牱閫氥€傜紪杈戝櫒浼氭樉绀?`Draft Session off`锛?  閭ｅ彧鏄〉闈㈣繛鎺ユ柇浜嗏€斺€?*姝ゆ椂鍗冧竾鍒偣 Run All**锛屽惁鍒欎細鏂板缓浼氳瘽骞堕噸涓?20GB銆?- **Stop Session / 鍏虫満**锛氬鍣ㄩ攢姣侊紝`/tmp` 涓?`/kaggle/working` 鍏ㄩ儴娓呯┖锛屽繀椤婚噸璺戙€?
鍒ゆ柇瑕佷笉瑕侀噸鍚紝鐪嬪煙鍚嶈€屼笉鏄湅椤甸潰锛?
```powershell
# 200 = 浼氳瘽娲荤潃锛屼粈涔堥兘鍒姩锛?30/502 = 宸叉锛屾墠闇€瑕侀噸鏂?Run All
Invoke-RestMethod "https://<YOUR_SUBDOMAIN>.<YOUR_DOMAIN>/v1/models"
```

## DSH 娓犻亾閰嶇疆

鏀?`~/.dsh/profiles/desktop/cordis.patch.yml`锛?*涓嶆槸 settings.yaml**锛夛細

```yaml
- id: imagegen
  name: "@q253595422/dsh-imagegen-video"
  config:
    channels:
      # ... 宸叉湁娓犻亾 ...
      - id: <鏂癠UID>
        preset: ""
        name: kaggle
        apiUrl: https://comfyui.浣犵殑鍩熷悕/v1/images/generations
        apiUrlFull: true          # 瀹屾暣绔偣锛岀粫杩?qwen-* 鐨?DashScope 鍘熺敓鍒嗘敮
        watermark: true
        protocol: images
        models:
          - alias: kaggle-turbo
            id: qwen-image-2.1-turbo
    channelSecrets:
      <鏂癠UID>: kaggle             # 缃戝叧涓嶆牎楠岋紝闅忎究濉?```

**鏀瑰畬蹇呴』閲嶈浇鎻掍欢**锛堜笉鐢ㄩ噸鍚?DSH锛夛細
```
plugin_manager set_plugin target="include:imagegen" enabled=false
plugin_manager set_plugin target="include:imagegen" enabled=true
```

## 纭檺鍒讹紙鍏ㄩ儴瀹炴祴韪╄繃锛?
| 闄愬埗 | 鏁板€?| 琛ㄧ幇 | 瀵圭瓥 |
| --- | --- | --- | --- |
| Cloudflare 鍗曡姹?| ~100s | HTTP **524** | 缃戝叧鍏堝彂澶?+ 姣?10s 鍐欑┖鏍煎績璺?|
| DSH 鎻掍欢涓婃父瓒呮椂 | **240s**锛坄UPSTREAM_TIMEOUT_MS`锛?| 璇姤銆岄潪 JSON 鍝嶅簲锛圚TTP 200锛夈€?| 鎸夈€屽疄娴嬭€楁椂鎬昏〃銆嶉€夊昂瀵?+ 鍚姩棰勭儹 |
| Kaggle 骞跺彂 GPU 浼氳瘽 | 2 | push 鎶?`Maximum batch GPU session count` | 鍏堝仠鏃т細璇?|
| 鍏嶈垂闅ч亾 | 姣忔闅忔満鍩熷悕 | 鍦板潃鍙?| 鐢?*鍛藉悕闅ч亾**鍥哄畾 |
| 鏃犲ご杩愯 | cell 璺戝畬鍗抽攢姣?| 闅ч亾娑堝け | 鍔犱繚娲?cell锛屾垨鏀圭敤浜や簰浼氳瘽 |

## 鈿狅笍 鐗堟湰鍒囨崲绾緥锛堟渶瀹规槗缈昏溅鐨勫湴鏂癸級

**鍚屼竴涓懡鍚嶉毀閬撳彲浠ヨ澶氫釜浼氳瘽鍚屾椂杩炴帴锛孋loudflare 浼氭妸璇锋眰闅忔満鍒嗗彂缁欎换鎰忎竴涓繛鎺ュ櫒銆?*

鍚庢灉锛氫綘浠ヤ负鍦ㄦ祴鏂颁唬鐮侊紝瀹為檯璇锋眰琚墦鍒颁簡杩樺湪璺戠殑鏃х増鏈細璇濅笂鈥斺€旂棁鐘舵槸銆屾柊鍔熻兘濂藉儚娌＄敓鏁堛€嶏紝
浣嗘棩蹇?浠ｇ爜鎬庝箞鐪嬮兘瀵广€傚疄娴嬫椂鏇惧嚭鐜?3 涓細璇濓紙浜や簰浼氳瘽 + v13 + v14锛夊悓鏃跺湪绾匡紝
`n=4` 鐨勬壒閲忚姹傚彧杩斿洖 1 寮狅紝鍥犱负璺敱鍒颁簡鏃т唬鐮併€?
**姣忔鎺ㄩ€佹垨鍚姩鏂扮増鏈紝蹇呴』鍏堟竻骞插噣鏃т細璇濓細**

1. 鎵撳紑 Notebook 鐨?*鐗堟湰椤?*锛坄/code/<user>/<slug>`锛屼笉鏄?`/edit`锛?2. 宸︿笅瑙?`View Active Events`锛堟暟瀛?= 褰撳墠娲诲姩浼氳瘽鏁帮級
3. 閫愯鐐?`鈰痐 鈫?`Stop Session`锛岄櫎浜嗚淇濈暀鐨勯偅涓€涓?4. 纭鏁板瓧闄嶅埌 1锛屽啀鍋氫笅涓€姝?
鍙﹀娉ㄦ剰锛?*缂栬緫鍣ㄩ〉闈㈢殑浠ｇ爜鍦ㄤ綘 push 涔嬪悗涓嶄細鑷姩鏇存柊**銆俻ush 鍚庤鍦ㄦ祻瑙堝櫒閲?**鍒锋柊椤甸潰**锛岀紪杈戝櫒鐨?Draft Session 鎵嶄細鍔犺浇鏂颁唬鐮侊紝鍚﹀垯 Run All 璺戠殑浠嶆槸鏃т唬鐮併€?
鍋滃畬浼氳瘽鍚庡煙鍚嶄細鍏堣繑鍥?502/530锛堣繛鎺ュ櫒鏂紑锛夛紝鏂颁細璇濊捣鏉ュ悗鑷姩鎭㈠锛屼笉鐢ㄦ敼 DSH銆?
## 妯″瀷閫夋嫨锛圦wen-Image-2.1-Turbo 閲忓寲鐗堬級

| 鏍煎紡 | 缁撴灉 | 鍘熷洜 |
| --- | --- | --- |
| FP8 safetensors | 鉁?**鍙敤** | 鏍囧噯 UNETLoader 鍙洿鎺ュ姞杞?|
| GGUF (Q4/Q8) | 鉂?| city96 GGUF 鍔犺浇鍣ㄤ笉璁よ鏋舵瀯锛圲nknown model architecture锛?|
| INT8 ConvRot | 鉂?| header 杩囧ぇ锛屾爣鍑嗗姞杞藉櫒鎷掓敹 |

**涓嬭浇璺緞闄烽槺**锛氭墿鏁ｆā鍨嬪湪 HF 浠撳簱**鏍圭洰褰?*锛宍text_encoders/` 鍜?`vae/` 鎵嶅湪瀛愮洰褰曘€?鎷奸敊浼氭嬁鍒?15 瀛楄妭 404 椤甸潰锛屽姞杞芥椂鎶?`safetensors header is too large`锛堟瀬鏄撹鍒や负鏍煎紡闂锛夈€?蹇呴』鍦ㄤ笅杞藉悗鏍￠獙鏂囦欢澶у皬锛坒p8 7.13GB / te 9.35GB / vae 675MB锛夈€?
## 浜虹墿涓€鑷存€э紙鍙傝€冨浘 / 鎹㈣。鐫€鎹㈣〃鎯咃級

閫氳繃 `/v1/images/edits` 瀹炵幇锛屽凡鍦?DSH 鐨?`edit_image` 宸ュ叿涓婇獙璇侀€氳繃锛堝悓涓€寮犺劯鎹?5 濂楅€犲瀷浜斿畼瀹屽叏涓€鑷达級銆?
**宸ヤ綔娴佹帴绾?*锛?
```
鍙傝€冨浘 鈹€鈹€LoadImage鈹€鈹€鈻?TextEncodeQwenImage21.images 鈹€鈹€鈹?                                                    鈹溾攢鈻?閲囨牱 鈹€鈻?鍑哄浘
鎻忚堪鏂囧瓧锛堣。鏈?鍔ㄤ綔/琛ㄦ儏/鍦烘櫙锛夆攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?```

`TextEncodeQwenImage21` 鐨?`images` 鏀寔 **1~16 寮?*锛坄image_1` 鈥?`image_16`锛夛紝鏄畼鏂瑰師鐢熻兘鍔涳紝涓嶉渶瑕?IP-Adapter銆?
**缃戝叧渚ц鍋氫笁浠朵簨**锛?1. 瑙ｆ瀽 `multipart/form-data`锛堢敤 `email.parser.BytesParser`锛宍cgi` 妯″潡鍦?Python 3.13 宸茬Щ闄わ級
2. 鎶婂弬鑰冨浘 `POST /upload/image` 涓婁紶鍒?*姣忎釜瑕佺敤鍒扮殑** ComfyUI 瀹炰緥锛屾嬁鍒拌繑鍥炵殑鏂囦欢鍚?3. 宸ヤ綔娴侀噷鍔?`LoadImage` 鑺傜偣锛屾妸 `te_inputs["images"] = {"image_1": ["6", 0]}` 鎺ヤ笂

**prompt 鍐欐硶寰堝叧閿?*鈥斺€斿紑澶村繀椤绘槑纭攣瀹氳韩浠斤細

> 淇濇寔杩欎綅濂虫€х殑闈㈤儴鐗瑰緛鍜岃韩浠藉畬鍏ㄤ笉鍙橈紙鍚屾牱鐨勮劯鍨嬨€佺溂鐫涖€侀蓟瀛愩€佸槾鍞囥€佺毊鑲わ級锛屾敼涓猴細<鏂拌。鐫€>锛?鏂板姩浣?琛ㄦ儏>锛?鏂板満鏅?

缂栬緫璺緞杈撳嚭鐨勫昂瀵哥敱 `resolution` 鍐冲畾锛?024 妗?鈫?1024脳1536锛夈€?
## 楂樻竻杈撳嚭锛?080p / 2K / 4K锛?
**鏍稿績绛栫暐锛氫綆鍒嗙敓鎴?鈫?4x-UltraSharp 瓒呭垎 鈫?lanczos 缂╁洖鐩爣**

```
鐩爣 1920脳1080 鈫?鐢熸垚 768脳432锛堢害 75s锛夆啋 4x 鏀惧ぇ鍒?3072脳1728 鈫?缂╁洖 1920脳1080锛堢害 17s锛?                                                                  鍚堣绾?92 绉?```

涓轰粈涔堜笉鑳界洿鎺ョ敓鎴愬ぇ鍥撅紙瀹炴祴鏁版嵁锛夛細

| 鍋氭硶 | 鑰楁椂 | 鐢昏川 |
| --- | --- | --- |
| 鐩寸敓 1920脳1080 | **396 绉?* | 鏃犱吉褰憋紝浣嗗お鎱紙6 寮犺 40 鍒嗛挓锛?|
| 鐢熸垚 480 鈫?4x 鐩村嚭 1920 | 38 绉?| 鉂?灞变綋/鐨偆鍑虹幇楸奸鏉＄汗锛?x 绾圭悊鎷変几锛?|
| **鐢熸垚 768 鈫?4x 鈫?缂╁洖 1920** | **92 绉?* | 鉁?骞插噣锛岀瓑鏁?2.5x 鏀惧ぇ |

**鍏抽敭**锛氬厛鏀惧ぇ鍐?*缂╁洖**銆?x 妯″瀷鏀惧ぇ鍒?3072 鍚庣敤 `ImageScale`(lanczos) 缂╁埌 1920锛?鐩稿綋浜庤 4x 妯″瀷骞?2.5x 鐨勬椿锛岀汗鐞嗕笉浼氳鎷変几澶辩湡銆?
宸ヤ綔娴佺墖娈碉細

```python
g["20"] = {"class_type": "UpscaleModelLoader", "inputs": {"model_name": "4x-UltraSharp.pth"}}
g["21"] = {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["20",0], "image": ["12",0]}}
g["22"] = {"class_type": "ImageScale", "inputs": {"image": ["21",0], "method": "lanczos",
           "width": target_w, "height": target_h, "crop": "disabled"}}
```

瓒呭垎妯″瀷锛歚4x-UltraSharp.pth`锛?6.9MB锛夛紝鏀?`models/upscale_models/`锛?涓嬭浇婧?`https://hf-mirror.com/lokCX/4x-Ultrasharp/resolve/main/4x-UltraSharp.pth`銆?
**瑙﹀彂鏂瑰紡**锛氳姹傚甫 `upscale: true`锛屾垨 `size` 鐢ㄦ。浣嶅悕 `1080p` / `2k` / `4k`锛堣嚜鍔ㄥ惎鐢級銆?
### 鈿狅笍 棰樻潗鍐冲畾鏀惧ぇ鏂瑰紡锛堝疄娴嬭俯杩囷級

| 棰樻潗 | 鎺ㄨ崘 | 鍘熷洜 |
| --- | --- | --- |
| 椋庢櫙 / 寤虹瓚 / 澶х汗鐞?| 768 鈫?4x 瓒呭垎 鈫?缂╁洖 | AI 瓒呭垎鑳借ˉ鍑鸿川鎰熺粏鑺?|
| **浜哄儚 / 鎵?/ 灏忕墿浠?* | **1024 鐩寸敓 鈫?lanczos 鏀惧ぇ** | AI 瓒呭垎浼氣€滅紪閿欌€濅簲瀹?|

**瀹炴祴妗堜緥**锛?68脳432 鐢熸垚 + 4x 瓒呭垎鍑虹殑姘戝浗鏃楄浜哄儚锛屾斁澶у埌 236% 妫€鏌ユ椂
**榧绘涓棿鍑虹幇妯悜鏂銆侀蓟澶寸粨鏋勯敊浣?*銆傛敼 1024脳576 鐩寸敓 + `PIL.Image.resize(LANCZOS)`
鏀惧ぇ鍒?1920脳1080 鍚庯紝榧诲瓙缁撴瀯瀹屾暣杩炶疮銆?
**鍘熺悊**锛?68 鍒嗚鲸鐜囦笅浜鸿劯榧诲瓙鍙崰绾?20 鍍忕礌锛孉I 瓒呭垎鏄敓鎴愬紡鐨勶紝瑕侀潬璁粌缁忛獙鈥滅寽鈥?鍑鸿繖浜涘儚绱狅紝灏忕粨鏋勬渶瀹规槗鐚滈敊锛沴anczos 鏄暟瀛︽彃鍊硷紝鍙仛骞虫粦锛?*涓嶄細鏀瑰彉缁撴瀯**銆?
**鎴愭湰**锛?024 鐩寸敓绾?108 绉掞紝涓庤秴鍒嗘柟妗堬紙92 绉掞級鐩稿綋锛屼汉鍍忓満鏅病鏈夌悊鐢辩敤瓒呭垎銆?
鏈湴鎻掑€兼斁澶т竴琛屼唬鐮侊細

```python
from PIL import Image
im.resize((1920, 1080), Image.LANCZOS).save(out)
```

## 瀹炴祴鑰楁椂鎬昏〃锛圱4脳2锛孎P8锛? 姝?Turbo锛?
| 璇锋眰 | 瀹為檯杈撳嚭 | 鑰楁椂 | 澶囨敞 |
| --- | --- | --- | --- |
| `size: "1:1"` | 1024脳1024 | ~110s | 榛樿姣斾緥妗?|
| `size: "16:9"` | 1024脳576 | ~105s | 榛樿姣斾緥妗?|
| **`size:"1920x1080", upscale:true`** | **1920脳1080** | **92s** | 猸?鎺ㄨ崘楂樻竻璺緞 |
| `size: "2k"` | 2048脳1152 | ~100s | 鑷姩瓒呭垎 |
| `size:"1920x1080"`锛堜笉瓒呭垎锛?| 1920脳1088 | 396s | 鉂?澶參锛岀鐢?|
| 鎵归噺 `n=2`锛堝弻鍗★級 | 2 寮犲悓灏哄 | 鈮?鍗曞紶 +5s | 鍙屽疄渚嬪苟琛?|
| 缂栬緫锛堝弬鑰冨浘锛?| 1024脳1536 | ~103s | resolution=1024 妗?|

**鎵归噺灏哄鑷姩鏀舵暃**锛歚n=1` 鍏佽鍒?1920 闀胯竟锛沗n=2` 鏀跺埌 1280锛沗n鈮?` 鏀跺埌 640 鈥斺€?淇濊瘉鎬绘椂闀夸粛鍦?DSH 鐨?240s 鍐呫€?
## 鍙傝€冨浘缂撳瓨

鍚屼竴寮犲弬鑰冨浘鍦ㄥ悓涓€浼氳瘽鍐呴噸澶嶄娇鐢ㄦ椂锛屾寜 `sha256` 鍛戒腑缂撳瓨鐩存帴澶嶇敤 ComfyUI 閲岀殑鏂囦欢锛屽厤鍘婚噸鏂颁笂浼狅紙2MB 澶у浘鑳界渷 1~4 绉?娆★級銆傝法浼氳瘽澶辨晥锛堝鍣ㄩ攢姣佸嵆娓呯┖锛夛紝閫昏緫鏃犲壇浣滅敤銆?
## 鍙屽崱璇存槑

涓ゅ紶 T4 **涓嶈兘**鍚堝苟鎴?32GB 鎴?2脳 鍗曞崱绠楀姏锛堟棤 NVLink锛孋omfyUI 涓嶆敮鎸佸紶閲忓苟琛岋級銆?浣?*鍙互**鐢ㄤ袱涓嫭绔嬪疄渚嬭涓ゅ紶鍗″悇骞插悇鐨勬椿 鈥斺€?宸查獙璇佹湁鏁堬細

```python
for port, dev in ((8188, 0), (8189, 1)):
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(dev)   # 鍏抽敭锛氱敤鐜鍙橀噺闅旂锛屼笉瑕佺敤 --cuda-device
    subprocess.Popen(["python", "main.py", "--listen", "0.0.0.0", "--port", str(port)],
                     cwd=COMFY, env=env, stdout=open(log,"w"), stderr=subprocess.STDOUT)
```

**瀹炴祴鏁版嵁锛圦wen-Image-2.1-Turbo FP8锛屾祴璇曟椂鐢?640脳640锛?*锛?
| 鍦烘櫙 | 鍗曞疄渚嬩覆琛?| 鍙屽疄渚嬪苟琛?|
| --- | --- | --- |
| 2 寮?| ~170s | **86s锛堢害 2脳锛?* |
| 1 寮?| ~80s | ~80s锛堟棤宸埆锛?|

> 鍙︽湁骞跺彂楠岃瘉锛氬悓鏃跺彂 2 涓?`n=1` 璇锋眰 鈫?**74 绉?*瀹屾垚锛堣瘉鏄庣綉鍏宠疆璇㈡妸涓や釜璇锋眰鍒嗗埌浜嗕袱寮犲崱锛夈€?
娉ㄦ剰鐐癸細
- `--cuda-device` 浼氳杩涚▼璧锋潵浣嗕笉鐩戝惉绔彛锛?*蹇呴』**鏀圭敤 `CUDA_VISIBLE_DEVICES` 鐜鍙橀噺
- 涓や釜瀹炰緥鍏变韩 `models/`锛堝彧璇诲畨鍏級锛岃緭鍑虹洰褰曞悇鑷嫭绔嬮伩鍏嶉噸鍚?- 鏄惧瓨锛氭瘡涓疄渚嬮兘瑕?16.5GB锛團P8 7.13 + TE 9.35锛? 鍗曞崱 15GB锛屽悇鑷?swap锛汻AM 涔熶細鍚冪揣锛圞aggle 涓婇檺 30GB锛屼細鎺ヨ繎婊¤浇锛?- 缃戝叧渚?`MAX_N = 2 if len(PORTS) == 1 else 4`锛屾寜瀹為檯瀹炰緥鏁拌皟鏁存壒閲忎笂闄?
## 鐩稿叧鏂囦欢

- `scripts/comfyui_kaggle_cell.py` 鈥?Cell 1锛氳 ComfyUI + 涓嬫ā鍨?+ 鍚弻瀹炰緥 + UI 闅ч亾
- `scripts/comfyui_gateway_cell.py` 鈥?Cell 2锛歄penAI 缃戝叧锛堝弻鍗¤疆璇?蹇冭烦/瓒呭垎/鍙傝€冨浘缂撳瓨锛? 鍛藉悕闅ч亾
- `references/troubleshooting.md` 鈥?鏁呴殰鎺掓煡鎵嬪唽锛堟寜鐜拌薄鏌ワ級
- `references/verified-values.md` 鈥?宸查獙璇佺殑鍏蜂綋鍙傛暟鍊硷紙闅ч亾 ID銆佸煙鍚嶃€佹ā鍨嬪湴鍧€銆佸疄娴嬭€楁椂锛?
## 鑳藉姏娓呭崟锛坴23 宸查獙璇侊級

| 鑳藉姏 | 鍏ュ彛 | 瀹炴祴 |
| --- | --- | --- |
| 鏂囩敓鍥撅紙姣斾緥妗ｏ級 | `size: 1:1 / 16:9 / 9:16 鈥 | 1024 绾э紝绾?105~110s |
| 楂樻竻鏂囩敓鍥?| `size: 1920x1080 + upscale: true` | 1920脳1080锛?2s |
| 2K | `size: "2k"` | 2048脳1152锛寏100s |
| 鎵归噺 | `n: 2`锛堝弻鍗″苟琛岋級 | 2 寮犵害 90s |
| 浜虹墿涓€鑷存€?+ 鎹㈣ | `POST /v1/images/edits` | 1024脳1536锛寏103s |

## 瀹夊叏鎻愰啋

- 闅ч亾鍩熷悕**鏃犻壌鏉?*锛岀煡閬撳湴鍧€鐨勪汉閮借兘娑堣€椾綘鐨?GPU 棰濆害锛屽埆澶栦紶
- CF Token銆並aggle Token 瀛樻枃浠讹紝涓嶈璐磋繘瀵硅瘽
- 鐢ㄥ畬鍦?Kaggle 鍚庡彴 **Stop Session**锛屽惁鍒欐寔缁秷鑰楁瘡鍛?30 灏忔椂棰濆害
