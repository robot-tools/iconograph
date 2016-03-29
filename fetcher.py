#!/usr/bin/python3
# coding=utf8

import argparse
import json
import hashlib
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
	'--image-type',
	dest='image_type',
	action='store',
	required=True)
FLAGS = parser.parse_args()


class Fetcher(object):

  _MAX_BP = 10000

  def __init__(self, base_url, image_type):
    self._base_url = base_url
    self._image_type = image_type

  def _GetManifest(self):
    url = '%s/%s.manifest.json' % (self._base_url, self._image_type)
    return json.loads(urllib.request.urlopen(url).read().decode('utf8'))

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
    image = self._ChooseImage(manifest)
    print(image)


fetcher = Fetcher(FLAGS.base_url, FLAGS.image_type)
fetcher.Fetch()
