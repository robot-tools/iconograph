#!/usr/bin/python3

import argparse
import json
import hashlib
from OpenSSL import crypto
import socket
import struct
import urllib.request


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
    '--image-type',
    dest='image_type',
    action='store',
    required=True)
FLAGS = parser.parse_args()


class Fetcher(object):

  _MAX_BP = 10000

  def __init__(self, base_url, image_type, ca_cert):
    self._base_url = base_url
    self._image_type = image_type
    with open(ca_cert, 'r') as fh:
      self._ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, fh.read())

  def _Unwrap(self, wrapped):
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, wrapped['cert'])
    crypto.verify(
        cert,
        wrapped['sig'].encode('ascii'),
        wrapped['inner'].encode('ascii'),
        'sha256')

  def _GetManifest(self):
    url = '%s/%s.manifest.json' % (self._base_url, self._image_type)
    resp = urllib.request.urlopen(url).read().decode('utf8')
    return self._Unwrap(json.loads(resp))

  def _ChooseImage(self, manifest):
    hostname = socket.gethostname()
    hash_base = hashlib.sha256(hostname.encode('ascii'))
    for image in manifest:
      hashobj = hash_base.copy()
      hashobj.update(struct.pack('!L', image['timestamp']))
      my_bp = struct.unpack('!I', hashobj.digest()[-4:])[0] % self._MAX_BP
      if my_bp < image['rollout_‱']:
        return image

  def Fetch(self):
    manifest = self._GetManifest()
    #image = self._ChooseImage(manifest)
    #print(image)


fetcher = Fetcher(FLAGS.base_url, FLAGS.image_type, FLAGS.ca_cert)
fetcher.Fetch()
