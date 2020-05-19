# appa-backend

> Astronomy Publication Proximity Analyzer (APPA): finds chains of collaboration using the ADS API

A web interface is live at [samvankooten.net/appa](https://samvankooten.net/appa), with code at [appa-web](https://github.com/svank/appa-web).

The Astronomy Publication Proximity Analyzer (APPA) uses the ADS database to let you explore connections between authors. Given two names, APPA will find the chains of coauthorship (person A published a paper with B, who wrote a paper with C...) connecting those two names.

Requires an access token for the [ADS API](http://adsabs.github.io/help/api/) entered in `local_config.py`.

Can be run locally, with output as an ASCII table of connection chains (see `appa.py`).

Can also be run as a backend for the more useful [web interface](https://github.com/svank/appa-backend), as either a Flask server (see `appa_web_backend.py`) or in Google Cloud (see `main.py`).

To speed up path finding and reduce the number of ADS queries, data received from ADS is cached locally. Two cache backends are provided: using the local filesystem (see `cache_fs.py`) and using GCP Firestore (see `cache_firestore.py`).