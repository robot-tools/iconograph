#!/usr/bin/python3

import argparse
import os
import subprocess
import sys
import tempfile


parser = argparse.ArgumentParser(description='iconograph fetcher')
parser.add_argument(
    '--cert',
    dest='cert',
    action='store',
    required=True)
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
    '--key',
    dest='key',
    action='store',
    required=True)
parser.add_argument(
    '--other-cert',
    dest='other_certs',
    action='append')
FLAGS = parser.parse_args()


def Exec(*args, **kwargs):
  print('+', args)
  subprocess.check_call(args, **kwargs)


def main():
  base = os.path.dirname(sys.argv[0])

  unsigned_manifest = os.path.join(FLAGS.image_dir, 'manifest.json.unsigned')
  signed_manifest = os.path.join(FLAGS.image_dir, 'manifest.json')

  with tempfile.NamedTemporaryFile(dir=FLAGS.image_dir, delete=False) as fh:
    try:
      Exec(
          os.path.join(base, 'build_manifest.py'),
          '--default-rollout', str(FLAGS.default_rollout),
          '--image-dir', FLAGS.image_dir,
          '--old-manifest', unsigned_manifest,
          stdout=fh)
      os.rename(fh.name, unsigned_manifest)
    except:
      os.unlink(fh.name)
      raise

  with tempfile.NamedTemporaryFile(dir=FLAGS.image_dir, delete=False) as fh, open(unsigned_manifest, 'r') as fh_in:
    try:
      args = [
          os.path.join(base, 'wrap_file.py'),
          '--cert', FLAGS.cert,
          '--key', FLAGS.key,
      ]
      for other_cert in FLAGS.other_certs or []:
        args.extend([
            '--other-cert', other_cert,
        ])
      Exec(
          *args,
          stdin=fh_in,
          stdout=fh)
      os.rename(fh.name, signed_manifest)
    except:
      os.unlink(fh.name)


if __name__ == '__main__':
  main()
