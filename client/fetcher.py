#!/usr/bin/python3

import codecs
import json
import hashlib
import os
import re
import requests
import shutil
import socket
import struct
import subprocess
import tempfile
from OpenSSL import crypto


class Error(Exception):
  pass


class InvalidHash(Error):
  pass


class NoValidImage(Error):
  pass


class ManifestTimeRegressed(Error):
  pass


class Fetcher(object):

  _BUF_SIZE = 2 ** 16
  _MAX_BP = 10000
  _FILE_REGEX = re.compile('^(?P<timestamp>\d+)\.iso$')

  def __init__(self, base_url, ca_cert, image_dir, https_ca_cert, https_client_cert, https_client_key):
    self._base_url = base_url
    self._ca_cert_path = ca_cert
    self._image_dir = image_dir
    self._session = requests.Session()
    if https_ca_cert:
      self._session.verify = https_ca_cert
    if https_client_cert and https_client_key:
      self._session.cert = (https_client_cert, https_client_key)

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
    resp = self._session.get(url)
    unwrapped = self._Unwrap(resp.json())
    self._ValidateManifest(unwrapped)
    return unwrapped

  def _ValidateManifest(self, new_manifest):
    path = os.path.join(self._image_dir, 'manifest.json')
    try:
      with open(path, 'r') as fh:
        old_manifest = json.load(fh)

      # This checks for replay of an old manifest. Injecting an older manifest
      # could allow an attacker to cause us to revert to an older image with
      # security issues. Manifest timestamps are therefor required to always
      # increase.
      if old_manifest['timestamp'] > new_manifest['timestamp']:
        raise ManifestTimeRegressed
    except FileNotFoundError:
      pass

    with open(path, 'w') as fh:
      json.dump(new_manifest, fh, indent=4)

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
    print('Fetching:', url, flush=True)
    resp = self._session.get(url, stream=True)

    hash_obj = hashlib.sha256()
    try:
      fh = tempfile.NamedTemporaryFile(dir=self._image_dir, delete=False)
      for data in resp.iter_content(self._BUF_SIZE):
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

    print('Changing current link to:', filename, flush=True)
    temp_path = tempfile.mktemp(dir=self._image_dir)
    os.symlink(filename, temp_path)
    os.rename(temp_path, current_path)

  def Fetch(self):
    manifest = self._GetManifest()
    image = self._ChooseImage(manifest)
    self._FetchImage(image)
    self._SetCurrent(image)

  def DeleteOldImages(self, max_images=5):
    if not max_images:
      return
    images = []
    for filename in os.listdir(self._image_dir):
      match = self._FILE_REGEX.match(filename)
      if not match:
        continue
      images.append((int(match.group('timestamp')), filename))
    images.sort(reverse=True)
    for timestamp, filename in images[max_images:]:
      print('Deleting old image:', filename, flush=True)
      path = os.path.join(self._image_dir, filename)
      os.unlink(path)
