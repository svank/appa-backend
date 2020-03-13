import os.path

ADS_TOKEN = ""

if os.path.exists("ads_token"):
    _token_data = open("ads_token").read()
    if len(_token_data):
        ADS_TOKEN = _token_data
