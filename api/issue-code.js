// 用途：落地页「领专属会员码」的服务端函数（Vercel Serverless）。
// 密钥从环境变量 ZHENG_SECRET 读，绝不进前端。签名算法与 CLI codes.py 一致。
// 手机号：POST body 传，SHA256 哈希后存 KV（不存明文，回头率用哈希去重）。
// 前缀：从 ZHENG_PREFIXES 环境变量读（逗号分隔），与 brand.yaml coupon.prefix 保持一致。
const crypto = require("crypto");

const PREFIXES = (process.env.ZHENG_PREFIXES || "STEAM,ZHENG,原味,锁鲜,蛇口")
  .split(",").map((s) => s.trim()).filter(Boolean);
const PHONE_RE = /^1\d{10}$/;

function base32(bytes) {
  const A = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = 0, val = 0, out = "";
  for (const b of bytes) {
    val = (val << 8) | b;
    bits += 8;
    while (bits >= 5) {
      out += A[(val >>> (bits - 5)) & 31];
      bits -= 5;
    }
  }
  if (bits > 0) out += A[(val << (5 - bits)) & 31];
  return out;
}

function sign(body, secret) {
  const hmac = crypto.createHmac("sha256", secret).update(body, "utf8").digest();
  return base32(hmac).slice(0, 6);
}

function pad(n) {
  return String(n).padStart(2, "0");
}

function phoneHash(phone) {
  return crypto.createHash("sha256").update(phone).digest("hex");
}

// 写 KV（配了 KV 才写；失败不影响发码）
async function kvSet(key, value) {
  const url = process.env.KV_REST_API_URL;
  const token = process.env.KV_REST_API_TOKEN;
  if (!url || !token) return false;
  try {
    await fetch(`${url.replace(/\/$/, "")}/set/${encodeURIComponent(key)}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ value }),
    });
    return true;
  } catch (e) {
    return false;
  }
}

module.exports = async function handler(req, res) {
  res.setHeader("Content-Type", "application/json; charset=utf-8");

  const secret = process.env.ZHENG_SECRET;
  if (!secret) {
    return res.status(503).json({
      ok: false,
      error: "门店尚未配置服务端密钥，请用终端领码：zheng code",
    });
  }

  // 手机号只从 POST body 读（不走 GET query，避免手机号留在访问日志）
  let phone = "";
  if (req.method === "POST") {
    try {
      const chunks = [];
      for await (const chunk of req) {
        chunks.push(chunk);
      }
      const body = JSON.parse(Buffer.concat(chunks).toString("utf-8") || "{}");
      phone = String((body && body.phone) || "").trim();
    } catch (e) {
      phone = "";
    }
  }
  if (phone && !PHONE_RE.test(phone)) {
    return res.status(400).json({ ok: false, error: "手机号格式不正确" });
  }

  const prefix = PREFIXES[Math.floor(Math.random() * PREFIXES.length)];
  const now = new Date();
  const ymd = "" + now.getFullYear() + pad(now.getMonth() + 1) + pad(now.getDate());
  const id = String(Math.floor(Math.random() * 10000)).padStart(4, "0");
  const body = `${prefix}-${ymd}-${id}`;
  const code = `${body}-${sign(body, secret)}`;

  // 手机号哈希后存 KV（不存明文），回头率用哈希去重
  if (phone) {
    const h = phoneHash(phone);
    await kvSet(`phone:${h}`, code);
    await kvSet(`code:${code}`, h);
  }

  return res.status(200).json({ ok: true, code, hasPhone: !!phone });
};
