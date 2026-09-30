"""John relay: HTTPS only, capability-based pairing; no PC command execution here.
Python 3.11+, standard library. Run with a trusted TLS certificate on a dedicated host.
"""
import argparse, hashlib, hmac, json, os, secrets, sqlite3, ssl, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit

def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def token(): return secrets.token_urlsafe(32)
class Denied(Exception): pass
class Store:
    def __init__(self, path, enroll_key, clock=time.time):
        self.db=sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory=sqlite3.Row
        self.lock=threading.RLock(); self.clock=clock; self.enroll_key=enroll_key
        self.db.executescript('''PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS pcs(id TEXT PRIMARY KEY, secret TEXT UNIQUE NOT NULL, seen INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS pairs(id TEXT PRIMARY KEY, pc TEXT NOT NULL REFERENCES pcs(id), ticket TEXT UNIQUE NOT NULL, expires INTEGER NOT NULL, state TEXT NOT NULL, phone TEXT, code TEXT);
CREATE INDEX IF NOT EXISTS pairs_pc ON pairs(pc,state);
CREATE TABLE IF NOT EXISTS phones(id TEXT PRIMARY KEY, pc TEXT NOT NULL REFERENCES pcs(id), secret TEXT UNIQUE NOT NULL, expires INTEGER NOT NULL, state TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS phones_pc ON phones(pc,state);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, pc TEXT NOT NULL REFERENCES pcs(id), phone TEXT NOT NULL REFERENCES phones(id), command TEXT NOT NULL, state TEXT NOT NULL, expires INTEGER NOT NULL, result TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS jobs_pc ON jobs(pc,state);
CREATE INDEX IF NOT EXISTS jobs_phone ON jobs(phone);
''')
        self.db.commit()
    def close(self): self.db.close()
    def one(self,sql,args=()): return self.db.execute(sql,args).fetchone()
    def run(self,path,body,pc_secret='',phone_secret=''):
        with self.lock, self.db:
            now=int(self.clock())
            self.db.execute("UPDATE jobs SET state='expired',result='Demande expirée ; exécution non confirmée.' WHERE expires<=? AND state IN ('queued','running')",(now,))
            self.db.execute("DELETE FROM jobs WHERE expires<?",(now-86400,))
            self.db.execute("DELETE FROM pairs WHERE expires<?",(now-600,))
            if path=='/api/pc/register':
                key=body.get('key','')
                if not isinstance(key,str) or not hmac.compare_digest(key,self.enroll_key): raise Denied('Inscription refusée.')
                if self.one('SELECT COUNT(*) n FROM pcs')['n']>=1000: raise Denied('Capacité du relais atteinte.')
                pid=token(); secret=token()
                self.db.execute('INSERT INTO pcs VALUES(?,?,?)',(pid,digest(secret),now))
                return {'token':secret,'pc':pid}
            pc=self.one('SELECT * FROM pcs WHERE secret=?',(digest(pc_secret),)) if pc_secret else None
            if path.startswith('/api/pc/'):
                if not pc: raise Denied('PC non authentifié.')
                pid=pc['id']; self.db.execute('UPDATE pcs SET seen=? WHERE id=?',(now,pid))
                if path=='/api/pc/pair':
                    # A new QR invalidates every older unfinished QR for this PC.
                    self.db.execute("UPDATE phones SET state='revoked' WHERE id IN (SELECT phone FROM pairs WHERE pc=? AND state='claimed')",(pid,))
                    self.db.execute("UPDATE pairs SET state='cancelled' WHERE pc=? AND state IN ('open','claimed')",(pid,))
                    ticket=token();pair=token()
                    self.db.execute('INSERT INTO pairs VALUES(?,?,?,?,?,?,?)',(pair,pid,digest(ticket),now+120,'open',None,None))
                    return {'ticket':ticket,'expires_in':120,'pair':pair}
                if path=='/api/pc/poll':
                    p=self.one("SELECT * FROM pairs WHERE pc=? AND state='claimed' AND expires>? LIMIT 1",(pid,now))
                    if p:return {'kind':'pair','pair':p['id'],'code':p['code']}
                    j=self.one("SELECT jobs.* FROM jobs JOIN phones ON phones.id=jobs.phone WHERE jobs.pc=? AND jobs.state='queued' AND phones.state='active' AND phones.expires>? AND jobs.expires>? ORDER BY jobs.rowid LIMIT 1",(pid,now,now))
                    if j:
                        self.db.execute("UPDATE jobs SET state='running' WHERE id=? AND state='queued'",(j['id'],))
                        return {'kind':'job','id':j['id'],'command':j['command']}
                    return {'kind':'idle'}
                if path=='/api/pc/confirm':
                    p=self.one("SELECT * FROM pairs WHERE id=? AND pc=? AND state='claimed' AND expires>?",(body.get('pair'),pid,now))
                    if not p:raise Denied('Association expirée ou déjà traitée.')
                    yes=body.get('accept') is True
                    self.db.execute('UPDATE pairs SET state=? WHERE id=?',('approved' if yes else 'rejected',p['id']))
                    self.db.execute('UPDATE phones SET state=? WHERE id=?',('active' if yes else 'revoked',p['phone']))
                    return {'ok':True,'accepted':yes}
                if path=='/api/pc/cancel':
                    self.db.execute("UPDATE phones SET state='revoked' WHERE id IN (SELECT phone FROM pairs WHERE pc=? AND state='claimed')",(pid,))
                    self.db.execute("UPDATE pairs SET state='cancelled' WHERE pc=? AND state IN ('open','claimed')",(pid,))
                    return {'ok':True}
                if path=='/api/pc/revoke':
                    self.db.execute("UPDATE phones SET state='revoked' WHERE pc=?",(pid,))
                    self.db.execute("UPDATE pairs SET state='cancelled' WHERE pc=?",(pid,))
                    self.db.execute("UPDATE jobs SET state='cancelled',result='Téléphone révoqué ; résultat non confirmé.' WHERE pc=? AND state IN ('queued','running')",(pid,))
                    return {'ok':True}
                if path=='/api/pc/result':
                    result=body.get('result','')
                    if not isinstance(result,str) or len(result)>4000:raise Denied('Résultat invalide.')
                    j=self.one("SELECT jobs.id FROM jobs JOIN phones ON phones.id=jobs.phone WHERE jobs.id=? AND jobs.pc=? AND jobs.state='running' AND jobs.expires>? AND phones.state='active' AND phones.expires>?",(body.get('id'),pid,now,now))
                    if not j:raise Denied('Mission expirée, révoquée ou déjà terminée.')
                    self.db.execute("UPDATE jobs SET state='completed',result=? WHERE id=?",(result,j['id']))
                    return {'ok':True}
                raise Denied('Route inconnue.')
            if path=='/api/phone/claim':
                ticket=body.get('ticket','')
                if not isinstance(ticket,str) or len(ticket)>100:raise Denied('QR invalide.')
                p=self.one("SELECT * FROM pairs WHERE ticket=? AND state='open' AND expires>?",(digest(ticket),now))
                if not p:raise Denied('QR expiré ou déjà utilisé. Demandez un nouveau QR à John.')
                phone=token(); secret=token(); code=f'{secrets.randbelow(1000000):06d}'
                self.db.execute('INSERT INTO phones VALUES(?,?,?,?,?)',(phone,p['pc'],digest(secret),now+30*86400,'pending'))
                self.db.execute("UPDATE pairs SET state='claimed',phone=?,code=? WHERE id=?",(phone,code,p['id']))
                return {'cookie':secret,'code':code,'pc':p['pc'][-8:]}
            ph=self.one('SELECT * FROM phones WHERE secret=? AND expires>?',(digest(phone_secret),now)) if phone_secret else None
            if not ph or ph['state']=='revoked':raise Denied('Téléphone non associé ou révoqué.')
            if ph['state']=='pending':
                p=self.one("SELECT * FROM pairs WHERE phone=? AND state='claimed' AND expires>?",(ph['id'],now))
                if not p:raise Denied('Association expirée ou annulée.')
                if path=='/api/phone/status':return {'state':'pending','code':p['code'],'pc':ph['pc'][-8:]}
                raise Denied('Confirmation du PC nécessaire.')
            if path=='/api/phone/status':
                pc=self.one('SELECT seen FROM pcs WHERE id=?',(ph['pc'],))
                jobs=[dict(j) for j in self.db.execute('SELECT id,command,state,result FROM jobs WHERE phone=? ORDER BY rowid DESC LIMIT 10',(ph['id'],))]
                return {'state':'active','pc':ph['pc'][-8:],'online':now-pc['seen']<15,'jobs':jobs}
            if path=='/api/phone/send':
                cmd=body.get('command','')
                if not isinstance(cmd,str): raise Denied('Commande invalide.')
                cmd=cmd.strip()
                if not cmd or len(cmd)>500: raise Denied('Commande vide ou trop longue (500 caractères maximum).')
                pc=self.one('SELECT seen FROM pcs WHERE id=?',(ph['pc'],))
                if now-pc['seen']>=15:raise Denied('PC hors ligne ou John en pause. Réessayez lorsqu’il est connecté.')
                if self.one("SELECT COUNT(*) n FROM jobs WHERE phone=? AND state IN ('queued','running')",(ph['id'],))['n']>=3:raise Denied('Attendez le résultat des demandes en cours.')
                jid=token(); self.db.execute('INSERT INTO jobs(id,pc,phone,command,state,expires) VALUES(?,?,?,?,?,?)',(jid,ph['pc'],ph['id'],cmd,'queued',now+60))
                return {'id':jid,'state':'queued'}
            raise Denied('Route inconnue.')

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.0'
    def setup(self):
        super().setup(); self.connection.settimeout(10)
    def log_message(self,*args): pass # Never log pairing tickets, credentials or user content.
    def reply(self,status,data,ctype='application/json; charset=utf-8',cookie=None):
        payload=json.dumps(data,ensure_ascii=False).encode() if ctype.startswith('application/json') else data
        self.send_response(status)
        for k,v in {'Content-Type':ctype,'Content-Length':str(len(payload)),'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff','Strict-Transport-Security':'max-age=31536000','Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"}.items():self.send_header(k,v)
        if cookie:self.send_header('Set-Cookie',f'john_phone={cookie}; Path=/api/phone; Secure; HttpOnly; SameSite=Strict; Max-Age=2592000')
        self.end_headers();self.wfile.write(payload)
    def do_GET(self):
        path=urlsplit(self.path).path
        names={'/':'phone.html','/phone.js':'phone.js','/phone.css':'phone.css'}
        if path not in names:return self.reply(404,{'error':'Introuvable.'})
        data=(Path(__file__).parent/names[path]).read_bytes()
        ctype={'/':'text/html; charset=utf-8','/phone.js':'text/javascript; charset=utf-8','/phone.css':'text/css; charset=utf-8'}[path]
        self.reply(200,data,ctype)
    def do_POST(self):
        try:
            if not self.server.allow(self.client_address[0]):return self.reply(429,{'error':'Trop de demandes. Réessayez dans une minute.'})
            path=urlsplit(self.path).path
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.reply(415,{'error':'JSON requis.'})
            size=int(self.headers.get('Content-Length','0'))
            if size<2 or size>8192:return self.reply(413,{'error':'Taille invalide.'})
            if path.startswith('/api/phone/') and self.headers.get('Origin')!=self.server.origin:return self.reply(403,{'error':'Origine refusée.'})
            body=json.loads(self.rfile.read(size))
            if not isinstance(body,dict):raise ValueError()
            auth=self.headers.get('Authorization','')
            if len(auth)>200:raise ValueError()
            cookies=SimpleCookie(); cookies.load(self.headers.get('Cookie','')[:4096])
            phone=cookies['john_phone'].value if 'john_phone' in cookies else ''
            result=self.server.store.run(path,body,auth[7:] if auth.startswith('Bearer ') else '',phone)
            cookie=result.pop('cookie',None)
            self.reply(200,result,cookie=cookie)
        except Denied as e:self.reply(403,{'error':str(e)})
        except (ValueError,TypeError,json.JSONDecodeError):self.reply(400,{'error':'Requête invalide.'})
        except Exception:self.reply(503,{'error':'Service temporairement indisponible.'})

class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,store,origin):
        super().__init__(address,Handler);self.store=store;self.origin=origin;self.rates={};self.rate_lock=threading.Lock();self.slots=threading.BoundedSemaphore(32);self.tls_context=None
    def process_request(self,request,client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request);return
        try:super().process_request(request,client_address)
        except Exception:self.slots.release();raise
    def process_request_thread(self,request,client_address):
        try:
            request.settimeout(10)
            if self.tls_context:request=self.tls_context.wrap_socket(request,server_side=True)
            super().process_request_thread(request,client_address)
        except (OSError,ssl.SSLError):self.shutdown_request(request)
        finally:self.slots.release()
    def allow(self,ip):
        with self.rate_lock:
            minute=int(time.time()//60)
            self.rates={k:v for k,v in self.rates.items() if v[0]==minute}
            if len(self.rates)>10000:return False
            n=self.rates.get(ip,(minute,0))[1]+1;self.rates[ip]=(minute,n)
            return n<=120

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--cert')
    p.add_argument('--key')
    p.add_argument('--origin',default=os.environ.get('JOHN_ORIGIN') or os.environ.get('RENDER_EXTERNAL_URL'))
    p.add_argument('--port',type=int,default=int(os.environ.get('PORT','8443')))
    p.add_argument('--db',default=os.environ.get('JOHN_DB','john.sqlite3'))
    a=p.parse_args()
    if not a.origin:
        p.error('Set JOHN_ORIGIN (or run on Render, which provides RENDER_EXTERNAL_URL).')
    a.origin=a.origin.rstrip('/')
    u=urlsplit(a.origin)
    if u.scheme!='https' or not u.netloc or u.path or u.query or u.fragment or u.username:
        p.error('Origin must be an HTTPS origin without a trailing slash.')
    secret=os.environ.get('JOHN_ENROLL_KEY','')
    if len(secret)<32:
        p.error('Set JOHN_ENROLL_KEY to at least 32 random characters; never reuse a password.')
    os.umask(0o077)
    store=Store(a.db,secret);server=Server(('0.0.0.0',a.port),store,a.origin)
    # Render terminates public TLS and forwards requests to this private HTTP port.
    # For direct/self-hosted use, --cert and --key still enable local TLS.
    if a.cert or a.key:
        if not (a.cert and a.key): p.error('Use --cert and --key together.')
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.minimum_version=ssl.TLSVersion.TLSv1_2;ctx.load_cert_chain(a.cert,a.key)
        server.tls_context=ctx
    print(f'John relay started on 0.0.0.0:{a.port} for {a.origin}.')
    try:server.serve_forever()
    finally:server.server_close();store.close()
if __name__=='__main__': main()
