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
def mocked_backend_wm(backend):
    wm = wash_machine.WashMachine()
    wm.backend = backend
    yield wm


@patch("pivovar.wash_machine.WashMachine.is_fuse_blown")
@patch("pivovar.wash_machine.WashMachine.is_total_stop_pressed")
@patch("pivovar.wash_machine.WashMachine.is_keg_present",
       side_effect=[False, True])
@patch("pivovar.wash_machine.WashMachine.keep_running",
       side_effect=[True, False])
@patch("pivovar.wash_machine.time")
def test_wash_the_kegs(time_mock, kr, kp, ts, fb, mocked_backend_wm):
    fb.return_value = False
    ts.return_value = False
    mocked_backend_wm.wash_the_kegs()


@patch("pivovar.wash_machine.WashMachine.is_fuse_blown",
       side_effect=[True, False])
@patch("pivovar.wash_machine.WashMachine.is_total_stop_pressed",
       side_effect=[True, False])
@patch("pivovar.wash_machine.time")
def test_wait_until_inputs_ok(time_mock, fb, ts, mocked_backend_wm):
    mocked_backend_wm.wait_until_inputs_ok()


def test_washing_machine_add_temp(mocked_backend_wm):
    wm = mocked_backend_wm
    for i in range(wm.MAX_TEMP_SAMPLES_COUNT+2):
        wm.add_temp(datetime.now() + timedelta(seconds=i), i)
    assert len(wm.temp_log) == wm.MAX_TEMP_SAMPLES_COUNT


@patch('pivovar.unipi.Client')
def test_check(rpc_client_mock, mocked_backend_wm):
    wash_machine = mocked_backend_wm
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
    date = datetime(2018, 8, 24, 15, 3, 54)
    wash.wash_machine.add_temp(date, 0)
    date = datetime(2018, 8, 24, 15, 3, 55)
    wash.wash_machine.add_temp(date, 1)
    date = datetime(2018, 8, 24, 15, 3, 56)
    wash.wash_machine.add_temp(date, None)
    response = json.loads(flask_client.get('/temp_log').data)
    expected = {'datetime': ["2018-08-24 15:03:54",
                             "2018-08-24 15:03:55",
                             "2018-08-24 15:03:56"],
                'temps': ["0", "1", None]}
    expected == response


def test_index(flask_client):
    assert flask_client.get('/')
