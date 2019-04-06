import json
from datetime import datetime, timedelta
from pivovar import wash
from pivovar import phases
from pivovar import config as cfg
from pivovar import unipi
import pytest
from .themock import MagicMock, patch


@pytest.fixture
def phases_patched():
    phases.delay = MagicMock()
    yield phases


@pytest.fixture
def backend():
    backend = MagicMock()
    backend.temp.return_value = cfg.REQ_TEMP
    backend.ALL_RLYS = unipi.UniPi.ALL_RLYS
    yield backend


@patch("pivovar.phases.time")
def test_heating(time_mock, backend, phases_patched):
    phases_patched.heating(backend)


@patch("pivovar.phases.time")
def test_reset(time_mock, backend, phases_patched):
    phases_patched.reset(backend)


def test_washing_machine_add_temp():
    wm = wash.WashMachine()
    for i in range(wm.MAX_TEMP_SAMPLES_COUNT+2):
        wm.add_temp(datetime.now() + timedelta(seconds=i), i)
    assert len(wm.temp_log) == wm.MAX_TEMP_SAMPLES_COUNT


@pytest.fixture
def flask_app():
    app = wash.app
    app.testing = True
    yield app


@pytest.fixture
def flask_client(flask_app):
    with flask_app.test_client() as cli:
        yield cli


def test_real_temps(flask_client):
    date = datetime(2018, 8, 24, 15, 3, 55)
    wash.wash_machine.add_temp(date, 1)
    response = json.loads(flask_client.get('/temp_log').data)
    assert {'datetime': ["2018-08-24 15:03:55"], 'temps': ["1"]} == response


def test_index(flask_client):
    assert flask_client.get('/')
