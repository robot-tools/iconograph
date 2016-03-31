#!/usr/bin/python3

import argparse
import os
import string
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

  _HOTKEYS = string.digits + string.ascii_letters

  def __init__(self, image_dir, boot_dir):
    self._image_dir = image_dir
    self._boot_dir = boot_dir

    assert self._image_dir.startswith(self._boot_dir)

    self._image_path = '/' + os.path.relpath(self._image_dir, self._boot_dir)

  def Update(self):
    current = os.readlink(os.path.join(self._image_dir, 'current'))

    sys.stdout.write("""
set timeout=5
set default=%(default_image_filename)s
""" % {
      'default_image_filename': os.path.basename(current),
    })

    files = []
    for filename in os.listdir(self._image_dir):
      if not filename.endswith('.iso'):
        continue
      files.append(filename)

    for i, filename in enumerate(sorted(files, reverse=True)):
      sys.stdout.write("""
menuentry "%(image_filename)s" --hotkey=%(hotkey)s {
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
        'hotkey': self._HOTKEYS[i],
      })


def main():
  updater = GrubUpdater(FLAGS.image_dir, FLAGS.boot_dir)
  updater.Update()


if __name__ == '__main__':
  main()
