# 文生图 Prompt 配置

## 画风说明

| 画风 ID        | 中文名称     | 风格特点                             |
|----------------|--------------|--------------------------------------|
| photorealistic | 超写实摄影   | 相机感、皮肤纹理、景深虚实、RAW质感  |
| showa          | 昭和画风     | 90年代日本动画风格、手绘赛璐璐感     |
| anime          | 二次元动漫   | 现代日式动画、大眼睛、线条清晰       |
| oil_painting   | 艺术油画     | 印象派笔触、奇幻氛围、Ghibli风       |

## 衣物状态映射

| 状态类型      | 匹配关键词                              | 英文 SD 标签                              |
|---------------|-----------------------------------------|-------------------------------------------|
| naked         | 全裸、裸体、naked、nude、一丝不挂       | `naked, nude, completely nude`            |
| half_naked    | 半裸、半褪、topless、裸露、bottomless   | `half naked, topless, exposed breasts, bottomless` |
| lingerie      | 内衣、内裤、lingerie、panties、bra      | `lingerie, panties only, bra`             |
| messy         | 凌乱、messy、torn、disheveled           | `messy clothes, torn clothes, disheveled` |
| fully_clothed | 完整衣物、fully clothed、dressed        | `fully clothed, no nudity`                |


## YAML 配置区（供程序解析）

```yaml
version: 3.0
styles:
  photorealistic:
    style_desc: "Photorealistic portrait photography, ultra-detailed skin texture with visible pores and natural imperfections, natural cinematic lighting with soft volumetric god rays, shot on Canon EOS R5 with 85mm f/1.4 lens, shallow depth of field creating beautiful bokeh background, realistic eyes with accurate reflections, 8k resolution, hyper-detailed masterpiece, raw photo aesthetic"
    constraints: "no cartoon, no illustration, no painting, no low quality, no blur, no artifacts, no oversmoothing of skin, no fused fingers, no extra limbs, no deformed hands, no mutated anatomy, no text, no watermark, no logos, no compression artifacts, anatomically correct proportions and five-fingered hands, sharp focus on subject, plain background"
  showa:
    style_desc: "Authentic 1990s Showa era Japanese anime style, classic 90s OVA aesthetic with hand-drawn cel animation look, bold expressive linework and soft cel-shading with limited gradients, nostalgic color palette featuring muted blues pinks and earth tones, detailed sparkling eyes and dramatic hair flow, retro film grain with slight chromatic aberration, inspired by 90s masterpieces like Evangelion and Sailor Moon, high detail background with atmospheric perspective, retro anime art masterpiece"
    constraints: "no photorealistic elements, no 3D render, no modern anime shine effects, no glossy gradients, no realistic skin pores, no lowres, no ugly details, no deformed anatomy, no bad anatomy, no fused fingers, no extra limbs, no deformed hands, anatomically correct proportions"
  anime:
    style_desc: "Beautiful 2D anime style illustration with classic Japanese anime character design, large sparkling expressive eyes and detailed flowing hair, vibrant yet balanced colors with clean sharp lineart and soft cel-shading, dynamic pose with emotional atmosphere, high detail face and clothing textures, anime key visual quality, absurdres masterpiece with best quality, source anime aesthetic"
    constraints: "no realistic photo appearance, no 3D rendering, no western cartoon style, no deformed face, no bad hands, no extra fingers, no fused fingers, no low quality, no blur, no overexposed areas, anatomically correct proportions and five-fingered hands"
  oil_painting:
    style_desc: "Dreamy artistic oil painting style with soft impressionist brush strokes blended with ethereal fantasy elements, vibrant yet muted dreamy colors with golden hour glow and volumetric god rays, textured canvas impasto details with subtle surreal elements like floating particles or soft bokeh, atmospheric depth and mist, inspired by Studio Ghibli backgrounds meeting classical oil painters like Monet and Klimt, intricate magical lighting on skin and fabrics, high resolution HDR masterpiece with ultra detailed enchanting atmosphere"
    constraints: "no photorealistic photo elements, no sharp digital lines, no flat colors, no modern anime cel shading, no low quality, no blur, no deformed anatomy, no harsh shadows, anatomically correct proportions"
```
clothing_state_mappings:
  naked:
    keywords: ["全裸", "裸体", "naked", "nude", "一丝不挂", "completely naked"]
    tags: "naked, nude, completely nude"
  half_naked:
    keywords: ["半裸", "半褪", "topless", "裸露", "bottomless", "shirt open", "exposed breasts"]
    tags: "half naked, topless, exposed breasts, bottomless"
  lingerie:
    keywords: ["内衣", "内裤", "lingerie", "panties", "bra", "情趣内衣", "garter belt"]
    tags: "lingerie, panties only, bra, garter belt"
  messy:
    keywords: ["凌乱", "messy", "torn", "disheveled", "衣服撕破", "clothes torn"]
    tags: "messy clothes, torn clothes, disheveled"
  fully_clothed:
    keywords: ["完整衣物", "fully clothed", "dressed", "穿着衣服"]
    tags: "fully clothed, no nudity"
  black_stockings:
    keywords: ["黑丝", "黑色丝袜", "black stockings", "stockings", "thigh highs", "nylon"]
    tags: "black stockings, thigh highs, nylon, pantyhose"
  tight_skirt:
    keywords: ["包臀裙", "紧身裙", "tight skirt", "pencil skirt", "miniskirt", "short skirt"]
    tags: "tight skirt, pencil skirt, short skirt, hip skirt"
  office_outfit:
    keywords: ["职业装", "衬衫", "西装", "office outfit", "business suit", "blouse", "white shirt"]
    tags: "office outfit, business attire, white shirt, blouse"
  maid_outfit:
    keywords: ["女仆装", "maid outfit", "maid dress", "apron", "女仆服"]
    tags: "maid outfit, maid dress, white apron"
```
