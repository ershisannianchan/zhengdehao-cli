# 🦞 蒸的好海鲜馆 CLI

> Steam is the sauce. —— 给程序员客群做的餐饮营销终端：在命令行里看菜单、领会员码、读品牌故事、玩极客梗，截图即传播。

这是一个**品牌可配置的餐饮营销 CLI 框架**：代码与品牌数据完全分离，整套终端的品牌、菜单、故事、优惠规则全部来自一份 `brand.yaml`。仓库内置的示例是深圳一家真实蒸汽海鲜店的配置，换上你自己的 yaml，就是另一家店。

## 它长什么样

```bash
$ zheng
╔══════════════════════════════════════════════════╗
║   蒸的好海鲜馆 · 蒸汽海鲜（蛇口网谷店）
║   Established 2015 · Steam is the sauce. · 11y uptime
╚══════════════════════════════════════════════════╝
  门店  故事  菜单  预订  优惠  暗号
```

进入交互模式后直接说人话：`菜单` / `预订 4人` / `看海鲜` / `暗号`。

## 快速开始

```bash
git clone https://github.com/ershisannianchan/zhengdehao-cli.git
cd zhengdehao-cli
pip install -e .
zheng --help
```

需要 Python 3.8+，依赖只有 click / qrcode / PyYAML。

## 核心命令

| 命令 | 说明 |
|------|------|
| `zheng menu [-c 分类/--hot/--all]` | 菜单浏览，交互模式支持 `看凉菜` |
| `zheng book [人数]` | 预订桌位（日期/时段/桌型，桌位按时段占用） |
| `zheng cancel / status` | 取消预订 / 查订单 |
| `zheng code` | 领专属会员码（HMAC 签名，门店离线可验真伪） |
| `zheng verify <码>` / `zheng verify --file 登记本.txt` | 门店端验证会员码 / 暗号 / 预订码；--file 批量对账 |
| `zheng share` | 生成终端分享卡片 + HTML 截图版 |
| `zheng ping / uptime / bench / pr` | 极客梗命令（ping 渔港、点菜走 PR 流程……） |
| `zheng ask` | AI 管家（配 DeepSeek api_key 后是真 AI，否则离线问答） |
| `zheng deals / info / story` | 点评二维码 / 门店信息 / 品牌故事 |

## 暗号签名闭环（为什么门店敢认这个码）

会员码格式：`前缀-签发日-4位-HMAC签名`，例如 `STEAM-20260826-1234-A1B2C3`。

- 门店端 `zheng verify <码>` **离线重算签名即可验真伪**，伪造/随手编的码直接拒绝
- 每次发码/核销写入本地 JSONL 日志（`~/.zheng/data/ledger.jsonl`），`zheng stats` 输出回头率
- 核销后端抽象成 `Backend` 接口，默认本地日志，接飞书/自建后端只需实现三个方法

**密钥配置**（门店侧必做）：签名密钥不进仓库。按优先级读取 `ZHENG_SECRET` 环境变量 → `~/.zheng/secret` 文件。未配置时 CLI 拒绝发码（空密钥签出的码任何人都能伪造）。

```bash
python -c "import secrets; print(secrets.token_hex(16))" > ~/.zheng/secret
```

⚠️ 换密钥会让所有已发出的旧码失效，投放物料之前换成本为零。

## 换成你自己的品牌

```bash
cp brand.yaml 你的品牌.yaml   # 改店名/菜单/电话/点评 shop_id/暗号前缀
ZHENG_BRAND=你的品牌.yaml zheng menu
```

框架代码零改动。`brand.py` 里的 `Brand` 对象负责全部品牌字段的结构化访问。

## 附：落地页领码（可选）

`index.html` + `api/issue-code.js` 是一套 Vercel 部署的配套落地页：用户填手机号领会员码（手机号经 HMAC 哈希后存 Vercel KV，不存明文）。部署时配置环境变量 `ZHENG_SECRET`（与门店 CLI 一致）和 `ZHENG_PREFIXES`（与 brand.yaml 的 `coupon.prefix` 一致）。

## 开发

```bash
python -m pytest tests -q   # 20 个测试：签名防伪/跨年/日期解析/菜单结构/CLI 集成
```

数据落盘统一在 `~/.zheng/data/`（可用 `ZHENG_HOME` 覆盖），不污染包目录。

## License

代码 MIT（见 LICENSE）。`brand.yaml` 中「蒸的好海鲜馆」为真实门店的示例数据，品牌权利归门店所有——换成你自己客户的配置即可自由商用。
