import hashlib
import json
import traceback

import cache_buddy
from ads_buddy import ADSRateLimitError
from log_buddy import lb
from path_finder import PathFinder, PathFinderError
from route_jsonifyer import to_json


def _find_route(request):
    source, dest, exclude = parse_url_args(request)
    progress_key = make_progress_key(source, dest, exclude)
    lb.set_progress_key(progress_key)
    lb.d(f"find_route invoked for src:{source}, dest:{dest}, "
         f"excl={';'.join(sorted(exclude))}, pkey={progress_key}")
    
    pf = PathFinder(source, dest, exclude)
    try:
        pf.find_path()
        data = to_json(pf, lb)
    except PathFinderError as e:
        data = json.dumps({
            "error_key": e.key,
            "error_msg": str(e),
            "src": pf.src.name.original_name,
            "dest": pf.dest.name.original_name
        })
    except ADSRateLimitError as e:
        data = json.dumps({
            "error_key": "rate_limit",
            "error_msg": str(e),
            "reset": e.reset_time,
            "src": pf.src.name.original_name,
            "dest": pf.dest.name.original_name
        })
    except:
        lb.e("Uncaught exception: " + traceback.format_exc())
        data = json.dumps({
            "error_key": "unknown",
            "error_msg": "Unexpected server error",
            "src": pf.src.name.original_name,
            "dest": pf.dest.name.original_name
        })
    
    lb.log_stats()
    lb.reset_stats()
    return data, 200, {'Access-Control-Allow-Origin': '*'}


def _get_progress(request):
    source, dest, exclude = parse_url_args(request)
    key = make_progress_key(source, dest, exclude)
    try:
        data = cache_buddy.load_progress_data(key)
        response = json.dumps(data.asdict())
    except:
        response = json.dumps({"error": True})
    return response, 200, {'Access-Control-Allow-Origin': '*'}


def make_progress_key(source, dest, exclude):
    string = f"src={source}&dest={dest}&exclusions={';'.join(sorted(exclude))}"
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
