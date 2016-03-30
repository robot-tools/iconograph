#!/usr/bin/python3

import argparse
import codecs
import json
from OpenSSL import crypto
import sys


parser = argparse.ArgumentParser(description='iconograph wrap_file')
parser.add_argument(
    '--cert',
    dest='cert',
    action='store',
    required=True)
parser.add_argument(
    '--key',
    dest='key',
    action='store',
    required=True)
parser.add_argument(
    '--other-cert',
    dest='other_certs',
    action='store',
    nargs='*')
FLAGS = parser.parse_args()


class Wrapper(object):

  def __init__(self, key, cert, other_certs):
    with open(key, 'r') as fh:
      self._key = crypto.load_privatekey(crypto.FILETYPE_PEM, fh.read())
    with open(cert, 'r') as fh:
      self._cert_str = fh.read()
      self._cert = crypto.load_certificate(crypto.FILETYPE_PEM, self._cert_str)
    self._other_cert_strs = []
    for path in (other_certs or []):
      with open(path, 'r') as fh:
        self._other_cert_strs.append(fh.read())

  def Wrap(self, instr):
    inbytes = instr.encode('utf8')
    return {
        'cert': self._cert_str,
        'other_certs': self._other_cert_strs,
        'sig': codecs.encode(crypto.sign(self._key, inbytes, 'sha256'), 'hex').decode('ascii'),
        'inner': instr,
    }


def main():
  wrapper = Wrapper(FLAGS.key, FLAGS.cert, FLAGS.other_certs)
  wrapped = wrapper.Wrap(sys.stdin.read())
  json.dump(wrapped, sys.stdout, sort_keys=True, indent=4)
  sys.stdout.write('\n')


if __name__ == '__main__':
  main()
