'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const file = process.argv[2];
if (!file) throw new Error('Usage: node test_native_bridge_invocation.cjs <index.html>');
const html = fs.readFileSync(file, 'utf8');
const found = html.match(/function nativeCall\(name,arg=''\)\{[\s\S]*?return result\}/);
assert.ok(found, 'nativeCall() must exist in the packaged HTML');
const source = found[0];
assert.match(source, /arguments\.length<2\?api\[name\]\(\):api\[name\]\(arg\)/, 'zero-argument calls and explicit arguments must preserve both the Java interface receiver and argument count');
assert.doesNotMatch(source, /(?:const|let|var)\s+fn\s*=\s*api\[name\][\s\S]{0,220}?\bfn\s*\(/, 'a detached interface method must never be invoked');
const calls = [];
const native = {
  getStatus() { assert.equal(this, native); calls.push('getStatus'); return 'disconnected'; },
  subscriptionStatus() { assert.equal(this, native); calls.push('subscriptionStatus'); return '[]'; },
  subscriptionRefresh(id) { assert.equal(this, native); calls.push('subscriptionRefresh:' + id); return 'OK'; },
  stopVpn(reason) { assert.equal(this, native); assert.equal(reason, ''); calls.push('stopVpn:<empty>'); return 'OK'; }
};
const sandbox = { window: { SmartTunnelNative: native }, nativeAvailable: () => true };
vm.runInNewContext(source + "\nglobalThis.results=[nativeCall('getStatus'),nativeCall('subscriptionStatus'),nativeCall('subscriptionRefresh','sub-123'),nativeCall('stopVpn','')];", sandbox);
assert.deepEqual(Array.from(sandbox.results), ['disconnected', '[]', 'OK', 'OK']);
assert.deepEqual(calls, ['getStatus', 'subscriptionStatus', 'subscriptionRefresh:sub-123', 'stopVpn:<empty>']);
const browser = { window: {}, nativeAvailable: () => false };
vm.runInNewContext(source + "\nlet rejected=false;try{nativeCall('subscriptionStatus')}catch(e){rejected=/Native Bridge/.test(String(e.message))}globalThis.browserRejected=rejected;", browser);
assert.equal(browser.browserRejected, true, 'browser-only mode must fail closed when the Android bridge is absent');
console.log('PASS: Java bridge receiver preserved for no-arg and argument methods; browser-only mode fails closed.');
