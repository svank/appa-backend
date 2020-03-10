import os.path

import ads

# Note the token can also be set in ~/.ads/dev_key or by env var ADS_DEV_KEY
if os.path.exists("ads_token"):
    _token_data = open("ads_token").read()
    if len(_token_data):
        ads.config.token = _token_data
