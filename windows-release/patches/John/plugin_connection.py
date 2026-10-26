"""Companion-only lifecycle and setup; protected gateway files stay unchanged."""
import re
import threading
from john_v13.runtime import Runtime
from john_v13.client import request
from john_v13.storage import load_secrets, save_secrets


def save_connection(tunnel_id, key):
    tunnel_id = tunnel_id.strip()
    if not re.fullmatch(r'tunnel_[A-Za-z0-9_-]{8,128}', tunnel_id):
        raise ValueError('Identifiant du tunnel invalide.')
    values = load_secrets()
    if not key.strip() and not values.get('api_key'):
        raise ValueError('Collez la clé runtime du tunnel dans le champ masqué.')
    values['tunnel_id'] = tunnel_id
    if key.strip():
        values['api_key'] = key.strip()
    save_secrets(values)


class Connection:
    def __init__(self):
        self.owned = None
        self.last_error = ''
        self.connected = False
        self.state = 'Connexion au plugin : vérification…'
        self.stop = threading.Event()
        self.lock = threading.RLock()
        self.started = False

    def probe(self):
        with self.lock:
            if self.stop.is_set():
                return
            try:
                self.connected = bool(request().get('ok'))
            except Exception:
                self.connected = False
            try:
                if self.owned is None:
                    self.owned = Runtime()
                if self.connected:
                    # A responding local server does not imply a running tunnel.
                    self.owned.start_tunnel()
                else:
                    self.owned.start()
                    self.connected = bool(request().get('ok'))
                self.state = 'Passerelle : ' + self.owned.tunnel_status()
                self.last_error = ''
            except Exception as exc:
                # Do not display exception text: third-party errors can contain secrets.
                self.last_error = type(exc).__name__
                self.state = 'Connexion en erreur (' + self.last_error + '). Consultez le journal local.'

    def start(self):
        with self.lock:
            if self.started:
                return
            self.started = True
        self.probe()
        def monitor():
            while not self.stop.wait(10):
                self.probe()
        threading.Thread(target=monitor, daemon=True).start()

    def reconnect(self):
        with self.lock:
            if self.owned:
                self.owned.stop_tunnel()
        self.probe()

    def close(self):
        self.stop.set()
        with self.lock:
            if self.owned:
                # Runtime only closes children created by this instance.
                self.owned.close()
