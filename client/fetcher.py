#!/usr/bin/python3

import argparse
import codecs
import json
import hashlib
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import urllib.request
from OpenSSL import crypto


parser = argparse.ArgumentParser(description='iconograph fetcher')
parser.add_argument(
    '--base-url',
    dest='base_url',
    action='store',
    required=True)
parser.add_argument(
    '--ca-cert',
    dest='ca_cert',
    action='store',
    required=True)
parser.add_argument(
    '--image-dir',
    dest='image_dir',
    action='store',
    required=True)
FLAGS = parser.parse_args()


class Error(Exception):
  pass


class InvalidHash(Error):
  pass


class NoValidImage(Error):
  pass


class Fetcher(object):

  _BUF_SIZE = 2 ** 16
  _MAX_BP = 10000

  def __init__(self, base_url, ca_cert, image_dir):
    self._base_url = base_url
    self._ca_cert_path = ca_cert
    self._image_dir = image_dir

  def _VerifyChain(self, untrusted_certs, cert):
    tempdir = tempfile.mkdtemp()

    try:
      untrusted_path = os.path.join(tempdir, 'untrusted.pem')
      with open(untrusted_path, 'w') as fh:
        for cert_str in untrusted_certs:
          fh.write(cert_str)

      cert_path = os.path.join(tempdir, 'cert.pem')
      with open(cert_path, 'w') as fh:
        fh.write(cert)

      # Rely on pipe buffering to eat the stdout junk
      subprocess.check_call([
          'openssl', 'verify',
          '-CAfile', self._ca_cert_path,
          '-untrusted', untrusted_path,
          cert_path,
      ], stdout=subprocess.PIPE)
    finally:
      shutil.rmtree(tempdir)

  def _Unwrap(self, wrapped):
    self._VerifyChain(wrapped.get('other_certs', []), wrapped['cert'])

    cert = crypto.load_certificate(crypto.FILETYPE_PEM, wrapped['cert'])
    sig = codecs.decode(wrapped['sig'], 'hex')
    crypto.verify(
        cert,
        sig,
        wrapped['inner'].encode('utf8'),
        'sha256')

    return json.loads(wrapped['inner'])

  def _GetManifest(self):
    url = '%s/manifest.json' % (self._base_url)
    resp = urllib.request.urlopen(url).read().decode('utf8')
    return self._Unwrap(json.loads(resp))

  def _ChooseImage(self, manifest):
    hostname = socket.gethostname()
    hash_base = hashlib.sha256(hostname.encode('ascii'))
    for image in manifest['images']:
      hashobj = hash_base.copy()
      hashobj.update(struct.pack('!L', image['timestamp']))
      my_bp = struct.unpack('!I', hashobj.digest()[-4:])[0] % self._MAX_BP
      if my_bp < image['rollout_‱']:
        return image
    raise NoValidImage

  def _FetchImage(self, image):
    filename = '%d.iso' % (image['timestamp'])
    path = os.path.join(self._image_dir, filename)

    if os.path.exists(path):
      return

    url = '%s/%s' % (self._base_url, filename)
    print('Fetching:', url)
    resp = urllib.request.urlopen(url)

    hash_obj = hashlib.sha256()
    try:
      fh = tempfile.NamedTemporaryFile(dir=self._image_dir, delete=False)
      while True:
        data = resp.read(self._BUF_SIZE)
        if not data:
          break
        hash_obj.update(data)
        fh.write(data)
      if hash_obj.hexdigest() != image['hash']:
        raise InvalidHash
      os.rename(fh.name, path)
    except:
      os.unlink(fh.name)
      raise

  def _SetCurrent(self, image):
    filename = '%d.iso' % (image['timestamp'])
    path = os.path.join(self._image_dir, filename)
    current_path = os.path.join(self._image_dir, 'current')

    try:
      link = os.readlink(current_path)
      link_path = os.path.join(self._image_dir, link)
      if link_path == path:
        return
    except FileNotFoundError:
      pass

    print('Changing current link to:', path)
    temp_path = tempfile.mktemp(dir=self._image_dir)
    os.symlink(filename, temp_path)
    os.rename(temp_path, current_path)

  def Fetch(self):
    manifest = self._GetManifest()
    image = self._ChooseImage(manifest)
    self._FetchImage(image)
    self._SetCurrent(image)


def main():
  fetcher = Fetcher(FLAGS.base_url, FLAGS.ca_cert, FLAGS.image_dir)
  fetcher.Fetch()


if __name__ == '__main__':
  main()
