from pathlib import Path
import hashlib,json,zipfile
r=Path(__file__).resolve().parent/'Delivery34_0_4'
exe=r/'PC_Sentinelle_John_Setup_34_0_4.exe'
v=json.loads((r/'VALIDATION.json').read_text())
required=['fresh_install','bundled_runtime_ui_and_dpapi','desktop_shortcuts','unknown_python_process_guard','upgrade_with_receiver_running','native_pc_window','uninstall_preserves_personal_data','windows_session_autostart']
assert all(v.get(k) is True for k in required),v
sha=hashlib.sha256(exe.read_bytes()).hexdigest()
(r/'SHA256.txt').write_text(sha+'  '+exe.name+'\n',encoding='ascii')
(r/'LIRE_MOI.txt').write_text('PC SENTINELLE + JOHN 34.0.4 — 26 octobre 2026\nExtraire le ZIP puis lancer PC_Sentinelle_John_Setup_34_0_4.exe.\nWindows 10/11 64 bits. Installation autonome unique, raccourcis Bureau.\nDémarrage automatique de John avec la session Windows (option sélectionnée par défaut).\nJohn compagnon 33.0.6 : bouton Connecter ChatGPT accessible depuis la bulle.\nDonnez vos demandes dans ChatGPT avec le plugin John Sentinelle activé.\nLa bulle exécute les commandes locales ; elle ne fournit pas un dialogue ChatGPT autonome.\nAucun appel de génération à l’API OpenAI payante dans ce mode.\n\nCONNEXION DU PLUGIN\nConfigurer votre propre identifiant de tunnel et sa clé runtime (Tunnels Read + Use).\nLa configuration existante du compte Windows est conservée ; clé chiffrée par Windows.\nAucune clé personnelle, aucun identifiant de tunnel individuel dans ce paquet public.\nLe compagnon démarre le tunnel même si le serveur local répond déjà.\nL’état affiché est celui du tunnel ; seul un appel depuis ChatGPT valide la liaison complète.\nUn tunnel arrêté est relancé périodiquement tant que John reste ouvert.\nRéduire John conserve la connexion ; quitter John arrête ses propres processus.\nL’association au compte ChatGPT et les autorisations restent nécessaires.\n\nVÉRIFICATIONS\nV24 et transfert V1 : composants protégés vérifiés identiques.\nFichiers PC conservés. Tests Windows : interface, installation, mise à jour,\nraccourcis, stockage DPAPI et désinstallation sans suppression des données personnelles.\nLa connexion à un compte utilisateur et le transfert depuis un téléphone physique\nne peuvent pas être certifiés par les tests CI sans ces appareils et identifiants.\nLe certificat de signature commercial n’est pas fourni.\n',encoding='utf-8-sig')
zpath=r/'PC_SENTINELLE_JOHN_34_0_4.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_STORED) as z:
 for p in [exe,r/'SHA256.txt',r/'LIRE_MOI.txt',r/'VALIDATION.json']:z.write(p,p.name)
with zipfile.ZipFile(zpath) as z:assert z.testzip() is None
print(json.dumps({'file':str(zpath),'bytes':zpath.stat().st_size,'exe_sha256':sha,'zip_sha256':hashlib.sha256(zpath.read_bytes()).hexdigest()}))
