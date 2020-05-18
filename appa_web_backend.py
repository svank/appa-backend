from flask import Flask, request

from backend_common import _find_route, _get_progress
from log_buddy import lb

app = Flask(__name__)
lb.set_log_level(lb.INFO)


@app.route('/find_route', methods=['GET', 'POST'])
def find_route():
    return _find_route(request)


@app.route('/get_progress')
def get_progress():
    return _get_progress(request)
