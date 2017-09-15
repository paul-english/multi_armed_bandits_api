import json
import random
import uuid
from collections import namedtuple

import asyncio_redis
from sanic import Sanic
from sanic_session import RedisSessionInterface
from schema import And, Schema

from policies import POLICIES
from utils import hash_key, json_response, valid_uuid

EXPERIMENT_SCHEMA = Schema({
    'name': str,
    'policy': lambda s: s in POLICIES.keys(),
    'choices': [str],
    'parameters': object
})

app = Sanic()

@app.route("/")
async def index(request):
    return json_response({"message": "Hello."})

@app.route("/", methods=['POST'])
async def register_experiment(request):
    redis = request.app.redis

    experiment_id = uuid.uuid4().hex
    experiment = EXPERIMENT_SCHEMA.validate(request.json)

    experiment_exists = await redis.hexists(
        hash_key('experiments', experiment_id),
        experiment_id
    )
    if experiment_exists:
        return json_response({"message": "Experiment by this id already exists."}, status=400)

    await redis.hset(
        hash_key('experiments', experiment_id),
        experiment_id,
        json.dumps(experiment),
    )

    print('- registered')
    return json_response({
        "message": "New experiment created.",
        "experiment_id": experiment_id,
    })


@app.route("/<experiment_id:[a-z0-9]+>", methods=['GET'])
async def get_experiment(request, experiment_id):
    redis = request.app.redis
    session_id = request['session'].sid

    try:
        experiment = json.loads(await redis.hget(hash_key('experiments', experiment_id), experiment_id))
    except TypeError as e:
        print('Error', e)
        return json_response({"message": "Invalid experiment. Has it been registered?"}, status=404)
    print('--- expr', experiment)

    # TODO check if session in experiment
    # if not, increase samples
    # TODO always return same choice for this session
    print('--', hash_key('samples', experiment_id), experiment_id)

    policy = POLICIES[experiment.get('policy')]
    choice_idx = await policy(
        experiment_id,
        experiment,
        redis
    )

    print('--- choice_idx', choice_idx)
    await redis.sadd(
        'samples:%s:%s' % (experiment_id, choice_idx),
        [session_id]
    )

    return json_response({
        "message": "Ok.",
        "choice": choice_idx,
    })

@app.route("/<experiment_id:[a-z0-9]+>/<choice:[0-9]+>", methods=['POST'])
async def success(request, experiment_id, choice):
    redis = request.app.redis
    session_id = request['session'].sid

    await redis.sadd(
        'successes:%s:%s' % (experiment_id, choice),
        [session_id]
    )
    # get policy
    # compute posterior based on experiment
    return json_response({"message": "Ok."})

@app.route("/reset-session")
async def reset_session(request):
    request['session'].clear()
    request['session'].sid = uuid.uuid4().hex
    return json_response({"message": "Session reset."})

################################################################
################################################################
################################################################

@app.listener('before_server_start')
async def before_server_start(app, loop):
    app.redis = await asyncio_redis.Pool.create(
        host='localhost',
        port=6379,
        poolsize=10
    )

    async def pool_getter():
        return app.redis

    app.session_interface = RedisSessionInterface(pool_getter)

@app.listener('after_server_stop')
async def after_server_stop(app, loop):
    app.redis.close()
    pass

@app.middleware('request')
async def add_session_to_request(request):
    await request.app.session_interface.open(request)

@app.middleware('response')
async def save_session(request, response):
    await request.app.session_interface.save(request, response)

################################################################
################################################################
################################################################

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
