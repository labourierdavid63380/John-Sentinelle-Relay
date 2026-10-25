from pathlib import Path
import hashlib,json,zipfile
r=Path(__file__).resolve().parent/'Delivery34_0_3'
exe=r/'PC_Sentinelle_John_Setup_34_0_3.exe'
v=json.loads((r/'VALIDATION.json').read_text())
required=['fresh_install','bundled_runtime_ui_and_dpapi','desktop_shortcuts','unknown_python_process_guard','upgrade_with_receiver_running','native_pc_window','uninstall_preserves_personal_data']
assert all(v.get(k) is True for k in required),v
sha=hashlib.sha256(exe.read_bytes()).hexdigest()
(r/'SHA256.txt').write_text(sha+'  '+exe.name+'\n',encoding='ascii')
(r/'LIRE_MOI.txt').write_text('''PC SENTINELLE + JOHN 34.0.3 — 25 octobre 2026
Extraire le ZIP puis lancer PC_Sentinelle_John_Setup_34_0_3.exe.
Windows 10/11 64 bits. Installation unique, moteurs inclus, raccourcis Bureau.
PC Sentinelle conserve les fichiers de la version 34.0.2.
John intègre le compagnon réparé 33.0.5 et son bouton Connexion IA.
Passerelle V24 et transfert V1 : 113 composants identiques.

CONNEXION IA
Une clé API OpenAI personnelle est nécessaire pour le dialogue IA.
L'abonnement ChatGPT ne fournit pas les crédits API. Aucun mot de passe ChatGPT n'est demandé.
Le bouton Tester et enregistrer vérifie une réponse avant le stockage chiffré Windows.
Aucune clé personnelle n'est incluse dans cet installateur public.
Les salutations et outils locaux restent disponibles sans IA.

VÉRIFICATIONS
Tests automatisés sur runner Windows : installation, mise à jour avec récepteur actif,
interface du chevalier, Python embarqué, chiffrement DPAPI, raccourcis, ouverture native PC,
garde contre les processus Python inconnus, désinstallation sans suppression des données personnelles.
Ces tests ne valident pas toutes les actions PC ni un transfert depuis un téléphone physique.
Le dernier essai réel de génération OpenAI a reçu une erreur 429 de quota ou limite.
Le fonctionnement du dialogue dépend des crédits et autorisations API de chaque utilisateur.

L'installateur n'est pas signé par un certificat commercial : Windows peut afficher un avertissement.
''',encoding='utf-8-sig')
zpath=r/'PC_SENTINELLE_JOHN_34_0_3.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_STORED) as z:
 for p in [exe,r/'SHA256.txt',r/'LIRE_MOI.txt',r/'VALIDATION.json']:z.write(p,p.name)
with zipfile.ZipFile(zpath) as z:assert z.testzip() is None
print(json.dumps({'file':str(zpath),'bytes':zpath.stat().st_size,'exe_sha256':sha,'zip_sha256':hashlib.sha256(zpath.read_bytes()).hexdigest()}))
