import configparser as _configparser
import os.path
import pivovar
import sys


def _get_cfg():
    _cfg = _configparser.ConfigParser()
    pivovar_pkg_dirname = os.path.dirname(pivovar.__file__)
    _cfg.read_file(open(os.path.join(pivovar_pkg_dirname, 'pivovar.cfg')))
    return _cfg


sys.modules[__name__] = _get_cfg()
