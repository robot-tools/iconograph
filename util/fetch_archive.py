#!/usr/bin/python3

import argparse
import os
import requests
import shutil
import subprocess


parser = argparse.ArgumentParser(description='iconograph fetch_archive')
parser.add_argument(
    '--dest-dir',
    dest='dest_dir',
    action='store',
    default='.')
parser.add_argument(
    '--https-ca-cert',
    dest='https_ca_cert',
    action='store')
parser.add_argument(
    '--https-client-cert',
    dest='https_client_cert',
    action='store')
parser.add_argument(
    '--https-client-key',
    dest='https_client_key',
    action='store')
parser.add_argument(
    '--url',
    dest='url',
    action='store',
    required=True)
FLAGS = parser.parse_args()


class ArchiveFetcher(object):

  _BUF_SIZE = 2 ** 16

  def __init__(self, https_ca_cert, https_client_cert, https_client_key):
    self._session = requests.Session()
    if https_ca_cert:
      self._session.verify = https_ca_cert
    if https_client_cert and https_client_key:
      self._session.cert = (https_client_cert, https_client_key)

  def Fetch(self, url, dest_dir='.'):
    resp = self._session.get(url, stream=True)

    tar = subprocess.Popen(
        ['tar', '--extract', '--verbose'],
        stdin=subprocess.PIPE,
        cwd=dest_dir)
    for data in resp.iter_content(self._BUF_SIZE):
      tar.stdin.write(data)
    tar.wait()


def main():
  fetcher = ArchiveFetcher(
      FLAGS.https_ca_cert,
      FLAGS.https_client_cert,
      FLAGS.https_client_key)
  fetcher.Fetch(
      FLAGS.url,
      FLAGS.dest_dir)


if __name__ == '__main__':
  main()
