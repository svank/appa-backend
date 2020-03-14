from flask import Flask, request

from log_buddy import lb
from path_finder import PathFinder
from route_jsonifyer import to_json

app = Flask(__name__)


@app.route('/find_route')
def find_route():
    lb.set_log_level(lb.WARNING)
    source = request.args.get('src')
    dest = request.args.get('dest')
    exclude = request.args.get('exclusions')
    if exclude is not None:
        exclude = exclude.split('\n')
    else:
        exclude = []
    
    pf = PathFinder(source, dest, exclude)
    pf.find_path()
    
    lb.reset_stats()
    
    return to_json(pf)


@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response
