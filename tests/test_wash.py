import logging

from pivovar import phases
from pivovar import config as cfg
try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


logging.basicConfig(level=logging.DEBUG)


def test_temp_ready():
    backend = MagicMock()
    backend.temp.return_value = cfg.REQ_TEMP
    phases.delay = MagicMock()
    phases.wash_the_keg(backend)
