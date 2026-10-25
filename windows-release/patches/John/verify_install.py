"""Validate dependencies and companion UI, without gateway startup."""
import hashlib, json, os, subprocess, sys, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parent
REPORT = Path(os.environ.get('LOCALAPPDATA', str(ROOT.parent))) / 'PCSentinelleSuite' / 'Logs' / 'installation-check.txt'

def verify():
    sys.path.insert(0, str(ROOT))
    from runtime_bootstrap import configure
    configure()
    manifest = json.loads((ROOT.parent / 'protected_manifest.json').read_text(encoding='utf-8-sig'))
    if not isinstance(manifest, list) or not manifest:
        raise RuntimeError('Le manifeste des composants protégés est vide ou invalide.')
    for row in manifest:
        path = (ROOT.parent / row['path']).resolve()
        if not path.is_relative_to(ROOT.parent.resolve()):
            raise RuntimeError('Chemin de manifeste invalide.')
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest().upper() != row['sha256'].upper():
            raise RuntimeError('Composant protégé non identique : ' + row['path'])
    for rel in ['PC/PC_Sentinelle_V32.exe', 'PC/PC_Sentinelle_V32.dll', 'PC/coreclr.dll',
                'John/runtime/python.exe', 'John/runtime/pythonw.exe', 'John/launch_john.py',
                'John/suite_john.py', 'John/pc_skills.py', 'John/file_mailbox.py',
                'John/photo/JohnPhoto.exe', 'John/pcphone/JohnPCPhone.exe']:
        if not (ROOT.parent / rel).is_file():
            raise RuntimeError('Composant absent : ' + rel)
    os.environ['TCL_LIBRARY'] = str(ROOT / 'runtime/tcl/tcl8.6')
    os.environ['TK_LIBRARY'] = str(ROOT / 'runtime/tcl/tk8.6')
    import tkinter, sqlite3, pc_skills, ssl, psutil, win32api, pythoncom, mcp, openai_planner, john_connexion
    if not tkinter.Tcl().eval('info patchlevel'):
        raise RuntimeError('Le moteur Tcl ne répond pas.')
    for query, tag in [('mon Internet rame', 'booster'), ('restaurer le nettoyage', 'restoreTemp'),
                       ('cache navigateur', 'browserCaches')]:
        if pc_skills.select(query) != tag:
            raise RuntimeError('Compétence non reconnue : ' + query)
    if '--gui' in sys.argv:
        code = 'import runpy,sys;sys.path.insert(0,sys.argv[1]);sys.argv=[sys.argv[1]+"/suite_john.py","--smoke"];runpy.run_path(sys.argv[0],run_name="__main__")'
        result = subprocess.run([str(ROOT / 'runtime/python.exe'), '-c', code, str(ROOT)],
                                cwd=ROOT, capture_output=True, timeout=45)
        output = (result.stdout + result.stderr).decode('utf-8', errors='replace')
        if result.returncode != 0 or 'SUITE_KNIGHT_SINGLE_BUBBLE_OK' not in output:
            raise RuntimeError('Échec du démarrage de John (code ' + str(result.returncode) + ') :\n' + output)
    return ('INSTALLATION_OK\n' + str(len(manifest)) + ' composants protégés identiques.\n'
            'Python embarqué, Tcl, Tk et dépendances importés.\n'
            'Contrôle hors ligne : aucune écoute réseau démarrée.\n'
            'Interface à tester séparément avec --gui.\n'
            'Ce contrôle ne valide pas toutes les actions PC ni la connexion distante.\n')

def main():
    try:
        message = verify()
        code = 0
    except Exception:
        message = 'INSTALLATION_ERROR\nPython : ' + sys.executable + '\n' + traceback.format_exc()
        code = 1
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(message, encoding='utf-8')
    print(message)
    return code

if __name__ == '__main__':
    raise SystemExit(main())
