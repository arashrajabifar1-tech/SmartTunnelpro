#!/usr/bin/env python3
"""Integrate failover UI with the Native Bridge contract actually shipped by Smart Tunnel."""
from pathlib import Path
import sys

MARKER = "/* Smart Tunnel v0.24.3 native failover integration */"
HTML_MARKER = '<section id="stNativeFailoverCard"'
JS_MARKER = "/* Smart Tunnel v0.24.3 native failover integration: JS */"

CSS = r"""
/* Smart Tunnel v0.24.3 native failover integration */
#stNativeFailoverCard{margin:14px 0;padding:16px;border:1px solid color-mix(in srgb,#52d9ff 20%,transparent);border-radius:20px;background:linear-gradient(145deg,color-mix(in srgb,#0b2b40 88%,transparent),color-mix(in srgb,#061725 94%,transparent));color:#e9f7ff}
#stNativeFailoverCard .stf-head{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
#stNativeFailoverCard .stf-title{font-size:15px;font-weight:800}
#stNativeFailoverCard .stf-pill{font-size:10px;border:1px solid color-mix(in srgb,#42e99a 30%,transparent);border-radius:99px;padding:5px 9px;color:#9df5c8;background:color-mix(in srgb,#42e99a 8%,transparent)}
#stNativeFailoverCard .stf-copy{font-size:12px;line-height:1.9;color:#b4ccdc;margin:10px 0}
#stNativeFailoverCard .stf-actions{display:flex;gap:8px;flex-wrap:wrap}
#stNativeFailoverCard .stf-actions button{min-height:42px;min-width:115px;border-radius:12px}
#stNativeFailoverCard .stf-status{margin-top:12px;border:1px solid color-mix(in srgb,#9ac8e8 16%,transparent);border-radius:12px;background:color-mix(in srgb,#d8eeff 4%,transparent);padding:10px 12px;font-size:12px;line-height:1.85;overflow-wrap:anywhere}
#stNativeFailoverCard .stf-status.ok{border-color:#35c98a66;color:#a8f2cb}
#stNativeFailoverCard .stf-status.bad{border-color:#fb718566;color:#ffc1ca}
#stNativeFailoverCard #stfHistory{max-height:150px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;font-size:10px;line-height:1.85;color:#9db8ce;margin:10px 0 0}
@media(max-width:560px){#stNativeFailoverCard{padding:13px;border-radius:17px}#stNativeFailoverCard .stf-actions{display:grid;grid-template-columns:1fr 1fr}#stNativeFailoverCard .stf-actions button{min-width:0;width:100%}}
"""

CARD = r"""
<section id="stNativeFailoverCard" dir="rtl" aria-labelledby="stfTitle">
  <div class="stf-head"><strong id="stfTitle" class="stf-title">پایداری و جابه‌جایی خودکار</strong><span class="stf-pill">Native HTTP probe</span></div>
  <p class="stf-copy">پایش فقط داخل APK و با پل واقعی Android کار می‌کند. پس از دو شکست پیاپی، پروفایل‌های VLESS فعال به‌ترتیب با اعتبارسنجی libbox، درخواست اتصال و آزمون HTTPS از داخل تونل بررسی می‌شوند. توقف این بخش، VPN را قطع نمی‌کند.</p>
  <div class="stf-actions"><button class="btn primary" id="stfStart" type="button">شروع پایش</button><button class="btn" id="stfStop" type="button" disabled>توقف پایش</button><button class="btn" id="stfProbe" type="button">آزمون HTTPS واقعی</button></div>
  <div class="stf-status" id="stfStatus" role="status" aria-live="polite">غیرفعال است. برای اتصال واقعی، پروفایل معتبر و مجوز VPN لازم است.</div>
  <pre id="stfHistory" aria-label="تاریخچهٔ آزمون تونل">تاریخچه خالی است.</pre>
</section>
"""

JS = r"""
<script>
/* Smart Tunnel v0.24.3 native failover integration: JS */
(function () {
  'use strict';
  const byId = id => document.getElementById(id);
  const statusEl = byId('stfStatus');
  if (!statusEl || window.__ST_NATIVE_FAILOVER_V243__) return;
  window.__ST_NATIVE_FAILOVER_V243__ = true;

  const HEALTH_URL = 'https://www.gstatic.com/generate_204';
  const MAX_HISTORY = 16;
  const pending = new Map();
  const history = [];
  let priorResult = window.smartTunnelTunnelTestResult;
  let timer = null, running = false, busy = false, failures = 0;
  let activeId = null, backoffMs = 30000;

  function status(message, kind) {
    statusEl.textContent = String(message || '');
    statusEl.className = 'stf-status' + (kind ? ' ' + kind : '');
  }
  function bridge() {
    const n = window.SmartTunnelNative;
    if (window.__ST_MOCK__) return null;
    if (!n || typeof n.getStatus !== 'function' ||
        typeof n.requestVpn !== 'function' ||
        typeof n.testThroughTunnel !== 'function' ||
        typeof n.validateConfig !== 'function') return null;
    return n;
  }
  function currentData() {
    try {
      if (typeof data !== 'undefined' && data && Array.isArray(data.profiles)) return data;
    } catch (_) {}
    return null;
  }
  function isVless(p) {
    const proto = String((p && (p.type || p.protocol || p.kind)) || '').toLowerCase();
    const uri = String((p && (p.address || p.raw || p.uri)) || '').trim().toLowerCase();
    return !!(p && p.id && p.enabled !== false && (proto === 'vless' || uri.startsWith('vless://')));
  }
  function pool() {
    const d = currentData();
    return d ? d.profiles.filter(isVless) : [];
  }
  function selected() {
    const d = currentData();
    return d && d.selectedId ? String(d.selectedId) : null;
  }
  function record(p, ok, ms, detail) {
    const e = { at: new Date().toLocaleTimeString(), name: p && (p.name || p.id) || '—',
      ok: !!ok, ms: Number.isFinite(ms) ? Math.max(0, Math.trunc(ms)) : null,
      detail: String(detail || (ok ? 'HTTP 204' : 'HTTP probe failed')).slice(0, 160) };
    history.push(e);
    if (history.length > MAX_HISTORY) history.shift();
    const target = byId('stfHistory');
    if (target) target.textContent = history.map(x =>
      x.at + ' · ' + x.name + ' · ' + (x.ok ? 'موفق' : 'ناموفق') + ' · ' +
      (x.ms == null ? '—' : x.ms + ' ms') + ' · ' + x.detail).join('\n') || 'تاریخچه خالی است.';
  }
  function callbackRouter(raw) {
    let msg = null;
    try { msg = typeof raw === 'string' ? JSON.parse(raw) : raw; } catch (_) {}
    if (msg && typeof msg.reqId === 'string' && pending.has(msg.reqId)) {
      const resolve = pending.get(msg.reqId);
      pending.delete(msg.reqId);
      resolve(msg);
    } else if (typeof priorResult === 'function') {
      try { priorResult.call(window, raw); } catch (_) {}
    }
  }
  window.smartTunnelTunnelTestResult = callbackRouter;

  function probe(p, timeoutMs) {
    const n = bridge();
    if (!n || String(n.getStatus()) !== 'connected')
      return Promise.resolve({ ok: false, ms: null, reason: 'Native VPN is not connected' });
    return new Promise(resolve => {
      const reqId = 'stf_' + Date.now() + '_' + Math.random().toString(36).slice(2, 9);
      let done = false;
      const finish = value => {
        if (done) return;
        done = true;
        clearTimeout(deadline);
        pending.delete(reqId);
        resolve(value);
      };
      const deadline = setTimeout(() => finish({ ok: false, ms: null, reason: 'Native HTTPS probe timed out' }), timeoutMs + 2500);
      pending.set(reqId, msg => {
        finish({ ok: msg.ok === true, ms: Number.isFinite(Number(msg.ms)) ? Number(msg.ms) : null,
          reason: msg.ok === true ? 'HTTPS 204 through VPN' : 'Native HTTPS probe failed' });
      });
      try {
        const result = String(n.testThroughTunnel(JSON.stringify({ reqId, url: HEALTH_URL, timeoutMs })));
        if (result.startsWith('ERROR:')) finish({ ok: false, ms: null, reason: result.slice(6) });
        else if (result !== 'OK') finish({ ok: false, ms: null, reason: 'Unexpected Native probe response' });
      } catch (e) {
        finish({ ok: false, ms: null, reason: 'Native probe call failed' });
      }
    });
  }

  function makeConfig(p) {
    if (typeof buildForPool !== 'function') throw new Error('سازندهٔ کانفیگ این نسخه در دسترس نیست.');
    const cfg = buildForPool([String(p.id)]);
    if (!cfg || typeof cfg !== 'object' || !Array.isArray(cfg.inbounds) ||
        !Array.isArray(cfg.outbounds) || !cfg.route) throw new Error('کانفیگ تولیدشده ناقص است.');
    return cfg;
  }
  function saveSelection(p, cfg) {
    const d = currentData();
    if (!d) throw new Error('حافظهٔ پروفایل‌ها در دسترس نیست.');
    d.selectedId = p.id;
    d.config = cfg;
    if (typeof save === 'function') save();
    if (typeof render === 'function') render();
    activeId = p.id;
  }
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

  async function switchProfile(previousId) {
    const n = bridge();
    const list = pool();
    if (!n || !list.length) return false;
    const idx = list.findIndex(p => p.id === previousId);
    const candidates = idx < 0 ? list : list.slice(idx + 1).concat(list.slice(0, idx + 1));
    for (const p of candidates) {
      if (!running) return false;
      try {
        const cfg = makeConfig(p);
        const json = JSON.stringify(cfg);
        const valid = String(n.validateConfig(json));
        if (valid !== 'OK') {
          record(p, false, null, valid.startsWith('ERROR:') ? valid.slice(6) : 'Native validation rejected config');
          continue;
        }
        const started = String(n.requestVpn(json));
        if (started !== 'OK') {
          record(p, false, null, started.startsWith('ERROR:') ? started.slice(6) : 'Native VPN start rejected');
          continue;
        }
        await sleep(1800);
        for (let attempt = 0; attempt < 3 && running; attempt++) {
          const result = await probe(p, 5000);
          record(p, result.ok, result.ms, result.reason);
          if (result.ok) {
            saveSelection(p, cfg);
            failures = 0; backoffMs = 30000;
            status('به پروفایل سالم «' + (p.name || p.id) + '» جابه‌جا شد؛ پاسخ HTTPS از تونل دریافت شد.', 'ok');
            return true;
          }
          if (attempt < 2) await sleep(900);
        }
      } catch (e) {
        record(p, false, null, e && e.message || 'Candidate failed');
      }
    }
    return false;
  }
  async function tick() {
    if (!running || busy) return;
    busy = true;
    let nextDelay = 60000;
    try {
      const n = bridge();
      const p = pool().find(x => x.id === activeId);
      if (!n || !p || String(n.getStatus()) !== 'connected') {
        const ok = await switchProfile(activeId);
        if (!ok) {
          nextDelay = backoffMs;
          backoffMs = Math.min(300000, backoffMs * 2);
          status('هیچ پروفایل فعال با پاسخ HTTPS تأیید نشد؛ تلاش بعدی پس از ' + Math.round(nextDelay / 1000) + ' ثانیه.', 'bad');
        }
      } else {
        const result = await probe(p, 5000);
        record(p, result.ok, result.ms, result.reason);
        if (result.ok) {
          failures = 0; backoffMs = 30000;
          status('تونل فعال است؛ آزمون HTTPS با موفقیت پاسخ گرفت (' + (result.ms == null ? '—' : result.ms + ' ms') + ').', 'ok');
        } else if (++failures >= 2) {
          failures = 0;
          const ok = await switchProfile(p.id);
          if (!ok) {
            nextDelay = backoffMs;
            backoffMs = Math.min(300000, backoffMs * 2);
            status('دو آزمون متوالی شکست خورد و مسیر جایگزین سالم پیدا نشد؛ تلاش بعدی پس از ' + Math.round(nextDelay / 1000) + ' ثانیه.', 'bad');
          }
        } else {
          status('آزمون HTTPS اول ناموفق بود؛ برای جلوگیری از جابه‌جایی بی‌مورد، یک بار دیگر بررسی می‌شود.', 'bad');
        }
      }
    } catch (_) {
      status('خطا هنگام پایش؛ وضعیت اتصال جعل نشده و چرخهٔ بعد دوباره بررسی می‌کند.', 'bad');
    } finally {
      busy = false;
      if (running) timer = setTimeout(tick, nextDelay);
    }
  }
  function start() {
    if (running) return;
    const n = bridge();
    if (!n) {
      status('این قابلیت فقط در APK دارای Native Bridge واقعی کار می‌کند؛ حالت مرورگر یا Mock اتصال را شبیه‌سازی نمی‌کند.', 'bad');
      return;
    }
    const list = pool();
    if (!list.length) {
      status('حداقل یک کانفیگ VLESS معتبر و فعال وارد کن.', 'bad');
      return;
    }
    activeId = list.some(p => p.id === selected()) ? selected() : null;
    running = true; failures = 0; backoffMs = 30000;
    byId('stfStart').disabled = true;
    byId('stfStop').disabled = false;
    status('پایش Native شروع شد. اتصال فقط پس از دریافت پاسخ HTTPS واقعی سالم اعلام می‌شود.');
    void tick();
  }
  function stop() {
    running = false;
    if (timer !== null) clearTimeout(timer);
    timer = null;
    byId('stfStart').disabled = false;
    byId('stfStop').disabled = true;
    status('پایش متوقف شد؛ وضعیت VPN تغییر نکرده و تونل قطع نشده است.');
  }
  byId('stfStart').addEventListener('click', start);
  byId('stfStop').addEventListener('click', stop);
  byId('stfProbe').addEventListener('click', async () => {
    const n = bridge(), p = pool().find(x => x.id === (activeId || selected()));
    if (!n) { status('آزمون واقعی فقط در APK دارای Native Bridge کار می‌کند.', 'bad'); return; }
    if (!p) { status('ابتدا یک پروفایل VLESS را انتخاب کن.', 'bad'); return; }
    byId('stfProbe').disabled = true;
    try {
      const r = await probe(p, 5000);
      record(p, r.ok, r.ms, r.reason);
      status(r.ok ? 'آزمون HTTPS واقعی از داخل تونل موفق بود (' + r.ms + ' ms).' : 'آزمون HTTPS واقعی شکست خورد؛ اتصال سالم فرض نمی‌شود. ' + r.reason, r.ok ? 'ok' : 'bad');
    } finally { byId('stfProbe').disabled = false; }
  });
})();
</script>
"""

def patch_html(path: Path) -> None:
    s = path.read_text(encoding="utf-8")
    if "Smart Tunnel v0.24.3 native failover integration" not in s:
        style_end = s.rfind("</style>")
        if style_end < 0:
            raise SystemExit("Native failover integration: no </style> found")
        s = s[:style_end] + "\n" + CSS + "\n" + s[style_end:]
    if HTML_MARKER not in s:
        # Existing release workflow places this stable dashboard card before the route summary.
        marker = '<div class="card half"><div class="row"><strong>مسیر منتخب</strong>'
        if marker not in s:
            raise SystemExit("Native failover integration: dashboard insertion point not found")
        s = s.replace(marker, CARD + "\n" + marker, 1)
    if JS_MARKER not in s:
        body_end = s.lower().rfind("</body>")
        if body_end < 0:
            raise SystemExit("Native failover integration: no </body> found")
        s = s[:body_end] + "\n" + JS + "\n" + s[body_end:]
    path.write_text(s, encoding="utf-8")

def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: integrate_failover.py <android-project-root>")
    root = Path(sys.argv[1]).resolve()
    html = root / "app/src/main/assets/index.html"
    if not html.is_file():
        raise SystemExit(f"Android HTML asset not found: {html}")
    patch_html(html)
    print("Integrated failover UI wired to requestVpn/testThroughTunnel/validateConfig. No mock success path added.")

if __name__ == "__main__":
    main()
