from pathlib import Path
import sys

OLD = """function nativeCall(name,arg=''){if(!nativeAvailable())throw new Error('Native Bridge موجود نیست؛ این فایل را از داخل APK اجرا کن.');const fn=window.SmartTunnelNative[name];if(typeof fn!=='function')throw new Error('Bridge method missing: '+name);const result=fn(arg);if(typeof result==='string'&&result.startsWith('ERROR:'))throw new Error(result.slice(6));return result}"""
NEW = """function nativeCall(name,arg=''){const api=window.SmartTunnelNative;if(!api||typeof api.getStatus!=='function')throw new Error('Native Bridge موجود نیست؛ این فایل را از داخل APK اجرا کن.');if(typeof api[name]!=='function')throw new Error('Bridge method missing: '+name);let result;try{result=arguments.length<2?api[name]():api[name](arg)}catch(e){const message=String(e&&e.message||e);if(message.includes('Java bridge method can\\'t be invoked on a non-injected object'))throw new Error('پل اندروید معتبر نیست یا صفحه دوباره بارگذاری شده است؛ برنامه را از داخل APK دوباره باز کن.');throw e}if(typeof result==='string'&&result.startsWith('ERROR:'))throw new Error(result.slice(6));return result}"""

def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: fix_native_bridge_calls.py <android-project-root-or-html-file>')
    target = Path(sys.argv[1]).resolve()
    if target.is_dir():
        target = target / 'app' / 'src' / 'main' / 'assets' / 'index.html'
    if not target.is_file():
        raise SystemExit(f'HTML asset not found: {target}')
    source = target.read_text(encoding='utf-8')
    if NEW in source:
        print('PASS: nativeCall already preserves the injected object receiver.')
        return
    if source.count(OLD) != 1:
        raise SystemExit(f'Expected exactly one known nativeCall implementation, found {source.count(OLD)}; refusing blind rewrite.')
    source = source.replace(OLD, NEW, 1)
    if 'const result=fn(arg)' in source:
        raise SystemExit('Detached bridge invocation remains after patch.')
    target.write_text(source, encoding='utf-8')
    print('PASS: nativeCall invokes the method on the original injected object.')

if __name__ == '__main__':
    main()
