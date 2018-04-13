import logging

from pivovar import wash
from pivovar import config as cfg
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch


logging.basicConfig(level=logging.DEBUG)


@patch('pivovar.wash.backend')
def test_temp_ready(backend):
    backend.temp.return_value = cfg.REQ_TEMP
    wash.temp_ready()
