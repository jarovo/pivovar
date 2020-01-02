import logging
import requests
import argparse

ALIASES = {
    ('input', '1_01'): 'al_fuse_ok',
    ('input', '1_02'): 'al_total_stop',
    ('input', '1_03'): 'al_keg_present',
    ('input', '1_04'): '',
    ('input', '2_01'): 'al_keg_50l',
    ('input', '2_02'): 'al_aux_wash',
    ('input', '2_03'): '',
    ('input', '2_04'): '',
    ('input', '2_05'): '',
    ('input', '2_06'): '',
    ('input', '2_07'): '',
    ('input', '2_08'): '',
    ('output', '1_01'): 'al_error_lamp',
    ('output', '1_02'): 'al_ready_lamp',
    ('output', '1_03'): 'al_waiting_for_input_lamp',
    ('output', '1_04'): '',
    ('ao', '1_01'): '',
    ('ai', '1_01'): '',
    ('led', '1_01'): '',
    ('led', '1_02'): '',
    ('led', '1_03'): '',
    ('led', '1_04'): '',
    ('uart', '1_01'): '',
    ('relay', '2_01'): 'al_pump',
    ('relay', '2_02'): 'al_air',
    ('relay', '2_03'): 'al_water_or_lye',
    ('relay', '2_04'): 'al_co2',
    ('relay', '2_05'): 'al_cold_water',
    ('relay', '2_06'): 'al_drain_or_recirculation',
    ('relay', '2_07'): 'al_drain',
    ('relay', '2_08'): '',
}


def null_aliases(address):
    for (dev, dev_id) in ALIASES.keys():
        set_alias(address, dev, dev_id, '')


def set_aliases(address):
    for (dev, dev_id), alias in ALIASES.items():
        set_alias(address, dev, dev_id, alias)


def set_alias(address, dev, dev_id, alias):
    logging.info('Setting alias for %s %s: %s', dev, dev_id, alias)
    url = 'http://{address}/rest/{dev}/{dev_id}'.format(
        address=address, dev=dev, dev_id=dev_id
    )
    resp = requests.post(url, data={'alias': alias})
    resp = resp.json()
    unipi_alias = resp['result']['alias'] if alias else ''
    assert unipi_alias == alias, 'Failed to set {}. Current value: {}'.format(
        alias, unipi_alias
    )
    assert resp['success']


def store_to_nvmem(address):
    url = 'http://{address}/rest/wd/1_01'.format(address=address)
    resp = requests.post(url, data={'nv_save': 1})
    resp = resp.json()
    assert resp['success']
    url = 'http://{address}/rest/wd/2_01'.format(address=address)
    resp = requests.post(url, data={'nv_save': 1})
    resp = resp.json()
    assert resp['success']
    logging.info('Saved to flash.')


def check_m103(address):
    url = 'http://{address}/rest/neuron/1'.format(address=address)
    resp = requests.get(url)
    resp = resp.json()
    dev = resp['dev']
    model = resp['model']
    assert dev == 'neuron', 'The device is not neuron, but {}'.format(dev)
    assert model == 'M103', 'The device is not M103, but {}'.format(model)


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='UniPi M103 initial setup')
    parser.add_argument(
        'unipi_address', type=str, help='Address to of UniPi M103.'
    )
    args = parser.parse_args()

    check_m103(args.unipi_address)
    null_aliases(args.unipi_address)
    set_aliases(args.unipi_address)
    store_to_nvmem(args.unipi_address)


if __name__ == '__main__':
    main()
