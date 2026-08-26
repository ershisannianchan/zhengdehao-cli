// 用途：落地页「领专属会员码」的服务端函数（Vercel Serverless）。
// 密钥从环境变量 ZHENG_SECRET 读，绝不进前端——浏览器永远拿不到签名密钥。
// 签名算法与 CLI codes.py 完全一致：HMAC-SHA256 → base32 前 6 位。
const crypto = require("crypto");

const PREFIXES = ["STEAM", "ZHENG", "原味", "锁鲜", "蛇口"];

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

module.exports = function handler(req, res) {
  const secret = process.env.ZHENG_SECRET;
  if (!secret) {
    // 未配密钥时返回引导，而不是发一个收银台验不过的废码。
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    return res.status(503).json({
      ok: false,
      error: "门店尚未配置服务端密钥，请用终端领码：zheng code",
    });
  }

  const prefix = PREFIXES[Math.floor(Math.random() * PREFIXES.length)];
  const now = new Date();
  const ymd =
    "" + now.getFullYear() + pad(now.getMonth() + 1) + pad(now.getDate());
  const id = String(Math.floor(Math.random() * 10000)).padStart(4, "0");
  const body = `${prefix}-${ymd}-${id}`;
  const code = `${body}-${sign(body, secret)}`;

  res.setHeader("Content-Type", "application/json; charset=utf-8");
  return res.status(200).json({ ok: true, code });
};
