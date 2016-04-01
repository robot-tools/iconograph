#!/usr/bin/python3

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time


parser = argparse.ArgumentParser(description='iconograph image')
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
    '--device',
    dest='device',
    action='store',
    required=True)
parser.add_argument(
    '--persistent-percent',
    dest='persistent_percent',
    action='store',
    type=int,
    default=0)
FLAGS = parser.parse_args()


class Imager(object):

  def __init__(self, device, persistent_percent, base_url, ca_cert):
    self._device = device
    self._persistent_percent = persistent_percent
    self._base_url = base_url
    self._ca_cert = ca_cert

    self._icon_path = os.path.dirname(sys.argv[0])

  def _Exec(self, *args, **kwargs):
    print('+', args)
    subprocess.check_call(args, **kwargs)

  def _PartDev(self, part_num):
    time.sleep(1)
    args = {
      'device': self._device,
      'part': part_num,
    }
    options = [
      '%(device)s%(part)d' % args,
      '%(device)sp%(part)d' % args,
    ]
    while True:
      for option in options:
        if os.path.exists(option):
          return option

  def _PartitionAndMkFS(self):
    self._Exec(
        'parted',
        '--script',
        self._device,
        'mklabel', 'msdos')

    boot_stop = '%d%%' % (100 - self._persistent_percent)
    self._Exec(
        'parted',
        '--script',
        '--align', 'optimal',
        self._device,
        'mkpart', 'primary', 'ext4', '0%', boot_stop)
    self._Exec(
        'mkfs.ext4',
        '-L', 'BOOT',
        '-F',
        self._PartDev(1))

    if self._persistent_percent:
      self._Exec(
          'parted',
          '--script',
          '--align', 'optimal',
          self._device,
          'mkpart', 'primary', 'ext4', boot_stop, '100%')
      self._Exec(
          'mkfs.ext4',
          '-L', 'PERSISTENT',
          '-F',
          self._PartDev(2))

  def _MountBoot(self):
    root = tempfile.mkdtemp()
    self._rmtree.append(root)

    self._Exec(
        'mount',
        self._PartDev(1),
        root)
    self._umount.append(root)

    return root

  def _InstallGrub(self, root):
    self._Exec(
        'grub-install',
        '--boot-directory', root,
        self._device)

  def _FetchImages(self, root):
    image_path = os.path.join(root, 'iconograph')
    os.mkdir(image_path)

    fetcher = os.path.join(self._icon_path, '..', 'client', 'fetcher.py')

    self._Exec(
        fetcher,
        '--image-dir', image_path,
        '--base-url', self._base_url,
        '--ca-cert', self._ca_cert)

    return image_path

  def _CreateGrubCfg(self, root, image_path):
    grub_cfg_path = os.path.join(root, 'grub', 'grub.cfg')

    update_grub = os.path.join(self._icon_path, '..', 'client', 'update_grub.py')

    with open(grub_cfg_path, 'w') as fh:
      self._Exec(
          update_grub,
          '--image-dir', image_path,
          '--boot-dir', root,
          stdout=fh)

  def _Image(self):
    self._PartitionAndMkFS()
    root = self._MountBoot()
    self._InstallGrub(root)
    image_path = self._FetchImages(root)
    self._CreateGrubCfg(root, image_path)

  def Image(self):
    self._umount = []
    self._rmtree = []
    try:
      self._Image()
    finally:
      for path in reversed(self._umount):
        self._Exec('umount', path)
      for path in self._rmtree:
        shutil.rmtree(path)


def main():
  imager = Imager(FLAGS.device, FLAGS.persistent_percent, FLAGS.base_url, FLAGS.ca_cert)
  imager.Image()


if __name__ == '__main__':
  main()
