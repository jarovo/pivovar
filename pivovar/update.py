from contextlib import contextmanager
import re
import os
import subprocess
import requests
import yaml


@contextmanager
def chwd(directory):
    prev_wd = os.getcwd()
    os.chdir(directory)
    yield
    os.chdir(prev_wd)


def machine_id(hostnamctl):
    return re.match('Machine ID:*\s(+\S)').group(1)


def get_version():
    url = (
        "https://raw.githubusercontent.com/jaryn/pivovar-versions/master/"
        "v2018-08-07"
    )
    hostnamectl = subprocess.check_output('hostnamectl')
    machine_id = machine_id(hostnamectl)

    resp = requests.get(url)
    versions = yaml.loads(resp)
    version = versions.get(machine_id)


def update(branch="v1.0"):
    path = os.getcwd()
    with chwd(path):
        subprocess.check_call(["git", "fetch", "origin"])
        subprocess.check_call(["git", "checkout", "origin/" + branch])
        subprocess.check_call(["pip", "install", "--force-reinstall", "-e", "."])

