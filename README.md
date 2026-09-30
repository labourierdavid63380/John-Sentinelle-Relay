# John Sentinelle Relay - Render

Small pairing relay for John Sentinelle.

Render settings:
- Runtime: Python 3
- Build command: `python -m compileall server.py`
- Start command: `python server.py`
- Environment secret: `JOHN_ENROLL_KEY` (at least 32 random characters; never commit it)

Render provides the public HTTPS URL and forwards requests to the internal HTTP `PORT` automatically.

Note: the default SQLite database is ephemeral on hosts without a persistent disk. This is suitable for the first pairing test; production deployment should use persistent storage.
