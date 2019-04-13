import json
from datetime import datetime, timedelta
from pivovar import wash
from pivovar import wash_machine
from pivovar import config as cfg
from pivovar import unipi
import pytest
from .themock import MagicMock, patch


@pytest.fixture
def backend():
    backend = MagicMock()
    backend.temp.return_value = cfg.REQ_TEMP
    backend.ALL_RLYS = unipi.UniPi.ALL_RLYS
    yield backend


@pytest.fixture
def mocked_backend_washing_machine(backend):
    wm = wash_machine.WashMachine()
    wm.backend = backend
    yield wm


@patch("pivovar.wash_machine.WashMachine.is_fuse_blown")
@patch("pivovar.wash_machine.WashMachine.is_total_stop_pressed")
@patch("pivovar.wash_machine.time")
def test_heating(time_mock, ts, fb, mocked_backend_washing_machine):
    ts.return_value = fb.return_value = False
    mocked_backend_washing_machine.heating()


@patch("pivovar.wash_machine.WashMachine.is_fuse_blown")
@patch("pivovar.wash_machine.WashMachine.is_total_stop_pressed")
@patch("pivovar.wash_machine.time")
def test_reset(time_mock, ts, fb, mocked_backend_washing_machine):
    ts.return_value = fb.return_value = False
    mocked_backend_washing_machine.reset()


def test_washing_machine_add_temp(mocked_backend_washing_machine):
    wm = mocked_backend_washing_machine
    for i in range(wm.MAX_TEMP_SAMPLES_COUNT+2):
        wm.add_temp(datetime.now() + timedelta(seconds=i), i)
    assert len(wm.temp_log) == wm.MAX_TEMP_SAMPLES_COUNT


@patch('pivovar.unipi.Client')
def test_check(rpc_client_mock, mocked_backend_washing_machine):
    wash_machine = mocked_backend_washing_machine
    backend = unipi.UniPiJSONRPC('someaddress')
    backend.server.sensor_get.return_value = (
        80.2, False, 1554587741.331581, 15)
    wash_machine.check()


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
