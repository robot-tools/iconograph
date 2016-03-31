#!/usr/bin/python3

import argparse
import os
import sys


parser = argparse.ArgumentParser(description='iconograph update_grub')
parser.add_argument(
    '--boot-dir',
    dest='boot_dir',
    action='store',
    required=True)
parser.add_argument(
    '--image-dir',
    dest='image_dir',
    action='store',
    required=True)
FLAGS = parser.parse_args()


class GrubUpdater(object):

  def __init__(self, image_dir, boot_dir):
    self._image_dir = image_dir
    self._boot_dir = boot_dir

    assert self._image_dir.startswith(self._boot_dir)

    self._image_path = '/' + os.path.relpath(self._image_dir, self._boot_dir)

  def Update(self):
    for filename in os.listdir(self._image_dir):
      if not filename.endswith('.iso'):
        continue
      sys.stdout.write("""
menuentry "%(image_filename)s" {
  search --no-floppy --file --set=root %(image_path)s/%(image_filename)s
  iso_path="%(image_path)s/%(image_filename)s"
  export iso_path
  loopback loop "%(image_path)s/%(image_filename)s"
  set root=(loop)
  configfile /boot/grub/loopback.cfg
}
""" % {
        'image_filename': filename,
        'image_path': self._image_path,
      })


def main():
  updater = GrubUpdater(FLAGS.image_dir, FLAGS.boot_dir)
  updater.Update()


if __name__ == '__main__':
  main()
