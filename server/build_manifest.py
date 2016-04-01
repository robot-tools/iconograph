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
    '--default-rollout',
    dest='default_rollout',
    action='store',
    type=int,
    default=0)
parser.add_argument(
    '--image-dir',
    dest='image_dir',
    action='store',
    required=True)
parser.add_argument(
    '--old-manifest',
    dest='old_manifest',
    action='store')
FLAGS = parser.parse_args()


class ManifestBuilder(object):

  _FILE_REGEX = re.compile('^(?P<timestamp>\d+)\.iso$')
  _BUF_SIZE = 2 ** 16

  def __init__(self, image_dir, old_manifest):
    self._image_dir = image_dir
    self._old_manifest = old_manifest

  def _Rollouts(self):
    if not self._old_manifest:
      return {}
    try:
      with open(self._old_manifest, 'r') as fh:
        parsed = json.load(fh)
        return dict(
            (image['timestamp'], image['rollout_‱'])
            for image in parsed['images'])
    except FileNotFoundError:
      return {}

  def BuildManifest(self):
    ret = {
        'timestamp': int(time.time()),
        'images': [],
    }
    rollouts = self._Rollouts()
    for filename in os.listdir(self._image_dir):
      match = self._FILE_REGEX.match(filename)
      if not match:
        continue
      timestamp = int(match.group('timestamp'))
      image = {
          'timestamp': timestamp,
          'rollout_‱': rollouts.get(timestamp, FLAGS.default_rollout),
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
    ret['images'].sort(key=lambda x: x['timestamp'], reverse=True)
    return ret


def main():
  builder = ManifestBuilder(FLAGS.image_dir, FLAGS.old_manifest)
  manifest = builder.BuildManifest()
  json.dump(manifest, sys.stdout, sort_keys=True, indent=4)
  sys.stdout.write('\n')


if __name__ == '__main__':
  main()
