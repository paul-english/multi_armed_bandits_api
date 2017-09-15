import math
import re

import numpy as np
from sanic.response import json as sanic_json

UUID_RE = re.compile('^[a-z0-9]+$')

def hash_key(key, uuid):
    """
    When using redis hashes, avoid storing them all in the same bucket

    https://engineering.instagram.com/storing-hundreds-of-millions-of-simple-key-value-pairs-in-redis-1091ae80f74c
    """
    bucket_id = math.floor(int(uuid, 16) / 1000)
    return '%s:%s' % (key, bucket_id)

def valid_uuid(s):
    return len(s) == 32 and UUID_RE.match(s)

def is_iterable(x):
    try:
        iter(x)
        return True
    except TypeError:
        return False

def map_anything(x, fn):
    if isinstance(x, str):
        return fn(x)
    if isinstance(x, dict):
        return {k: map_anything(v, fn) for k, v in x.items()}
    if is_iterable(x):
        return [map_anything(ele, fn) for ele in x]
    return fn(x)

def prepare_for_json(val):
    if isinstance(val, np.int32):
        return int(val)
    if isinstance(val, np.int64):
        return int(val)
    if isinstance(val, np.number):
        return str(val)
    if isinstance(val, np.ndarray):
        return [str(v) for v in val]
    return val

def json_response(data, **kwargs):
    # cls not supported by ujson
    # https://github.com/esnme/ultrajson/issues/124
    return sanic_json(map_anything(data, prepare_for_json), **kwargs)
