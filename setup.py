#!/usr/bin/env python
import os
import subprocess
from setuptools import setup


# https://stackoverflow.com/a/37906830/1950100
def create_mo_files():
    data_files = []
    localedir = 'pivovar/translations'
    po_dirs = [
        localedir + '/' + l + '/LC_MESSAGES/'
        for l in next(os.walk(localedir))[1]
    ]
    for d in po_dirs:
        mo_files = []
        po_files = [
            f for f in next(os.walk(d))[2] if os.path.splitext(f)[1] == '.po'
        ]
        for po_file in po_files:
            filename, extension = os.path.splitext(po_file)
            mo_file = filename + '.mo'
            msgfmt_cmd = 'msgfmt {} -o {}'.format(d + po_file, d + mo_file)
            subprocess.call(msgfmt_cmd, shell=True)
            mo_files.append(d + mo_file)
        data_files.append((d, mo_files))
    return data_files


setup(setup_requires=['pbr'], pbr=True, data_files=create_mo_files())
