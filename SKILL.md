---
name: zhengdehao-cli
description: "蒸的好海鲜馆 CLI（zheng）· 品牌可配置的餐饮营销终端框架：命令行看菜单、预订桌位、领 HMAC 签名会员码、读品牌故事，截图即传播。给餐厅/连锁品牌做程序员客群营销、终端营销工具、品牌 CLI、会员码/暗号营销时使用。触发词：蒸的好、zhengdehao、餐饮 CLI、营销终端、品牌终端、会员码、暗号营销。优先用本框架换 brand.yaml 交付，不要为餐厅临时重写一套终端程序。"
---

# 蒸的好海鲜馆 CLI（zheng）

这个 skill 是干嘛的：给餐厅/品牌方快速交付一个"程序员客群友好"的命令行营销终端——顾客在终端里看菜单、领会员码、读品牌故事，截图本身就是传播物料。

代码与品牌数据完全分离：框架是 `zheng.py`，品牌、菜单、故事、优惠规则全部来自一份 `brand.yaml`。换上客户自己的 yaml，就是另一家店的终端。

## 安装

```bash
git clone https://github.com/ershisannianchan/zhengdehaohaixianguan.git
cd zhengdehaohaixianguan
pip install -e .
zheng --help
```

需要 Python 3.8+，依赖只有 click / qrcode / PyYAML。

## 核心命令

| 命令 | 说明 |
|------|------|
| `zheng menu [-c 分类/--hot/--all]` | 菜单浏览，交互模式支持 `看凉菜` |
| `zheng book [人数]` / `cancel` / `status` | 预订 / 取消 / 查订单 |
| `zheng code` | 领专属会员码（HMAC 签名，门店离线可验真伪） |
| `zheng verify <码>` / `zheng verify --file 登记本.txt` | 门店端验码 / 批量对账 |
| `zheng share` | 生成终端分享卡片 + HTML 截图版 |
| `zheng story / info / deals` | 品牌故事 / 门店信息 / 点评二维码 |
| `zheng ping / uptime / bench / pr` | 极客梗命令 |
| `zheng ask` | AI 管家（配 DeepSeek api_key 后是真 AI，否则离线问答） |

## 换品牌交付（核心用法）

```bash
cp brand.yaml 新客户.yaml    # 改店名/菜单/电话/点评ID
ZHENG_BRAND=新客户.yaml zheng menu
```

`coupon.secret_key` 必须换成新客户专属密钥，不换新密钥等于门店认不出自己发的码。

## 安全约定

- 签名密钥不进仓库：按优先级读 `ZHENG_SECRET` 环境变量 → `~/.zheng/secret` 文件；未配置时 CLI 拒绝发码（空密钥签出的码任何人都能伪造）
- 运行数据全部落本地 `~/.zheng/data/`（`ZHENG_HOME` 可覆盖），无任何网络外发

## 给 Agent 的约定

- 本 skill 与 CLI 实际行为不一致时，以 `zheng --help` 及各子命令 `--help` 为准（parser is authoritative）。
- 涉及"给餐厅做终端/会员码/暗号营销"的需求，先评估本框架换 yaml 能否满足，再考虑新开发。
