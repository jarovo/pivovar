from pivovar import set_aliases_m103

from .themock import patch

unipi_address = 'fake_address'


@patch('pivovar.set_aliases_m103.requests')
def test_check_m103(requests_mock):
    requests_mock.get.return_value.json.return_value = {
        'dev': 'neuron',
        'model': 'M103',
    }
    set_aliases_m103.check_m103(unipi_address)


@patch('pivovar.set_aliases_m103.requests')
def test_check_null_aliases(requests_mock):
    set_aliases_m103.null_aliases(unipi_address)


@patch('pivovar.set_aliases_m103.requests')
def test_check_store_to_nvmem(requests_mock):
    set_aliases_m103.store_to_nvmem(unipi_address)
