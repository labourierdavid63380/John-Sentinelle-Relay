# John Sentinelle Relay - Render

Small pairing relay for John Sentinelle.

Render settings:
- Runtime: Python 3
- Build command: `python -m compileall server.py`
- Start command: `python server.py`
- Environment secret: `JOHN_ENROLL_KEY` (at least 32 random characters; never commit it)

Render provides the public HTTPS URL and forwards requests to the internal HTTP `PORT` automatically.

Note: the default SQLite database is ephemeral on hosts without a persistent disk. This is suitable for the first pairing test; production deployment should use persistent storage.

## Correction anti-boucle d'authentification (v3)

Cette version utilise désormais un jeton PC signé par `JOHN_ENROLL_KEY`. Après une première inscription avec cette version, l'identité du PC reste vérifiable même si la base SQLite éphémère de Render est recréée lors d'un redéploiement.

Important : un PC qui possède encore un ancien jeton aléatoire provenant d'une version précédente doit être réinscrit **une seule fois**. Après cette réinscription, les redéploiements n'entraînent plus le message « PC non authentifié », tant que `JOHN_ENROLL_KEY` n'est pas modifiée.

La base SQLite contient toujours les associations téléphone et les missions en cours. Sur une instance Render sans disque persistant, celles-ci peuvent être perdues lors d'un redémarrage. Le PC, lui, pourra recréer immédiatement un nouveau QR sans devoir être réinscrit.
