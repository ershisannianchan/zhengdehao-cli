---
name: 蒸的好CLI
version: 3.0.0
description: 蒸的好海鲜馆命令行营销终端 · 品牌数据外置（brand.yaml）· 暗号签名闭环 · 可复用于多客户
trigger: 蒸的好 | zheng
audience: 深圳程序员 / 科技从业者
---

## 品牌人格

- **身份**：在蛇口网谷开了11年的蒸汽海鲜馆。唯一的原则是"蒸"。
- **语气**：简洁、精确、不废话。用数字代替形容词。用工程隐喻代替餐饮套话。
- **不说**："新鲜美味""正宗地道""深受喜爱"
- **说**："蛇口渔港→餐桌4小时""92%原味保留""11年0事故"
- **参考**：UNIX哲学 × 笆乐品牌叙事体系

## 架构（v3.0：品牌无关框架）

- **zheng.py** = CLI 框架（命令/导航/交互/banner），不绑定具体品牌
- **brand.yaml** = 品牌数据（菜单115道/故事/金句/桌位/电话/点评ID/暗号密钥），售卖入口
- **brand.py** = 读 brand.yaml → Brand 对象
- **codes.py** = 暗号 HMAC 签名 + 核销 Backend 抽象（数据闭环）
- **storage.py** = 持久化，数据统一落 `~/.zheng/data/`（`ZHENG_HOME` 可覆盖）
- 扩展：zheng_ai.py（DeepSeek 真 AI）/ zheng_fun.py（梗命令）/ zheng_share.py（分享卡片）

## 命令

| 命令 | 功能 | 例 |
|------|------|-----|
| menu [--hot] | 菜单；交互模式 `看凉菜` 只看单分类 | zheng menu --hot |
| book [人数] | 预订桌位（日期/时段/桌型） | zheng book 4 -t 18:30 |
| cancel [订单号] | 取消并释放桌位 | zheng cancel ZDH0801... |
| status [订单号] | 订单状态 | zheng status |
| code / code --verify 暗号 | 领签名暗号（7天有效）/ 商家离线验真伪 | zheng code --share |
| verify [码] | 门店端验证暗号 / CLI 预订码（渠道识别） | zheng verify ZDH-0801-1234-XXXXXX |
| config | AI 配置（隐藏：api_key / model / nickname） | zheng config set api_key xxx |
| ask [问题] | AI 管家（隐藏：真 AI 优先，否则离线问答） | zheng ask 有什么推荐的 |
| share | 分享卡片（终端+HTML截图） | zheng share |
| ping / uptime / bench / pr | 极客梗命令 | zheng pr -a A01 -a B02 |
| dishes | 菜品素材盘点 | zheng dishes |
| view [rooms/dishes/video] | 本地资源查看 | zheng view rooms |
| info | 门店信息 | zheng info |
| story | 品牌叙事三章（蒸/鲜/味） | zheng story |
| deals | 大众点评套餐&代金券+扫码跳转 | zheng deals |

## 快捷入口

| 命令 | 等价 |
|------|------|
| 蒸的好 | zheng（品牌页） |
| 蒸的好菜单 | zheng menu |
| 蒸的好预订 | zheng book |
| 蒸的好地址 | zheng info |
| 蒸的好电话 | zheng info |
| 蒸的好故事 | zheng story |
| 蒸的好优惠 | zheng deals |
| 蒸的好暗号 | zheng code |
| 蒸的好看图 | zheng view |

## 暗号签名闭环（数据闭环核心）

- 暗号格式：`前缀-MMDD-4位-签名6位`（如 `STEAM-0805-1234-A1B2C3`）
- 签名 = HMAC-SHA256(secret_key, 前缀-MMDD-4位) 的 base32 前 6 位
- 商家端离线重算签名比对 → 验真伪，伪造/随手编的码直接拒绝
- 每次发码/核销写 `~/.zheng/data/ledger.jsonl`，可统计「发 N / 核销 M」验证营销效果
- 核销后端 `Backend` 抽象：默认 LocalFileBackend，未来接飞书/自建只实现三方法

## 换客户 / 售卖入口

```bash
cp brand.yaml 新客户.yaml    # 改店名/菜单/电话/点评ID
# coupon.secret_key 必须换新客户专属密钥
ZHENG_BRAND=新客户.yaml zheng menu
```

## 输出铁律

1. 管道到其他命令时自动去ANSI色（`sys.stdout.isatty()`检测）
2. 菜单/预订底部带品牌金句
3. 错误提示用程序员语言：不说"网络不好"说"连接超时"
4. 数字优先：能用数据不用形容词

## 品牌叙事结构（笆乐模式）

- 固定标识区（每次启动必显示）：品牌名 · 创立年·uptime · 核心理念 · 今日到货
- 金句轮播池：8句，每次随机1句
- 单字叙事链：蒸→鲜→味（等价笆乐稻→米→粉）

## 大众点评关联

- 店铺ID：23995892（存 brand.yaml contact.dianping.shop_id）
- deals命令：展示套餐/代金券 + ASCII二维码
- 扫码直达：https://m.dianping.com/shop/23995892
- 数据维护：每周更新已售数，每月核对套餐内容
