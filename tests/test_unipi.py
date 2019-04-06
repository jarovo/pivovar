from pivovar import phases
from pivovar import unipi

from .themock import patch


@patch('pivovar.unipi.Client')
def test_check(rpc_client_mock):
    backend = unipi.UniPiJSONRPC('someaddress')
    backend.server.sensor_get.return_value = (
        80.2, False, 1554587741.331581, 15)
    phases.check(backend)
