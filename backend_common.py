import json

import cache_buddy
from ads_buddy import ADSError, ADSRateLimitError
from log_buddy import lb
from path_finder import PathFinder, PathFinderError
from route_jsonifyer import to_json, canonicalize_graph_data

HEADERS = {'Access-Control-Allow-Origin': '*'}


def find_route(request, load_cached_result=True):
    source, dest, exclude = parse_url_args(request)
    
    result_cache_key = cache_buddy.generate_result_cache_key(
        source, dest, exclude)
    
    try:
        if (cache_buddy.result_is_in_cache(result_cache_key)
                and request.args.get('no_cache') is None):
            if load_cached_result:
                data = cache_buddy.load_result(result_cache_key)
            else:
                data = None
            lb.i("Loaded cached result")
            lb.reset_stats()
            return data, 200, HEADERS, result_cache_key
        
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
    else:
        cache_buddy.cache_result(data, result_cache_key)
    
    lb.log_stats()
    lb.reset_stats()
    return data, 200, HEADERS, result_cache_key


def get_progress(request):
    key = request.args.get('key')
    try:
        data = cache_buddy.load_progress_data(key)
        response = json.dumps(data.asdict())
    except:
        response = json.dumps({"error": True})
    return response, 200, HEADERS


def get_graph_data(request):
    source, dest, exclude = parse_url_args(request)
    
    result_cache_key = cache_buddy.generate_result_cache_key(
        source, dest, exclude)

    if cache_buddy.result_is_in_cache(result_cache_key):
        data = cache_buddy.load_result(result_cache_key)
        data = json.loads(data)
        chains = data['chains']
        chains = canonicalize_graph_data(chains)
        data = {'graphData': chains}
    else:
        data = {"error": "data not found"}
        lb.w(f"Graph source data unavailable for src:{source}, dest:{dest}, "
             f"excl:{';'.join(sorted(exclude))}")
    data = json.dumps(data)
    return data, 200, HEADERS


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
