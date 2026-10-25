"""Suite companion UI. Protected V24 and V1 files are imported/launched unchanged."""
import os,sys,site,subprocess,threading,json,queue
from pathlib import Path
ROOT=Path(__file__).resolve().parent
from runtime_bootstrap import configure
configure()
os.environ['TCL_LIBRARY']=str(ROOT/'runtime/tcl/tcl8.6')
os.environ['TK_LIBRARY']=str(ROOT/'runtime/tcl/tk8.6')
site.addsitedir(str(ROOT/'v24_dependencies'))
site.addsitedir(str(ROOT/'dependencies'))
sys.path.insert(0,str(ROOT/'reference_v24'))
import tkinter as tk
from tkinter import ttk,scrolledtext
from john_v13 import gui
from john_v13.client import request
from pc_skills import select,run,follow,choose,CATALOG
from openai_planner import ask, needs_planner, PlannerError
from john_connexion import load_key
OriginalRuntime=gui.Runtime
class CompanionRuntime:
 def __init__(self):self.owned=None;self.last_error='';self.connected=False
 def start(self):
  try:
   if request().get('ok'):
    self.connected=True;return
  except Exception:pass
  self.owned=OriginalRuntime()
  self.owned.start();self.last_error=self.owned.last_error
  try:self.connected=bool(request().get('ok'))
  except Exception:pass
 def close(self):
  if self.owned:self.owned.close()
class Bubble(gui.App):
 def __init__(self,root):
  self.last_pc_result=None;self.history=[];self.ai_history=[];super().__init__(root);root.title('John — PC Sentinelle V33.0.5')
  self.canvas.pack_forget();self.canvas.place(relx=1,rely=1,anchor='se',width=200,height=230)
  self.canvas.unbind('<Button-1>');self.canvas.bind('<ButtonPress-1>',self.press)
  self.canvas.bind('<ButtonRelease-1>',self.release)
 def press(self,e):self.pressed=(e.x_root,e.y_root);self.drag_start(e)
 def release(self,e):
  if abs(e.x_root-self.pressed[0])+abs(e.y_root-self.pressed[1])<6:self.toggle_panel()
 def reshape(self,w,h):
  self.root.update_idletasks();right=self.root.winfo_x()+self.root.winfo_width();bottom=self.root.winfo_y()+self.root.winfo_height()
  self.root.geometry(f'{w}x{h}+{max(0,min(right-w,self.root.winfo_screenwidth()-w))}+{max(0,min(bottom-h,self.root.winfo_screenheight()-h))}')
 def toggle_panel(self,e=None):
  if self.panel is not None:self.panel.destroy();self.panel=None;self.reshape(200,230);return
  self.reshape(540,565);self.panel=ttk.Frame(self.root,padding=12);self.panel.place(x=0,y=0,width=540,height=335)
  top=ttk.Frame(self.panel);top.pack(fill='x');ttk.Label(top,text='John • PC Sentinelle',font=('Segoe UI',14,'bold')).pack(side='left');ttk.Button(top,text='Réduire',command=self.toggle_panel).pack(side='right')
  ttk.Label(self.panel,text='Discussion IA, outils PC et réception de fichiers').pack(anchor='w')
  self.out=scrolledtext.ScrolledText(self.panel,height=7,wrap='word',font=('Segoe UI',10));self.out.pack(fill='both',expand=True,pady=6)
  for line in self.history:self.out.insert('end',line+'\n\n')
  row=ttk.Frame(self.panel);row.pack(fill='x');self.entry=ttk.Entry(row);self.entry.pack(side='left',fill='x',expand=True);self.entry.bind('<Return>',lambda e:self.command());ttk.Button(row,text='Envoyer',command=self.command).pack(side='left')
  row=ttk.Frame(self.panel);row.pack(fill='x',pady=4)
  for label,fn in [('PC Sentinelle',self.pc),('Diagnostic',lambda:self.pc_tool('diagnostic')),('Réparer',lambda:self.pc_tool('repairOneClick')),('Mes outils',self.catalog)]:ttk.Button(row,text=label,command=fn).pack(side='left',expand=True,fill='x')
  row=ttk.Frame(self.panel);row.pack(fill='x')
  for label,fn in [('Téléphone → PC',lambda:self.transfer('photo/JohnPhoto.exe')),('Connexion IA',self.configure_ai),('Fichiers transférés',self.folder)]:ttk.Button(row,text=label,command=fn).pack(side='left',expand=True,fill='x')
 def show(self,value):
  if isinstance(value,dict) and value.get('report_path'):
   self.last_pc_result=value.get('tool_result',value)
  if isinstance(value,dict) and value.get('message'):
   line=value['message']
   if value.get('tool_result') is not None:line+='\nRésultat de l’outil : '+json.dumps(value['tool_result'],ensure_ascii=False,indent=2)
  else:line=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)
  self.history.append(line);self.history=self.history[-60:]
  if self.panel is not None:
   if len(self.out.get('1.0','end'))>40000:self.out.delete('1.0','end');self.out.insert('end','\n\n'.join(self.history[-10:])+'\n')
   else:self.out.insert('end',line+'\n\n')
   self.out.see('end')
 def command(self):
  if self.busy:return
  text=self.entry.get().strip();self.entry.delete(0,'end')
  if not text:return
  self.show('> '+text)
  if 'pc sentinelle' in text.lower() and any(w in text.lower() for w in ('ouvre','lance')):self.pc();return
  q=text.lower()
  if any(x in q for x in ('recevoir une photo','recevoir un fichier','téléphone vers pc','telephone vers pc')):self.transfer('photo/JohnPhoto.exe');return
  prefixes={'désinstalle ':'uninstall','desinstalle ':'uninstall','désactive au démarrage ':'toggleStartup','desactive au demarrage ':'toggleStartup','nettoie le fichier ':'clean','sélectionne ':'select','selectionne ':'select'}
  for prefix,action in prefixes.items():
   if q.startswith(prefix):
    target=text[len(prefix):].strip()
    def selected_action(action=action,target=target):
     if not self.last_pc_result:raise ValueError('Lancez d’abord la liste ou l’analyse correspondante.')
     if not self.last_pc_result.get('session'):
      raise ValueError('Choisissez et confirmez cette action dans la fenêtre PC Sentinelle ouverte.')
     return follow(self.last_pc_result['report_path'],action,choose(self.last_pc_result,target),self.messages.put)
    self.work(selected_action);return
  self.work(lambda:self.handle_request(text))
 def configure_ai(self):
  subprocess.Popen([str(ROOT/'runtime/pythonw.exe'),str(ROOT/'john_connexion.py')],cwd=ROOT)
  self.show('Configuration IA ouverte. La clé API est personnelle et chiffrée par Windows ; aucun mot de passe ChatGPT demandé.')
 def handle_request(self,text):
  if text.strip().lower() in ('bonjour','bonjour john','salut','salut john','bonsoir','coucou'):
   return 'Bonjour ! Je suis là. Que puis-je faire pour vous ?'
  key=load_key()
  if key:
   try:
    result=ask(text,key,CATALOG,lambda tag:run(tag,self.messages.put),self.ai_history)
   except PlannerError as exc:
    return {'ok':False,'message':str(exc)}
   self.ai_history.extend([{'role':'user','content':text},{'role':'assistant','content':result.get('message','')}])
   self.ai_history=self.ai_history[-12:]
   return result
  tag=select(text)
  if tag:return run(tag,self.messages.put)
  result=gui.executer_demande(text)
  if needs_planner(result):
   return {'ok':False,'message':'Cette demande nécessite l’IA. Cliquez sur Connexion IA pour la configurer.'}
  return result
 def pc_tool(self,tag):self.work(lambda:run(tag,self.messages.put))
 def pc(self):
  exe=ROOT.parent/'PC/PC_Sentinelle_V32.exe'
  if not exe.is_file():self.show('PC Sentinelle absent. Aucun lancement confirmé.');return
  subprocess.Popen([str(exe)],cwd=exe.parent);self.show('PC Sentinelle lancé. Sélectionnez un outil ou donnez votre demande à John.')
 def transfer(self,name):
  exe=ROOT/name
  if not exe.is_file():self.show('Module de transfert absent.');return
  subprocess.Popen([str(exe)],cwd=exe.parent);self.show('Module V1 lancé. Utilisez l’adresse et le code affichés pour le transfert. Le fichier doit être reçu avant de confirmer le succès.')
 def folder(self):
  folder=Path.home()/'Pictures'/'John Transferts';folder.mkdir(parents=True,exist_ok=True);os.startfile(str(folder))
 def catalog(self):
  if getattr(self,'catalog_frame',None) is not None and self.catalog_frame.winfo_exists():
   self.catalog_frame.destroy();return
  frame=ttk.Frame(self.panel,padding=6);self.catalog_frame=frame
  frame.place(x=0,y=36,relwidth=1,height=250)
  ttk.Label(frame,text='Choisissez un outil — les confirmations restent nécessaires').pack(anchor='w')
  box=tk.Listbox(frame,height=8);box.pack(fill='both',expand=True)
  tags=sorted(CATALOG,key=lambda tag:CATALOG[tag])
  for tag in tags:box.insert('end',CATALOG[tag])
  def launch():
   choice=box.curselection()
   if choice:
    tag=tags[choice[0]];frame.destroy();self.pc_tool(tag)
  row=ttk.Frame(frame);row.pack(fill='x')
  ttk.Button(row,text='Ouvrir cet outil',command=launch).pack(side='left')
  ttk.Button(row,text='Retour',command=frame.destroy).pack(side='right')
  box.bind('<Double-Button-1>',lambda e:launch())
def main():
 smoke='--smoke' in sys.argv
 if not smoke and os.name=='nt':
  import ctypes
  kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.CreateMutexW.restype=ctypes.c_void_p
  mutex=kernel.CreateMutexW(None,False,'Local\\JohnPCSentinelleSuiteKnight')
  if ctypes.get_last_error()==183:return
  if not mutex:raise ctypes.WinError(ctypes.get_last_error())
 if not smoke:
  receiver=ROOT/'file_mailbox.py'
  if receiver.is_file():
   subprocess.Popen([str(ROOT/'runtime/pythonw.exe'),str(receiver)],cwd=ROOT,creationflags=0x08000208,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 if smoke:
  class Dummy:
   def __init__(self):self.last_error=''
   def start(self):pass
   def close(self):pass
  gui.Runtime=Dummy
 else:gui.Runtime=CompanionRuntime
 root=tk.Tk();app=Bubble(root);root.protocol('WM_DELETE_WINDOW',app.shutdown)
 if smoke:
  app.toggle_panel();root.update();assert app.panel.winfo_toplevel()==root
  assert not any(isinstance(w,tk.Toplevel) for w in root.winfo_children())
  assert app.canvas.winfo_width()==200
  app.toggle_panel();root.update();assert root.winfo_width()==200 and root.winfo_height()==230
  root.destroy();print('SUITE_KNIGHT_SINGLE_BUBBLE_OK');return
 app.show('John V33.0.5 est ouvert. Exemples : bonjour John, diagnostic, mon Internet rame. Connexion IA permet de configurer votre clé personnelle.')
 if not smoke and not load_key():
  app.toggle_panel()
  app.show('Première connexion : cliquez sur Connexion IA pour activer les réponses OpenAI. Les outils PC restent utilisables sans IA.')
 root.mainloop()
if __name__=='__main__':main()
