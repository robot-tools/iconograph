#!/usr/bin/python3

import argparse
import hashlib
import json
import os
import re
import sys
import time


parser = argparse.ArgumentParser(description='iconograph fetcher')
parser.add_argument(
    '--image-dir',
    dest='image_dir',
    action='store',
    required=True)
parser.add_argument(
    '--image-type',
    dest='image_type',
    action='store',
    required=True)
FLAGS = parser.parse_args()


class ManifestBuilder(object):

  _FILE_REGEX = '^%(image_type)s\.(?P<timestamp>\d+)\.iso$'
  _BUF_SIZE = 2 ** 16

  def __init__(self, image_dir, image_type):
    self._image_dir = image_dir
    self._file_regex = re.compile(self._FILE_REGEX % {
        'image_type': image_type,
    })

  def BuildManifest(self):
    ret = {
        'timestamp': int(time.time()),
        'images': [],
    }
    for filename in os.listdir(self._image_dir):
      match = self._file_regex.match(filename)
      if not match:
        continue
      image = {
          'timestamp': match.group('timestamp'),
      }
      with open(os.path.join(self._image_dir, filename), 'rb') as fh:
        hash_obj = hashlib.sha256()
        while True:
          data = fh.read(self._BUF_SIZE)
          if not data:
            break
          hash_obj.update(data)
        image['hash'] = hash_obj.hexdigest()
      ret['images'].append(image)
    return ret


builder = ManifestBuilder(FLAGS.image_dir, FLAGS.image_type)
manifest = builder.BuildManifest()
json.dump(manifest, sys.stdout, indent=4)
sys.stdout.write('\n')
