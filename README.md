# 🦞 蒸的好海鲜馆 CLI

> 深圳南山蛇口 · 蒸汽锁鲜 · 命令行营销终端  
> v3.0 —— 品牌数据外置，一套框架可复用于多个餐饮客户

## 这是什么

给程序员客群做的餐饮营销 CLI：终端里看菜单、领暗号、看品牌故事、玩梗命令，
截图即传播。核心设计是**「一套 CLI 框架 + 每客户一个 brand.yaml 配置」**，
换客户不用改代码，只换配置。

## 安装

```bash
# 1. 确认 Python 版本（需要 3.8+）
python --version

# 2. 安装（开发模式，改代码即时生效；自动装 click / qrcode / PyYAML）
pip install -e .

# 3. 验证
zheng --help
```

安装后 `zheng` 命令在任何终端直接可用（cmd / PowerShell / Git Bash 通用）。

## 使用方法

```bash
zheng --help          # 查看所有命令
zheng menu            # 查看菜单
zheng menu --hot      # 只看招牌菜
zheng book 4          # 预订4人桌
zheng cancel [订单号] # 取消订单 / 释放桌位
zheng status          # 查看订单（预订记录）
zheng code            # 领专属 8 折暗号（7天有效，可分享）
zheng code --verify <暗号>   # 商家端验证暗号真伪（离线可验）
zheng share           # 生成分享卡片
zheng ping / uptime / bench / pr   # 极客梗命令
zheng deals           # 大众点评套餐 & 代金券
zheng info            # 门店信息
zheng story           # 品牌故事（蒸/鲜/味）
zheng ask             # AI 管家（配置 api_key 后走 DeepSeek，否则离线问答）
```

## 架构（v3.0）

```
zheng.py       # CLI 框架：品牌无关的命令/导航/交互/banner
brand.py       # 读 brand.yaml → Brand 对象（售卖入口）
brand.yaml     # 品牌数据：菜单/故事/金句/桌位/联系/暗号规则
codes.py       # 暗号 HMAC 签名闭环 + 核销 Backend 抽象
storage.py     # 持久化：数据统一落 ~/.zheng/data/
zheng_ai.py    # 真 AI 问答（DeepSeek）
zheng_fun.py   # 梗命令（ping/uptime/bench/pr）
zheng_share.py # 分享卡片
```

- **品牌数据外置**：菜单 115 道、故事、金句、电话全部在 `brand.yaml`，代码零绑定。
- **数据闭环**：暗号改为 **HMAC 签名码**（`STEAM-0805-1234-XXXXXX`），
  商家离线即可验真伪，伪造/随手编的码直接拒绝；每次发码/核销写 `~/.zheng/data/ledger.jsonl`，
  30 天后可统计「发 N / 核销 M」回答「有没有用」。
- **可插拔后端**：核销后端抽象成 `Backend` 接口，默认本地日志，未来接飞书/自建只需实现三方法。

## 数据在哪里

所有运行时数据（订单 / 桌位 / 暗号 / 核销日志）统一落 `~/.zheng/data/`，
可用环境变量 `ZHENG_HOME` 覆盖根目录。不再写包目录，升级不丢数据。

## 换客户 / 售卖入口

```bash
# 1. 复制一份品牌配置
cp brand.yaml 新客户.yaml

# 2. 改数据（店名/菜单/电话/点评ID/暗号密钥）
#    注意：coupon.secret_key 必须更换为新客户专属密钥

# 3. 用环境变量指定配置启动
ZHENG_BRAND=新客户.yaml zheng menu
```

一套框架，N 个客户各一份 yaml。密钥不同则暗号互相不可伪造。

## 命令速查

| 命令 | 说明 |
|------|------|
| `menu [-c 分类/--hot/--all]` | 菜单；交互模式 `看凉菜` 只看单分类 |
| `book [人数]` | 预订桌位（日期/时段/桌型） |
| `cancel [订单号]` | 取消订单并释放桌位 |
| `status [订单号]` | 订单状态 |
| `code` / `code --verify 暗号` | 领签名暗号 / 商家独立验真伪 |
| `verify [码]` | 门店端验证暗号 / CLI 预订码 |
| `share` | 分享卡片（终端 + HTML 截图） |
| `ping` / `uptime` / `bench` / `pr` | 极客梗命令 |
| `dishes` | 菜品素材盘点 |
| `img [编号]` | 查看菜品图片（有素材的菜带 📷） |
| `view [rooms/dishes/video]` | 查看本地资源 |
| `deals` | 大众点评套餐 & 代金券 + 扫码 |
| `story` | 品牌故事（蒸/鲜/味） |
| `ask [问题]` | AI 管家（隐藏命令，需 `config set api_key`） |
| `info` | 门店信息 |

## 商家端验证 & 分享

**验证暗号（收银时，离线可验）**

```bash
zheng code --verify <顾客报的暗号>   # 例：zheng code --verify STEAM-0805-1234-A1B2C3
zheng verify <码>                    # 通用验证：暗号 / CLI 预订码都支持
```

- 暗号 = 前缀 + 日期段 + 4 位 + **6 位 HMAC 签名**，商家端无需联网/共享文件即可验真伪。
- 生成日起 **7 天有效**，过期或伪造码直接拒绝。
- CLI 预订码 = `ZDH-日期段-4位-签名`，识别 CLI 渠道，当日及之后 30 天内有效。

**分享给同事**

```bash
zheng code --share    # 生成暗号 + 分享文案，自动复制剪贴板
zheng share           # 生成分享卡片（终端 ASCII + share.html 截图版）
```

## v3.0 变更

- **品牌数据外置**：菜单/故事/金句/电话/点评ID 迁到 `brand.yaml`，代码品牌无关。
- **暗号签名闭环**：HMAC 签名防伪造，新增核销日志（数据闭环）。
- **数据目录统一**：运行时数据迁 `~/.zheng/data/`，支持 `ZHENG_HOME` 覆盖。
- **砍掉点餐/支付**：定位聚焦传播，到店点餐/现场结算。
- **修复跨年 bug**：12 月发的暗号次年 1 月验证不再误判「未来无效」。
- **补测试**：暗号签名/跨年/日期解析/菜单加载，`pytest -q` 全绿。

## 关于

蒸的好海鲜馆·蒸汽海鲜（蛇口网谷店）  
大众点评收录11年 · 评分4.8分  
主打蒸汽锁鲜技术，新鲜直采，保留海鲜原味。

📍 深圳市南山区南海大道万融大厦C座G层101  
🚇 地铁2号线水湾站D口步行约410米  
📞 0755-26922888  
🕐 10:00 - 22:30 全年无休
