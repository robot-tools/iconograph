#!/usr/bin/python3

import argparse
import fetcher
import os
import shutil
import subprocess
import sys
import tempfile
import time
import update_grub


parser = argparse.ArgumentParser(description='iconograph image')
parser.add_argument(
    '--server',
    dest='server',
    action='store',
    required=True)
parser.add_argument(
    '--ca-cert',
    dest='ca_cert',
    action='store',
    required=True)
parser.add_argument(
    '--https-ca-cert',
    dest='https_ca_cert',
    action='store',
    required=True)
parser.add_argument(
    '--https-client-cert',
    dest='https_client_cert',
    action='store',
    required=True)
parser.add_argument(
    '--https-client-key',
    dest='https_client_key',
    action='store',
    required=True)
parser.add_argument(
    '--image-type',
    dest='image_type',
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

  def __init__(self, device, persistent_percent):
    self._device = device
    self._persistent_percent = persistent_percent
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

  def _GetFetcher(self, image_dir):
    return fetcher.Fetcher(
        'https://%s/image/%s' % (FLAGS.server, FLAGS.image_type),
        FLAGS.ca_cert,
        image_dir,
        FLAGS.https_ca_cert,
        FLAGS.https_client_cert,
        FLAGS.https_client_key)

  def _UpdateGrub(self, root, image_dir):
    boot_dir = os.path.join(root, 'isodevice')

    update = update_grub.GrubUpdater(
        image_dir,
        boot_dir)
    update.Update()

  def _FetchImages(self, root):
    image_dir = os.path.join(root, 'iconograph')
    os.mkdir(image_dir)

    fetch = self._GetFetcher(image_dir)
    fetch.Fetch()

    return image_dir

  def _Image(self):
    self._PartitionAndMkFS()
    root = self._MountBoot()
    self._InstallGrub(root)
    image_dir = self._FetchImages(root)
    self._UpdateGrub(root, image_dir)

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
  imager = Imager(
      FLAGS.device,
      FLAGS.persistent_percent)
  imager.Image()


if __name__ == '__main__':
  main()
