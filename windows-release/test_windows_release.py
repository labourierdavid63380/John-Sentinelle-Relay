import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import winreg

HERE = Path(__file__).resolve().parent
PAYLOAD = HERE/'SuitePayload'
RESULTS = {}

def run(args, timeout=120, **kwargs):
    result = subprocess.run([str(x) for x in args], capture_output=True, timeout=timeout, **kwargs)
    output = (result.stdout+result.stderr).decode('utf-8', errors='replace')
    print(output, flush=True)
    if result.returncode:
        raise RuntimeError('Command failed (%d): %s\n%s' % (result.returncode, args[0], output))
    return output

def check_files(root):
    rows = json.loads((root/'protected_manifest.json').read_text(encoding='utf-8-sig'))
    for row in rows:
        assert hashlib.sha256((root/row['path']).read_bytes()).hexdigest().lower() == row['sha256'].lower(), row['path']
    for name, digest in json.loads((HERE/'pc_baseline_hashes.json').read_text()).items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest() == digest, name
    return len(rows)

def python_at(root):
    return root/'John/runtime/python.exe'

def check_ui_and_key(root):
    py = python_at(root)
    run([py, '-I', root/'John/verify_install.py', '--gui'])
    with tempfile.TemporaryDirectory(prefix='JohnDPAPI-') as folder:
        env = dict(os.environ, LOCALAPPDATA=folder)
        run([py, '-c', "import john_connexion as c;c.save_key('test-not-a-real-key');assert c.load_key()=='test-not-a-real-key';print('DPAPI_ROUNDTRIP_OK')"], cwd=root/'John', env=env)
    code = """import suite_john as s
b=s.Bubble.__new__(s.Bubble)
b.ai_history=[]
b.messages=__import__("queue").Queue()
assert 'Bonjour' in b.handle_request('bonjour John')
s.load_key=lambda:'test-not-a-real-key'
def fail(*a,**k): raise s.PlannerError('Quota OpenAI atteint')
s.ask=fail
assert 'Quota' in b.handle_request('Comment vas-tu ?')['message']
print('GREETING_AND_READABLE_API_ERROR_OK')
"""
    run([py, '-c', code], cwd=root/'John')

def registry_version():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Uninstall\PCSentinelleSuite3402') as key:
        return winreg.QueryValueEx(key, 'DisplayVersion')[0]

def main():
    if os.name != 'nt' or os.environ.get('CI','').lower() != 'true':
        raise SystemExit('Disposable Windows CI runner required.')
    run([sys.executable, HERE/'test_planner.py'])
    RESULTS['planner_unit_tests'] = 8
    RESULTS['protected_components'] = check_files(PAYLOAD)
    check_ui_and_key(PAYLOAD)
    RESULTS['bundled_runtime_ui_and_dpapi'] = True
    # Include bytecode created during runtime tests in the known-file uninstaller.
    files = [p.relative_to(PAYLOAD) for p in PAYLOAD.rglob('*') if p.is_file()]
    dirs = sorted({p.parent for p in files if str(p.parent) != '.'}, key=lambda p:len(p.parts), reverse=True)
    lines = [f'Delete "$INSTDIR\\{p}"' for p in files]
    lines += [f'RMDir "$INSTDIR\\{p}"' for p in dirs]
    (HERE/'uninstall_files.nsh').write_text('\n'.join(lines)+'\n', encoding='utf-8-sig')
    compiler = os.environ['NSIS_COMPILER']
    run([compiler, '/V3', HERE/'Installer.nsi'], cwd=HERE, timeout=600)
    exe = HERE/'Delivery34_0_3/PC_Sentinelle_John_Setup_34_0_3.exe'
    assert exe.is_file()
    target = Path('C:/SentinelleReleaseTest')
    run([exe, '/S', '/D='+str(target)], timeout=240)
    assert registry_version() == '34.0.3'
    check_files(target)
    check_ui_and_key(target)
    RESULTS['fresh_install'] = True
    ps = str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe')
    # Check actual .lnk targets on the runner's redirected Desktop.
    output = run([ps, '-NoProfile', '-Command', "$s=New-Object -ComObject WScript.Shell;$d=[Environment]::GetFolderPath('Desktop');foreach($n in @('PC Sentinelle.lnk','John Sentinelle.lnk')){$p=Join-Path $d $n;if(!(Test-Path $p)){throw 'Shortcut missing'};$l=$s.CreateShortcut($p);if(!(Test-Path $l.TargetPath)){throw 'Target missing'};Write-Output $l.TargetPath}"])
    RESULTS['desktop_shortcuts'] = True
    # Unrelated use of bundled Python must prevent overwriting, without termination.
    unrelated = subprocess.Popen([str(python_at(target)), '-c', 'import time;time.sleep(120)'])
    try:
        time.sleep(1)
        before = hashlib.sha256((target/'John/suite_john.py').read_bytes()).hexdigest()
        attempt = subprocess.run([str(exe), '/S', '/D='+str(target)], timeout=120)
        assert attempt.returncode == 2, attempt.returncode
        assert unrelated.poll() is None
        assert hashlib.sha256((target/'John/suite_john.py').read_bytes()).hexdigest() == before
    finally:
        unrelated.terminate(); unrelated.wait(timeout=10)
    RESULTS['unknown_python_process_guard'] = True
    # A known independent receiver holds Python DLLs and is safely stopped for update.
    receiver = subprocess.Popen([str(python_at(target)), str(target/'John/file_mailbox.py')], cwd=target/'John')
    try:
        time.sleep(3)
        assert receiver.poll() is None, 'Receiver did not start'
        run([exe, '/S', '/D='+str(target)], timeout=240)
        receiver.wait(timeout=10)
        check_files(target)
        check_ui_and_key(target)
    finally:
        if receiver.poll() is None:
            receiver.terminate();receiver.wait(timeout=10)
    RESULTS['upgrade_with_receiver_running'] = True
    # Launch the unchanged native PC executable and observe its window.
    pc = subprocess.Popen([str(target/'PC/PC_Sentinelle_V32.exe')], cwd=target/'PC')
    try:
        time.sleep(6)
        assert pc.poll() is None, 'PC exited at startup'
        run([ps, '-NoProfile', '-Command', "$p=Get-Process -Id "+str(pc.pid)+";if($p.MainWindowHandle -eq 0){throw 'No PC window'};Write-Output 'PC_WINDOW_OK';[void]$p.CloseMainWindow()"])
    finally:
        try:pc.wait(timeout=10)
        except subprocess.TimeoutExpired:pc.terminate();pc.wait(timeout=10)
    RESULTS['native_pc_window'] = True
    # Uninstall must leave user data outside the application directory untouched.
    keep = Path(os.environ['LOCALAPPDATA'])/'JohnSentinelle/preserve-test.txt'
    keep.parent.mkdir(parents=True, exist_ok=True);keep.write_text('preserve-user-data')
    run([target/'Desinstaller.exe', '/S'], timeout=90)
    for _ in range(50):
        if not (target/'PC/PC_Sentinelle_V32.exe').exists():break
        time.sleep(.2)
    assert not (target/'PC/PC_Sentinelle_V32.exe').exists(), 'Uninstall did not remove program'
    assert keep.read_text() == 'preserve-user-data'
    RESULTS['uninstall_preserves_personal_data'] = True
    RESULTS['api_live_generation'] = 'not validated: previous request returned HTTP 429 quota/rate limit'
    RESULTS['personal_api_key_included'] = False
    RESULTS['suite_version'] = '34.0.3'
    RESULTS['john_companion_version'] = '33.0.5'
    (exe.parent/'VALIDATION.json').write_text(json.dumps(RESULTS, indent=2), encoding='utf-8')
    print(json.dumps(RESULTS, indent=2))

if __name__ == '__main__':
    main()
