from contextlib import contextmanager
import logging
import os
import re
import subprocess
import requests
import yaml


VERSIONS_URL = (
    "https://raw.githubusercontent.com/jaryn/pivovar-versions/master/"
    "v2018-08-07"
)


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


def get_record(versions_url, machine_id):
    resp = requests.get(versions_url)
    versions = yaml.load(resp.text)
    return versions[machine_id]


def update(versions_url):
    path = os.path.dirname(__file__)
    logging('Updating repo on path: %s.', path)

    hostnamectl = subprocess.check_output('hostnamectl')
    machine_id = dict(hostnamectl_values(hostnamectl))['Machine ID']
    record = get_record(versions_url, machine_id)
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
    import argparse
    parser = argparse.ArgumentParser(description='Wash some kegs.')
    parser.add_argument('versions_url', dest='branch', action='store',
                        default=VERSIONS_URL,
                        help='URL of versions file.')

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    update(args.versions_url)


if __name__ == '__main__':
    main()
