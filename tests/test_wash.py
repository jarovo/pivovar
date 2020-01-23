import pytest
import json
from datetime import datetime, timedelta

from pivovar import wash
from pivovar import wash_machine

from .themock import MagicMock, patch


@pytest.fixture
def rpc_client_mock():
    rpc_client_mock = MagicMock()
    yield rpc_client_mock


@pytest.fixture
def mocked_backend_wm(rpc_client_mock):
    wm = wash_machine.WashMachine('test wash machine')
    wm._unipi_jsonrpc = rpc_client_mock
    wm.init_io()
    wm.io.inp.fuse_ok.read_state = MagicMock(return_value=True)
    wm.io.inp.total_stop.read_state = MagicMock(return_value=False)
    wm.io.inp.keg_present.read_state = MagicMock(side_effect=[False, True])
    yield wm


@pytest.fixture
def phase_mock(mocked_backend_wm):
    mocked_backend_wm.keep_running = MagicMock(side_effect=[True, False])
    mocked_backend_wm.keep_repeating = MagicMock(side_effect=[True, False])
    m = MagicMock()
    mocked_backend_wm.wash_cycle = [m]
    yield m


@patch("time.sleep")
def test_wash_the_kegs(sleep_mock, mocked_backend_wm, phase_mock):
    mocked_backend_wm.wash_the_kegs()
    assert phase_mock.called


@patch("time.sleep")
@patch("pivovar.wash_machine.logger")
def test_wash_the_kegs_exception(
    logger_mock, sleep_mock, mocked_backend_wm, phase_mock
):
    phase_mock.side_effect = [Exception('mocked exception')]
    mocked_backend_wm.wash_the_kegs()
    assert phase_mock.called
    assert logger_mock.exception.called


@patch("time.sleep")
def test_phases(sleep_mock, mocked_backend_wm):
    wm = mocked_backend_wm
    tested_phases = (
        wm.prewash,
        wm.drain,
        wm.wash_with_lye,
        wm.rinse_with_cold_water,
        wm.wash_with_hot_water,
        wm.dry,
        wm.fill_with_co2,
    )
    for phase in tested_phases:
        phase()


@patch("time.sleep")
def test_wait_for_keg(sleep_mock, mocked_backend_wm):
    mocked_backend_wm.io.inp.keg_present.read_state = MagicMock(
        side_effect=[False, True]
    )
    mocked_backend_wm.wait_for_keg()


@patch("time.sleep")
def test_heating(sleep_mock, mocked_backend_wm):
    mocked_backend_wm.io.water_temp.read_temperature = MagicMock(
        side_effect=[20, mocked_backend_wm.required_water_temp]
    )
    mocked_backend_wm.heating()


@pytest.fixture
def all_io_member(mocked_backend_wm):
    class Printable(object):
        __str__ = MagicMock()
        is_defined = MagicMock()

    printable_io = Printable()
    mocked_backend_wm.io.leafs = [printable_io]
    yield printable_io


def test_check_fail(mocked_backend_wm, all_io_member):
    all_io_member.is_defined.return_value = False
    with pytest.raises(Exception):
        mocked_backend_wm.check()
    assert all_io_member.is_defined.called
    assert all_io_member.__str__.called


def test_check_pass(mocked_backend_wm, all_io_member):
    all_io_member.is_defined.return_value = True
    mocked_backend_wm.check()
    assert all_io_member.is_defined.called


def test_check(mocked_backend_wm, rpc_client_mock):
    rpc_client_mock.sensor_get.return_value = (
        80.2,
        False,
        1554587741.331581,
        15,
    )
    mocked_backend_wm.check()


@patch("time.sleep")
@patch("pivovar.wash_machine.logger")
def test_temps_update(
    logger_mock, sleep_mock, mocked_backend_wm, rpc_client_mock
):
    mocked_backend_wm.keep_running = MagicMock(side_effect=[True, True, False])
    rpc_client_mock.sensor_get.side_effect = [
        (80.2, False, 1554587741.331581, 15),
        (80.2, True, 1554587741.331581, 15),
    ]
    mocked_backend_wm.temps_update()
    assert logger_mock.exception.called


@patch(
    "pivovar.wash_machine.WashMachine.is_fuse_blown", side_effect=[True, False]
)
@patch(
    "pivovar.wash_machine.WashMachine.is_total_stop_pressed",
    side_effect=[True, False],
)
@patch("pivovar.wash_machine.time")
def test_wait_until_inputs_ok(time_mock, fb, ts, mocked_backend_wm):
    mocked_backend_wm.wait_until_inputs_ok()


def test_washing_machine_add_temp(mocked_backend_wm):
    wm = mocked_backend_wm
    for i in range(wm.temp_samples_count_limit + 2):
        wm.add_temp(datetime.now() + timedelta(seconds=i), i)
    assert len(wm.temp_log) == wm.temp_samples_count_limit


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
    response = json.loads(flask_client.get('/temp_log').data.decode())
    expected = {
        'datetime': [
            "2018-08-24 15:03:54",
            "2018-08-24 15:03:55",
            "2018-08-24 15:03:56",
        ],
        'temps': ["0", "1", None],
    }
    expected == response


def test_index(flask_client):
    assert flask_client.get('/')
