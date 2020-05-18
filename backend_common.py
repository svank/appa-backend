import json

import cache_buddy
from ads_buddy import ADSError, ADSRateLimitError
from log_buddy import lb
from path_finder import PathFinder, PathFinderError
from route_jsonifyer import to_json


def _find_route(request):
    source, dest, exclude = parse_url_args(request)
    try:
        progress_key = request.data.decode()
        lb.i(f"find_route invoked for src:{source}, dest:{dest}, "
             f"excl:{';'.join(sorted(exclude))}, pkey:{progress_key}")
        lb.reset_stats()
        lb.set_progress_key(progress_key)
        
        pf = PathFinder(source, dest, exclude)
        pf.find_path()
        data = to_json(pf)
    except PathFinderError as e:
        data = json.dumps({
            "error_key": e.key,
            "error_msg": str(e),
            "src": source,
            "dest": dest
        })
    except ADSError as e:
        lb.log_exception()
        data = json.dumps({
            "error_key": e.key,
            "error_msg": str(e),
            "src": source,
            "dest": dest
        })
    except ADSRateLimitError as e:
        lb.log_exception()
        data = json.dumps({
            "error_key": "rate_limit",
            "error_msg": str(e),
            "reset": e.reset_time,
            "src": source,
            "dest": dest
        })
    except:
        lb.log_exception()
        data = json.dumps({
            "error_key": "unknown",
            "error_msg": "Unexpected server error",
            "src": source,
            "dest": dest
        })
    
    lb.log_stats()
    lb.reset_stats()
    return data, 200, {'Access-Control-Allow-Origin': '*'}


def _get_progress(request):
    key = request.args.get('key')
    try:
        data = cache_buddy.load_progress_data(key)
        response = json.dumps(data.asdict())
    except:
        response = json.dumps({"error": True})
    return response, 200, {'Access-Control-Allow-Origin': '*'}


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
