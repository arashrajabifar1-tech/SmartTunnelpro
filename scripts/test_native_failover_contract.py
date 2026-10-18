#!/usr/bin/env python3
"""Pre-build native/JavaScript contract checks for the actual extracted Android source."""
from pathlib import Path
import re
import sys

REQUIRED_BRIDGE_METHODS = ("getStatus", "requestVpn", "testThroughTunnel", "validateConfig")

def fail(message: str) -> None:
    raise SystemExit("FAIL: " + message)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_native_failover_contract.py <android-project-root>")
    root = Path(sys.argv[1]).resolve()
    bridge_files = list(root.rglob("*.kt")) + list(root.rglob("*.java"))
    bridge = next((p for p in bridge_files if p.name == "SmartTunnelBridge.kt"), None)
    if bridge is None:
        fail("SmartTunnelBridge.kt not found in extracted source")
    src = bridge.read_text(encoding="utf-8", errors="replace")

    for method in REQUIRED_BRIDGE_METHODS:
        pattern = re.compile(r"@JavascriptInterface[\s\S]{0,300}?\bfun\s+" + re.escape(method) + r"\s*\(", re.M)
        if not pattern.search(src):
            fail(f"Native method {method} is missing or not exposed with @JavascriptInterface")
    if "https://www.gstatic.com/generate_204" not in src and "www.gstatic.com/generate_204" not in src:
        fail("Native HTTPS health-check target is not the fixed gstatic 204 endpoint")
    if not re.search(r"getStatus\(\)\s*==\s*\"connected\"", src):
        fail("Native HTTP probe does not require an actually connected VPN state")
    if not re.search(r"responseCode\s*==\s*204", src):
        fail("Native HTTP probe does not require HTTP 204")
    if "HttpURLConnection" not in src and "HttpsURLConnection" not in src:
        fail("Native HTTP probe implementation not found")

    manifest_files = list((root / "app/src/main").rglob("AndroidManifest.xml"))
    if not manifest_files:
        fail("AndroidManifest.xml not found")
    manifest = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in manifest_files)
    if "android.permission.INTERNET" not in manifest:
        fail("INTERNET permission missing")
    if "android.net.VpnService" not in manifest or "android.permission.BIND_VPN_SERVICE" not in manifest:
        fail("VpnService or BIND_VPN_SERVICE declaration missing")

    html = root / "app/src/main/assets/index.html"
    if not html.is_file():
        fail("HTML asset missing")
    h = html.read_text(encoding="utf-8", errors="replace")
    marker = "/* Smart Tunnel v0.24.3 native failover integration: JS */"
    if marker not in h:
        fail("Native failover JS integration marker missing")
    start = h.index(marker)
    end = h.find("</script>", start)
    if end < 0:
        fail("Native failover script is not closed")
    block = h[start:end]
    for token in ("n.requestVpn(json)", "n.testThroughTunnel(", "n.validateConfig(json)", "window.__ST_MOCK__", "https://www.gstatic.com/generate_204"):
        if token not in block:
            fail("Failover integration lacks required contract: " + token)
    if "n.startVpn(" in block or "n.probeThroughTunnel(" in block:
        fail("Failover calls methods not implemented by this Android Native Bridge")
    if "Smart Tunnel v0.24.3 native failover integration" not in h:
        fail("Failover UI/style marker missing")
    if h.count('id="stNativeFailoverCard"') != 1:
        fail("Expected exactly one native failover UI")
    if "Math.random()" not in block:
        fail("Native test request IDs should be unique per request")

    print("PASS: Native Bridge annotations, real HTTPS 204 probe, connected-state guard, VPN manifest, fail-closed Mock guard, and JS/native method contract.")
    print("NOTE: This is a pre-build source contract test. It does not replace a live tunnel test using a valid server profile on a physical device.")

if __name__ == "__main__":
    main()
