# 角色声音配置

## Fish Audio 声音模型

Fish Audio 提供多种预设声音模型，可以通过 `reference_id` 参数指定。

## 预设声音列表

| 声音ID | 描述 | 适合角色类型 |
|--------|------|-------------|
| `default` | 默认女声 | 通用女性角色 |
| `zh-CN-XiaoxiaoNeural` | 中文女声 - 晓晓 | 温柔、甜美角色 |
| `zh-CN-XiaoyiNeural` | 中文女声 - 晓伊 | 活泼、年轻角色 |
| `zh-CN-YunjianNeural` | 中文男声 - 云健 | 成熟、稳重男性 |
| `zh-CN-YunxiNeural` | 中文男声 - 云希 | 年轻、阳光男性 |
| `zh-CN-YunxiaNeural` | 中文童声 - 云夏 | 萝莉、幼女角色 |
| `zh-CN-YunyangNeural` | 中文男声 - 云扬 | 中年、磁性男性 |
| `zh-CN-XiaochenNeural` | 中文女声 - 晓晨 | 知性、成熟女性 |
| `zh-CN-XiaohanNeural` | 中文女声 - 晓涵 | 清冷、高冷女性 |
| `zh-CN-XiaomengNeural` | 中文女声 - 晓梦 | 梦幻、空灵女性 |
| `zh-CN-XiaomoNeural` | 中文女声 - 晓墨 | 古风、文艺女性 |
| `zh-CN-XiaoqiuNeural` | 中文女声 - 晓秋 | 成熟、妩媚女性 |
| `zh-CN-XiaoruiNeural` | 中文女声 - 晓睿 | 干练、职场女性 |
| `zh-CN-XiaoshuangNeural` | 中文女声 - 晓双 | 俏皮、可爱角色 |
| `zh-CN-XiaoxuanNeural` | 中文女声 - 晓萱 | 温柔、治愈角色 |
| `zh-CN-XiaoyanNeural` | 中文女声 - 晓颜 | 标准、通用女性 |
| `zh-CN-XiaoyouNeural` | 中文童声 - 晓悠 | 正太、少年角色 |
| `zh-CN-XiaozhenNeural` | 中文女声 - 晓甄 | 优雅、高贵女性 |
| `ja-JP-NanamiNeural` | 日文女声 - 七海 | 日语角色 |
| `en-US-AriaNeural` | 英文女声 - Aria | 英语角色 |

## 角色声音匹配建议

### 按角色性格

- **温柔系** (女仆、姐姐): `zh-CN-XiaoxiaoNeural`, `zh-CN-XiaoxuanNeural`
- **活泼系** (妹妹、少女): `zh-CN-XiaoyiNeural`, `zh-CN-XiaoshuangNeural`
- **高冷系** (女王、御姐): `zh-CN-XiaohanNeural`, `zh-CN-XiaoqiuNeural`
- **成熟系** (人妻、OL): `zh-CN-XiaochenNeural`, `zh-CN-XiaoruiNeural`
- **可爱系** (萝莉、幼女): `zh-CN-YunxiaNeural`, `zh-CN-XiaoyouNeural`
- **古风系** (仙子、侠女): `zh-CN-XiaomoNeural`, `zh-CN-XiaozhenNeural`

### 按角色年龄

- **萝莉/正太** (7-12岁): `zh-CN-YunxiaNeural`, `zh-CN-XiaoyouNeural`
- **少女/少年** (13-17岁): `zh-CN-XiaoyiNeural`, `zh-CN-XiaoshuangNeural`
- **青年** (18-25岁): `zh-CN-XiaoxiaoNeural`, `zh-CN-XiaoyanNeural`
- **成熟** (26-35岁): `zh-CN-XiaochenNeural`, `zh-CN-XiaoqiuNeural`
- **御姐/大叔** (35岁+): `zh-CN-XiaohanNeural`, `zh-CN-YunyangNeural`

## YAML 配置区

```yaml
# Fish Audio 预设声音映射
voice_presets:
  # 温柔甜美
  gentle_sweet:
    id: "zh-CN-XiaoxiaoNeural"
    description: "温柔甜美的女声，适合女仆、姐姐类角色"
  
  # 活泼可爱
  lively_cute:
    id: "zh-CN-XiaoyiNeural"
    description: "活泼可爱的女声，适合妹妹、少女类角色"
  
  # 高冷御姐
  cold_domineering:
    id: "zh-CN-XiaohanNeural"
    description: "高冷御姐音，适合女王、高冷角色"
  
  # 成熟妩媚
  mature_charming:
    id: "zh-CN-XiaoqiuNeural"
    description: "成熟妩媚的女声，适合人妻、御姐角色"
  
  # 萝莉童声
  loli_child:
    id: "zh-CN-YunxiaNeural"
    description: "萝莉童声，适合幼女、萝莉角色"
  
  # 正太少年
  shota_youth:
    id: "zh-CN-XiaoyouNeural"
    description: "正太少年音，适合少年、正太角色"
  
  # 阳光男性
  sunny_male:
    id: "zh-CN-YunxiNeural"
    description: "阳光男声，适合年轻男性角色"
  
  # 成熟男性
  mature_male:
    id: "zh-CN-YunjianNeural"
    description: "成熟稳重的男声，适合大叔、成熟男性"
  
  # 知性优雅
  intellectual_elegant:
    id: "zh-CN-XiaochenNeural"
    description: "知性优雅的女声，适合OL、知性女性"
  
  # 梦幻空灵
  dreamy_ethereal:
    id: "zh-CN-XiaomengNeural"
    description: "梦幻空灵的女声，适合仙子、精灵角色"
  
  # 古风文艺
  ancient_literary:
    id: "zh-CN-XiaomoNeural"
    description: "古风文艺女声，适合古风、仙侠角色"
  
  # 俏皮搞怪
  playful_quirky:
    id: "zh-CN-XiaoshuangNeural"
    description: "俏皮搞怪的女声，适合活泼、调皮角色"
  
  # 治愈温柔
  healing_gentle:
    id: "zh-CN-XiaoxuanNeural"
    description: "治愈温柔的女声，适合治愈系角色"
  
  # 干练职场
  capable_professional:
    id: "zh-CN-XiaoruiNeural"
    description: "干练职场女声，适合女强人、职场角色"
  
  # 高贵优雅
  noble_elegant:
    id: "zh-CN-XiaozhenNeural"
    description: "高贵优雅的女声，适合公主、贵族角色"
  
  # 标准通用
  standard_general:
    id: "zh-CN-XiaoyanNeural"
    description: "标准通用女声，适合大多数女性角色"

# 默认声音
default_voice: "zh-CN-XiaoxiaoNeural"
```

## 使用说明

1. 在角色编辑页面选择合适的声音
2. 系统会根据角色的 `persona` 自动推荐声音
3. 如果没有设置，使用默认声音 `zh-CN-XiaoxiaoNeural`
4. 自定义声音：在 Fish Audio 平台训练自己的声音模型，填入模型ID
