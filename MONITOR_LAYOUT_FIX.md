# Smart Tunnel Pro — monitoring layout fix

Target: the standalone HTML development build whose Tools page contains the section heading `پایش و جابه‌جایی خودکار`, the `#failoverCard` card, and the `#failoverStartButton` / `#failoverStopButton` controls.

## Minimal HTML marker edits

1. Find:
   `<div class="section-head"><div><h2>پایش و جابه‌جایی خودکار</h2>`

   Replace that opening with:
   `<div class="section-head st-monitor-head"><div class="st-monitor-heading"><h2>پایش و جابه‌جایی خودکار</h2>`

   Keep the existing paragraph, closing `</div>`, and FAILOVER pill as they are.

2. Find:
   `<div class="card" id="failoverCard">`

   Replace with:
   `<div class="card st-monitor-card" id="failoverCard" dir="rtl">`

3. Find the toolbar immediately inside this card:
   `<div class="toolbar" style="margin-top:13px"><button class="btn primary" id="failoverStartButton"`

   Replace only `class="toolbar"` with `class="toolbar st-monitor-actions"`.

4. Insert the CSS from [monitor-layout-fix.css](./monitor-layout-fix.css) immediately before the existing closing `</style>`. Do not replace the whole stylesheet or change the dark-theme variables.

## What this patch addresses

- Explicitly keeps the monitoring card full-width in its page container.
- Lets the heading and long status/help text shrink and wrap safely rather than forming a narrow column.
- Keeps the start/stop controls in a flex row with wrapping as a fallback on very narrow screens.
- Preserves the existing theme colors and VPN logic; it is a presentation-only patch.

## Verification performed

Chromium responsive checks were run at 320, 360, 390, 430, 768, and 1440 CSS pixels. At all six sizes the card matched the Tools page's content width, the main paragraph used `word-break: break-word`, the two buttons shared a row without overlap, there was no horizontal page overflow, and no browser JavaScript errors were observed. In standalone/browser mode the monitor still reports the Native Bridge requirement rather than faking a successful VPN connection.

These browser checks validate layout and client-side rendering; they are not a physical-device VPN connectivity test.
