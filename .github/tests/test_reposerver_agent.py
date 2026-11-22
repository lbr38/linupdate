"""Unit tests for the reposerver agent websocket handling."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.controllers.lock import Lock
from src.controllers.module.reposerver import agent as agent_module
from src.controllers.module.reposerver.agent import Agent

# Locks taken by the agent go to a temporary directory
pytestmark = pytest.mark.usefixtures('lock_dir')


class FakeWebsocket:
    """Websocket stub recording the messages sent by the agent"""
    def __init__(self) -> None:
        self.sent = []

    def send(self, message) -> None:
        """Record a message sent by the agent"""
        self.sent.append(json.loads(message))


@pytest.fixture(name='agent')
def fixture_agent(tmp_path) -> Agent:
    """Return an agent connected to a fake websocket, with mocked controllers"""
    agent = Agent.__new__(Agent)
    agent.request_dir = str(tmp_path / 'requests')
    agent.configuration = {
        'agent': {'enabled': True, 'listen': {'enabled': True}},
        'client': {'auth': {'id': 'host-id', 'token': 'host-token'}},
        'reposerver': {'url': 'https://repo.example.com'}
    }
    agent.websocket = FakeWebsocket()
    agent.authenticated = False
    agent.websocket_is_running = False
    agent.websocket_exception = None
    agent.reposerver_status_controller = MagicMock()
    agent.config_controller = MagicMock()
    agent.package_controller = MagicMock()
    return agent


def receive(agent, message) -> None:
    """Simulate a message received from the reposerver"""
    agent.websocket_on_message(None, json.dumps(message))


def test_authenticate_request_sends_credentials(agent) -> None:
    """The agent answers an authenticate request with its id and token"""
    receive(agent, {'request': 'authenticate'})

    assert agent.websocket.sent == [
        {'response-to-request': {'request': 'authenticate', 'auth-id': 'host-id', 'token': 'host-token'}}
    ]


def test_authentication_successful(agent) -> None:
    """The agent is authenticated once the reposerver confirms it"""
    receive(agent, {'info': 'Authentication successful'})

    assert agent.authenticated


def test_general_infos_request(agent) -> None:
    """General informations are sent and the request is completed with its log"""
    agent.reposerver_status_controller.send_general_info.side_effect = lambda: print('general informations sent')

    receive(agent, {'request': 'request-general-infos', 'request-id': 7})

    agent.reposerver_status_controller.send_general_info.assert_called_once()
    response = agent.websocket.sent[-1]['response-to-request']
    assert response['request-id'] == '7'
    assert response['status'] == 'completed'
    assert 'general informations sent' in response['log']
    assert Path(agent.request_dir, '7', 'status').read_text(encoding='utf-8') == 'completed'


def test_update_profile_request(agent) -> None:
    """The profile configuration is retrieved, the request goes from running to completed"""
    receive(agent, {'request': 'update-profile', 'request-id': 9})

    agent.config_controller.get_profile_packages_conf.assert_called_once()
    agent.config_controller.get_profile_repos.assert_called_once()
    assert agent.websocket.sent[0] == {'response-to-request': {'request-id': '9', 'status': 'running'}}
    assert agent.websocket.sent[-1]['response-to-request']['status'] == 'completed'


def test_unknown_request_is_reported_as_failed(agent) -> None:
    """An unknown request fails, the error is saved and sent, and the request lock is released"""
    receive(agent, {'request': 'do-something-weird', 'request-id': 42})

    response = agent.websocket.sent[-1]['response-to-request']
    assert response['request-id'] == '42'
    assert response['status'] == 'failed'
    assert 'unknown request sent by reposerver: do-something-weird' in response['error']

    request_dir = Path(agent.request_dir, '42')
    assert (request_dir / 'status').read_text(encoding='utf-8') == 'failed'
    assert 'unknown request' in (request_dir / 'error').read_text(encoding='utf-8')

    assert not Lock.is_locked('reposerver-request')


def test_failing_request_is_reported_as_failed(agent) -> None:
    """An exception while processing a request marks it as failed"""
    agent.reposerver_status_controller.send_packages_info.side_effect = RuntimeError('reposerver unreachable')

    receive(agent, {'request': 'request-packages-infos', 'request-id': 3})

    response = agent.websocket.sent[-1]['response-to-request']
    assert response['status'] == 'failed'
    assert response['error'] == 'reposerver unreachable'
    assert not Lock.is_locked('reposerver-request')


def test_request_response_received_deletes_sent_files(agent) -> None:
    """Files the reposerver confirmed to have received are deleted, the others are kept"""
    request_dir = Path(agent.request_dir, '5')
    request_dir.mkdir(parents=True)
    for name in ('status', 'log', 'error'):
        (request_dir / name).write_text(name, encoding='utf-8')

    receive(agent, {'info': 'Request response received', 'request-id': 5, 'data': ['status', 'log']})

    assert not (request_dir / 'status').exists()
    assert not (request_dir / 'log').exists()
    assert (request_dir / 'error').exists()


@pytest.mark.parametrize('url, expected', [
    ('https://repo.example.com', 'wss://repo.example.com/ws'),
    ('http://repo.example.com', 'ws://repo.example.com/ws'),
    ('https://repo.http-lab.local', 'wss://repo.http-lab.local/ws'),
    ('https://http.example.com:8443', 'wss://http.example.com:8443/ws'),
])
def test_websocket_url_only_replaces_scheme(agent, monkeypatch, url, expected) -> None:
    """Only the URL scheme is converted to its websocket equivalent"""
    websocket_app = MagicMock()
    monkeypatch.setattr(agent_module.websocket, 'WebSocketApp', websocket_app)
    agent.configuration['reposerver']['url'] = url

    agent.websocket_client()

    assert websocket_app.call_args[0][0] == expected
    websocket_app.return_value.run_forever.assert_called_once()
