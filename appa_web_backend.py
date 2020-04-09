from flask import Flask, request

from backend_common import _find_route, _get_progress

app = Flask(__name__)


@app.route('/find_route')
def find_route():
    return _find_route(request)


@app.route('/get_progress')
def get_progress():
    return _get_progress(request)
