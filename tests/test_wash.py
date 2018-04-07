from pivovar import wash
from pivovar import config as cfg
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

@patch('pivovar.wash.backend')
@patch('pivovar.wash.sched')
def test_temp_ready(backend, sched):
    backend.temp.return_value = cfg.REQ_TEMP
    wash.temp_ready()

