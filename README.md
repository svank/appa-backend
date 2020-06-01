# appa-backend

> Astronomy Publication Proximity Analyzer (APPA): finds chains of collaboration using the ADS API

A web interface is live at [samvankooten.net/appa](https://samvankooten.net/appa), with code at [appa-web](https://github.com/svank/appa-web).

The Astronomy Publication Proximity Analyzer (APPA) uses the ADS database to let you explore connections between authors. Given two names, APPA will find the chains of coauthorship (person A published a paper with B, who wrote a paper with C...) connecting those two names.

Using the web interface at [samvankooten.net/appa](samvankooten.net/appa) is recommended, as the web interface is more fully-featured than the textual terminal output mode, and using a shared instance allows you to benefit from a pre-populated cache of ADS query results. However you can run your own instance for fun or if you plan to run very large numbers of searches for connections (i.e. in an automated fashion). 

### How to run

To run your own copy of APPA, you'll need to register for an access token for the [ADS API](http://adsabs.github.io/help/api/). Copy `local_config.sample.py` to `local_config.py` and insert your key in the line `ADS_TOKEN = "token_here"`.

APPA can be run locally, with output as an ASCII table of connection chains (see `appa.py`).

APPA can also be run as a backend for the more useful [web interface](https://github.com/svank/appa-backend), as either a Flask server (see `appa_web_backend.py`) or in Google Cloud (see `main.py`; requires additional configuration in `local_config.py`).

To speed up path finding and reduce the number of ADS queries, data received from ADS is cached locally. Two cache backends are provided: using the local filesystem (see `cache_fs.py`; the directory path used for caching data is set by `cache_fs_dir` in `local_config.py`) and using GCP Firestore (see `cache_firestore.py`; progress data is relayed through an App Engine instance---see `progress_relay/`). The choice of cache backend is made in `local_config.py`.