from pivovar import unipi

from .themock import patch


@patch('pivovar.unipi.Client')
def test_check(rpc_client_mock):
    backend = unipi.UniPiJSONRPC('someaddress')
    backend.check()
