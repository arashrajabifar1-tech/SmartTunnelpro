# Smart Tunnel Pro v0.24.7 — Canonical HTML + Android APK

Persian RTL Android WebView UI, Kotlin `VpnService` bridge, and sing-box `libbox` integration. The current GitHub Release is built from the packaged Android source with CI compatibility patches and the v0.24.7 dashboard integration. The published APK is **debug-signed**; it is not a Play Store production-signed build.

- **Latest APK:** [SmartTunnel-0.24.7-arm64.apk](https://github.com/arashrajabifar1-tech/SmartTunnelpro/releases/download/v0.24.7/SmartTunnel-0.24.7-arm64.apk)
- **Build and test run:** [GitHub Actions #17](https://github.com/arashrajabifar1-tech/SmartTunnelpro/actions/workflows/build-from-source-zip.yml)
- **Integrity:** the published APK's SHA-256 digest is recorded on the release asset and matches the successful build log.
- **Native Bridge receiver fix (v0.24.7):** `nativeCall()` now invokes methods directly on the injected Android WebView object instead of extracting a detached method; CI includes a Node.js regression test and verifies browser-only mode fails closed.
- **Native failover UI:** validates candidate configs with `validateConfig()`, requests the candidate via `requestVpn()`, and accepts health only after the existing Native async `testThroughTunnel()` reports HTTPS HTTP 204 from `www.gstatic.com/generate_204`. A physical-device connection test still requires a valid server profile.

The Android WebView entrypoint is now sourced from [SmartTunnelPro-v0.24.7.html](SmartTunnelPro-v0.24.7.html), and the build workflow copies it into `app/src/main/assets/index.html` before native bridge integration and regression tests. The APK is debug-signed, not Play Store production-signed. A valid user-owned server profile and a physical Android device are still required to verify live VPN connectivity.

## Added in v0.22.0

- Native per-profile HTTPS download benchmark, limited to 1–10 MiB per run and a bounded timeout.
- Per-profile speed history stored in Kbps, with Mbps display conversion and ranking from completed measurements.
- Cancel button for an active benchmark; tests stop the tunnel between profiles and leave it disconnected at the end.
- Conservative MTU profiles and selectable DoH presets. These are heuristics/presets, not a true path-MTU discovery test or an empirical fastest-DNS benchmark.
- Optional public config-source discovery. Candidates are untrusted, require manual selection, and are imported **disabled**. The app does not auto-connect to fetched profiles.
- Community-config cleanup only considers previously measured slow profiles marked as community/hunter imports; manual profiles and the selected profile are preserved.

## Additional hardening in v0.22.0

- ShadowTLS v1/v2/v3 URI parsing has explicit host/port/version checks; password is required only for v2/v3. A browser regression builds v1 and v3 sample outbounds. Native subscription normalization now recognizes `shadowtls://` and `type: shadowtls` entries.
- Smart failover waits for three consecutive failed live tunnel probes (or the existing pool health threshold), with cooldown to reduce route flapping. The Native probe only permits the fixed HTTPS `www.gstatic.com/generate_204` endpoint, requires a real connected service, and rejects test requests when this app is excluded from the VPN.
- Deep-link strings are base64-encoded as data before JavaScript evaluation. WebView denies file-origin cross-access, disables JS-created windows and turns Safe Browsing on where supported. JavaScript debugging is enabled only in debug builds.
- Exit-IP results are only shown while the VPN is connected and this app is not excluded. Refresh requests have timeouts, a response size cap, IP-literal validation and a 60-second cache expiry.
- The UI no longer downloads a font stylesheet from a third-party CDN on launch; it prefers an installed/local Vazirmatn font and falls back to Android system fonts when unavailable.
- GitHub Actions now runs the static validator and the Chromium UI regression suite before attempting the Android debug build.

## Benchmark safety and limits

- Real throughput tests require a built APK with `speedTestThroughTunnel` in the Native Bridge. Browser and Mock modes do not invent speed values.
- Starting the benchmark while a VPN is connected or connecting is blocked to avoid interrupting an existing session. Each test temporarily starts one profile; after the run the VPN remains disconnected. Reconnect manually afterwards.
- The Native request uses a fixed HTTPS endpoint (`speed.cloudflare.com`) instead of accepting arbitrary URLs from JavaScript, which limits misuse and keeps the test bounded.
- A result is recorded only when the entire requested payload downloads and the bridge still reports the VPN connected. Kbps is computed as `bytes × 8 ÷ elapsed milliseconds`; Mbps is Kbps ÷ 1000.
- Protocol type is a tie-breaker only. Hysteria2/TUIC are not guaranteed to be faster or harder to block on every carrier.
- Public proxy sources may be stale or malicious. A server operator can observe traffic metadata, and HTTPS-to-the-destination is not a substitute for trusting the proxy. Review each candidate before enabling it.
- WireGuard endpoint profiles are currently excluded from the per-profile throughput UI because the existing builder exposes WireGuard as an endpoint rather than a regular outbound/URLTest candidate.

## Build the APK

Requirements for a local build: JDK 17, Gradle 8.7, Android SDK Platform 35, Build Tools 35.0.0, and network access to download Gradle dependencies.

From this directory run:

```sh
gradle --no-daemon clean assembleDebug
```

Expected output:

`app/build/outputs/apk/debug/app-debug.apk`

The project does not bundle the Gradle Wrapper. On GitHub, put the *contents* of this project in a repository (private is fine), then run **Actions → Build Smart Tunnel APK**. On a successful run, download Artifact `SmartTunnel-0.22.0-debug-apk`; the workflow also publishes a clean source artifact named `SmartTunnel-0.22.0-source`. The source ZIP can be created locally with `python3 scripts/package_source.py`.

## Tests and release status

The static validator, Native Bridge receiver regression test, and Playwright Chromium smoke suite are included under `scripts/` and `tests/`. In this delivery they passed the available JavaScript syntax, XML, UI, config-generation, `.ir` route, DoH preset persistence, emergency-config and no-fake-VPN checks.

This environment has no installed Gradle or Android SDK, so the APK was not compiled here. No physical-device throughput, DNS/IPv6 leak, disconnect/kill-switch, battery, Starlink, or censorship-network test has been performed. A successful build is still required before device testing; these source changes do not imply an audited or untraceable VPN.

## License / dependency

The project includes the existing license notices. The `libbox` dependency is pinned in Gradle; observe its GPL-3.0 license obligations in any public distribution.
