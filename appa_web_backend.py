from flask import Flask, request

from backend_common import _find_route, _get_progress
from log_buddy import lb

app = Flask(__name__)
lb.set_log_level(lb.INFO)


@app.route('/find_route', methods=['GET', 'POST'])
def find_route():
    data, code, headers, cache_key = _find_route(request)
    return data, code, headers


@app.route('/get_progress')
def get_progress():
    return _get_progress(request)
