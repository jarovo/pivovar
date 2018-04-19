import logging

from pivovar import phases
from pivovar import config as cfg
try:
    from unittest.mock import MagicMock, patch
except ImportError:
    from mock import MagicMock, patch


logging.basicConfig(level=logging.DEBUG)


@patch("pivovar.phases.time")
def test_wash_the_keg(time_mock):
    backend = MagicMock()
    backend.temp.return_value = cfg.REQ_TEMP
    phases.delay = MagicMock()
    phases.wash_the_keg(backend)
