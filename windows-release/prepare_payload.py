import hashlib
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
source = Path(sys.argv[1]).resolve()
candidates = [p.parent for p in source.rglob('protected_manifest.json') if (p.parent/'PC').is_dir() and (p.parent/'John').is_dir()]
if len(candidates) != 1:
    raise SystemExit('Ambiguous or missing payload root: '+str(candidates))
baseline = candidates[0]
payload = HERE/'SuitePayload'
patches = HERE/'patches'
expected = json.loads((patches/'protected_manifest.json').read_text())
actual = json.loads((baseline/'protected_manifest.json').read_text(encoding='utf-8-sig'))
if expected != actual:
    raise SystemExit('Protected manifest changed from V33.0.2 reference')
shutil.copytree(baseline, payload, dirs_exist_ok=True)
for file in patches.rglob('*'):
    if file.is_file():
        target = payload/file.relative_to(patches)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
(payload/'Desinstaller.exe').unlink(missing_ok=True)
for row in expected:
    if hashlib.sha256((payload/row['path']).read_bytes()).hexdigest().lower() != row['sha256'].lower():
        raise SystemExit('Protected file differs: '+row['path'])
pc = {}
for file in (baseline/'PC').rglob('*'):
    if file.is_file():
        name = file.relative_to(baseline).as_posix()
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        if digest != hashlib.sha256((payload/name).read_bytes()).hexdigest():
            raise SystemExit('PC file changed: '+name)
        pc[name] = digest
(HERE/'pc_baseline_hashes.json').write_text(json.dumps(pc, indent=2))
files = [p.relative_to(payload) for p in payload.rglob('*') if p.is_file()]
dirs = sorted({p.parent for p in files if str(p.parent) != '.'}, key=lambda p:len(p.parts), reverse=True)
delete = ['Delete "$INSTDIR\\'+str(p).replace('/', '\\')+'"' for p in files]
remove = ['RMDir "$INSTDIR\\'+str(p).replace('/', '\\')+'"' for p in dirs]
(HERE/'uninstall_files.nsh').write_text('\n'.join(delete+remove)+'\n', encoding='utf-8-sig')
(HERE/'Delivery34_0_4').mkdir(exist_ok=True)
print('PAYLOAD_OK:', len(expected), 'protected files;', len(pc), 'PC files preserved')
