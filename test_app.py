import json
import time
import uuid

from app import app

NEW_EXPERIMENT = {
    'name': 'Test experiment',
    'policy': 'epsilon_greedy',
    'choices': ['A', 'B', 'C'],
    'parameters': {'epsilon': 0.1},
}

def test_index():
    request, response = app.test_client.get('/')
    assert response.status == 200
    assert 'session' in request

def test_reset_session():
    request, response = app.test_client.get('/')
    initial_session_id = request['session'].sid
    request, response = app.test_client.get('/reset-session')
    assert list(request['session'].keys()) == []
    assert initial_session_id != request['session'].sid

def test_register_experiment():
    request, response = app.test_client.post('/', data=json.dumps(NEW_EXPERIMENT))
    assert response.status == 200

    # TODO Test that we cant create multiple by same id
    # TODO test expr with invalid data

def test_get_experiment():
    request, response = app.test_client.post('/', data=json.dumps(NEW_EXPERIMENT))
    new_experiment_id = response.json['experiment_id']

    request, response = app.test_client.get('/' + new_experiment_id)
    assert response.status == 200
    assert 'message' in response.json
    assert 'choice' in response.json
    # TODO test fetching invalid experiment
    # TODO test that choice stays the same per session
    pass

def test_success():
    request, response = app.test_client.post('/', data=json.dumps(NEW_EXPERIMENT))
    new_experiment_id = response.json['experiment_id']

    # Make a bunch of 0 successes
    choice = '0'
    for i in range(10):
        app.test_client.get('/' + new_experiment_id)
        app.test_client.post('/' + new_experiment_id + '/' + choice)

    # 90% of these should exploit the fact that 0 is popular
    # it's very unlikely 0 isn't the most common
    choices = []
    for i in range(10):
        request, response = app.test_client.get('/' + new_experiment_id)
        choices.append(response.json.get('choice'))

    assert max(set(choices), key=choices.count) == 0
