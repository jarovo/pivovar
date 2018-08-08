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


def hostnamectl_values(hostnamectl):
    for line in hostnamectl.split('\n'):
        m = re.match(r'^\s*(.+):\s*(.+)$', line)
        if m:
            yield m.group(1), m.group(2)


def get_record(machine_id):
    url = (
        "https://raw.githubusercontent.com/jaryn/pivovar-versions/master/"
        "v2018-08-07"
    )
    resp = requests.get(url)
    versions = yaml.load(resp.text)
    return versions[machine_id]


def update():
    path = os.getcwd()
    hostnamectl = subprocess.check_output('hostnamectl')
    machine_id = dict(hostnamectl_values(hostnamectl))['Machine ID']
    path = os.path.dirname(__file__)
    record = get_record(machine_id)
    if record['packager'] == 'git':
        branch = record['branch']
        repo = record['repo']
        with chwd(path):
            checkout(repo, branch)
            install()


def checkout(repo, branch):
    subprocess.check_call(["git", "fetch", repo, branch])
    subprocess.check_call(["git", "checkout", 'FETCH_HEAD'])


def install():
    subprocess.check_call(
        ["pip", "install", "--force-reinstall", "-e", "."])


def main():
    update()


if __name__ == '__main__':
    main()
