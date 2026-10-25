"""Configuration OpenAI de John, indépendante de la passerelle V24. Windows uniquement."""
import json
import os
import subprocess
import urllib.request
import urllib.error
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

BASE = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'JohnSentinelle'
SECRET = BASE / 'openai_key.dpapi'


def powershell(script, data):
    p = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                       input=data, text=True, capture_output=True, timeout=20)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or 'Erreur de protection Windows')
    return p.stdout.strip()


def save_key(key):
    # DPAPI CurrentUser: clé déchiffrable uniquement sous le profil Windows actuel.
    script = ('Add-Type -AssemblyName System.Security; $s=[Console]::In.ReadToEnd().Trim(); '
              '$b=[Text.Encoding]::UTF8.GetBytes($s); '
              '$e=[Security.Cryptography.ProtectedData]::Protect($b,$null, '
              '[Security.Cryptography.DataProtectionScope]::CurrentUser); '
              '[Convert]::ToBase64String($e)')
    encrypted = powershell(script, key)
    BASE.mkdir(parents=True, exist_ok=True)
    SECRET.write_text(encrypted, encoding='ascii')


def load_key():
    if not SECRET.exists():
        return None
    script = ('Add-Type -AssemblyName System.Security; $s=[Console]::In.ReadToEnd().Trim(); '
              '$b=[Convert]::FromBase64String($s); '
              '$d=[Security.Cryptography.ProtectedData]::Unprotect($b,$null, '
              '[Security.Cryptography.DataProtectionScope]::CurrentUser); '
              '[Text.Encoding]::UTF8.GetString($d)')
    try:
        return powershell(script, SECRET.read_text(encoding='ascii'))
    except Exception:
        return None


def test_connection(key):
    from openai_planner import api_request, MODEL, PlannerError
    try:
        api_request(key, {'model': MODEL, 'store': False, 'input': 'Réponds seulement OK.', 'max_output_tokens': 20})
        return True, 'Réponse IA reçue : connexion validée.'
    except PlannerError as exc:
        return False, str(exc)


def main():
    root = tk.Tk()
    root.title('John Sentinelle | Première connexion ChatGPT')
    root.geometry('540x260')
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=20)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Configurer John avec l’API OpenAI', font=('Segoe UI', 14, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Une clé API OpenAI est nécessaire. ChatGPT Plus ne suffit pas.', wraplength=490).pack(anchor='w', pady=(10, 12))
    key = tk.StringVar()
    ttk.Entry(frame, textvariable=key, show='*', width=65).pack(anchor='w')
    status = tk.StringVar(value='La clé ne sera enregistrée qu’après un test réussi.')
    ttk.Label(frame, textvariable=status, wraplength=490).pack(anchor='w', pady=12)
    results = queue.Queue()
    def poll_result():
        try:
            ok, msg = results.get_nowait()
        except queue.Empty:
            root.after(100, poll_result)
            return
        button.configure(state='normal')
        status.set(msg)
        if ok:
            key.set('')
            messagebox.showinfo('John', msg)
    def test_and_save():
        value = key.get().strip()
        if not value:
            messagebox.showwarning('Clé manquante', 'Saisissez votre clé API OpenAI.')
            return
        status.set('Test de connexion en cours…')
        button.configure(state='disabled')
        def worker():
            ok, msg = test_connection(value)
            if ok:
                try:
                    save_key(value)
                    msg = 'Réponse IA reçue. Clé chiffrée pour ce compte Windows.'
                except Exception:
                    ok, msg = False, 'Réponse IA reçue, mais sauvegarde Windows impossible.'
            results.put((ok, msg))
        threading.Thread(target=worker, daemon=True).start()
        root.after(100, poll_result)
    button = ttk.Button(frame, text='Tester et enregistrer', command=test_and_save)
    button.pack(anchor='w')
    root.mainloop()

if __name__ == '__main__':
    main()
