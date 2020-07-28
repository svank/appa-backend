import time

from flask import Flask, request

import cache_buddy
from backend_common import _find_route, _get_progress
from log_buddy import lb

app = Flask(__name__)
lb.set_log_level(lb.INFO)


@app.before_first_request
def clear_cache():
    clear_start = time.time()
    cache_buddy.clear_stale_data()
    lb.i(f"Cleared stale cache data in {time.time() - clear_start:.2f} s")


@app.route('/find_route', methods=['GET', 'POST'])
def find_route():
    data, code, headers, cache_key = _find_route(request)
    return data, code, headers


@app.route('/get_progress')
def get_progress():
    return _get_progress(request)
