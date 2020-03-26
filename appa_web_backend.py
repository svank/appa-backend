import hashlib
import json

from flask import Flask, request

import cache_buddy
from log_buddy import lb
from path_finder import PathFinder
from route_jsonifyer import to_json

app = Flask(__name__)


@app.route('/find_route')
def find_route():
    lb.set_log_level(lb.WARNING)
    source, dest, exclude = parse_url_args(request)
    lb.set_progress_key(make_progress_key(source, dest, exclude))
    
    pf = PathFinder(source, dest, exclude)
    pf.find_path()
    
    data = to_json(pf, lb)
    
    lb.reset_stats()
    return data


@app.route('/get_progress')
def get_progress():
    source, dest, exclude = parse_url_args(request)
    key = make_progress_key(source, dest, exclude)
    try:
        data = cache_buddy.load_progress_data(key)
        return json.dumps(data.asdict())
    except:
        return json.dumps({"error": True})


def make_progress_key(source, dest, exclude):
    string = f"src={source}&dest={dest}&exclusions={';'.join(exclude)}"
    return hashlib.sha256(string.encode()).hexdigest()


def parse_url_args(request):
    source = request.args.get('src')
    dest = request.args.get('dest')
    exclude = request.args.get('exclusions')
    if exclude is not None:
        exclude = exclude.split('\n')
        # Remove duplicates
        exclude = set(exclude)
    else:
        exclude = set()
    return source, dest, exclude


@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response
