import ads
# TODO: Note this can also be set in ~/.ads/dev_key or by env var ADS_DEV_KEY
ads.config.token = open("ads_token").read()