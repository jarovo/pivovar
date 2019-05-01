import configparser as _configparser
import sys


def _get_cfg():
    _cfg = _configparser.ConfigParser()
    _cfg.read_file(open('pivovar.cfg'))
    return _cfg


sys.modules[__name__] = _get_cfg()
