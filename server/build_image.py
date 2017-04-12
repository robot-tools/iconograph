#!/usr/bin/python3

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time


parser = argparse.ArgumentParser(description='iconograph build_image')
parser.add_argument(
    '--arch',
    dest='arch',
    action='store',
    default='amd64')
parser.add_argument(
    '--archive',
    dest='archive',
    action='store',
    default='http://archive.ubuntu.com/ubuntu')
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
parser.add_argument(
    '--kernel-arg',
    dest='kernel_args',
    action='append')
parser.add_argument(
    '--module',
    dest='modules',
    action='append')
parser.add_argument(
    '--release',
    dest='release',
    action='store',
    required=True)
parser.add_argument(
    '--post-module-shell',
    dest='post_module_shell',
    action='store_true',
    default=False)
parser.add_argument(
    '--pre-module-shell',
    dest='pre_module_shell',
    action='store_true',
    default=False)
parser.add_argument(
    '--source-iso',
    dest='source_iso',
    action='store',
    required=True)
parser.add_argument(
    '--volume-id',
    dest='volume_id',
    action='store')
FLAGS = parser.parse_args()


class ImageBuilder(object):

  _BASE_PACKAGES = {
    'devscripts',
    'nano',
    'iputils-ping',
    'linux-firmware',
    'ubuntu-minimal',
    'ubuntu-standard',
    'user-setup',
  }

  _RELEASE_PACKAGES = {
    'trusty': {
      'linux-firmware-nonfree',
    },
  }

  _SUITES = {
    '%(release)s',
    '%(release)s-updates',
  }

  _SECTIONS = {
    'main',
    'restricted',
    'universe',
    'multiverse',
  }

  _DIVERSIONS = {
    '/sbin/initctl': '/bin/true',
  }

  _ISO_COPIES = {
    'grub.cfg': 'boot/grub/grub.cfg',
    'loopback.cfg': 'boot/grub/loopback.cfg',
  }

  def __init__(self, source_iso, image_dir, image_type, archive, arch, release, modules, kernel_args, volume_id=None):
    self._source_iso = source_iso
    self._image_dir = image_dir
    self._image_type = image_type
    self._archive = archive
    self._arch = arch
    self._release = release
    self._modules = modules or []
    self._kernel_args = kernel_args or []
    self._volume_id = volume_id

    self._ico_server_path = os.path.dirname(sys.argv[0])

  def _Exec(self, *args, **kwargs):
    print('+', args)
    subprocess.check_call(args, **kwargs)

  def _ExecChroot(self, chroot_path, *args, **kwargs):
    self._Exec('chroot', chroot_path, *args, **kwargs)

  def _CreateRoot(self, timestamp):
    root = tempfile.mkdtemp()
    self._rmtree.append(root)
    self._Exec(
        'mount',
        '--types', 'tmpfs',
        'none',
        root)
    self._umount.append(root)
    return root

  def _MountProc(self, chroot_path):
    path = os.path.join(chroot_path, 'proc')
    self._Exec(
        'mount',
        '--types', 'proc',
        'none',
        path)
    self._umount.append(path)
    return path

  def _Debootstrap(self, root):
    path = os.path.join(root, 'chroot')
    os.mkdir(path)
    self._Exec(
        'debootstrap',
        '--variant=buildd',
        '--arch', self._arch,
        self._release,
        path,
        self._archive)
    return path

  def _CreateUnion(self, root):
    iso_path = os.path.join(root, 'iso')
    os.mkdir(iso_path)
    self._Exec(
        'mount',
        '--options', 'loop,ro',
        self._source_iso,
        iso_path)
    self._umount.append(iso_path)

    upper_path = os.path.join(root, 'upper')
    os.mkdir(upper_path)

    work_path = os.path.join(root, 'work')
    os.mkdir(work_path)

    union_path = os.path.join(root, 'union')
    os.mkdir(union_path)
    self._Exec(
        'mount', 
        '--types', 'overlayfs',
        '--options', 'lowerdir=%s,upperdir=%s,workdir=%s' % (iso_path, upper_path, work_path),
        'none',
        union_path)
    self._umount.append(union_path)

    return union_path

  def _FixSourcesList(self, chroot_path):
    path = os.path.join(chroot_path, 'etc', 'apt', 'sources.list')
    with open(path, 'w') as fh:
      for suite in self._SUITES:
        fh.write('deb %(archive)s %(suite)s %(sections)s\n' % {
          'archive': self._archive,
          'suite': suite % {
            'release': self._release,
          },
          'sections': ' '.join(self._SECTIONS),
        })

  def _AddDiversions(self, chroot_path):
    for source, dest in self._DIVERSIONS.items():
      self._ExecChroot(
          chroot_path,
          'dpkg-divert',
          '--local',
          '--rename',
          '--add',
          source)
      self._ExecChroot(
          chroot_path,
          'ln',
          '--symbolic',
          '--force',
          dest,
          source)
    with open(os.path.join(chroot_path, 'usr', 'sbin', 'policy-rc.d'), 'w') as fh:
      fh.write('#!/bin/sh\n')
      fh.write('exit 101\n')
      os.fchmod(fh.fileno(), 0o744)

  def _InstallPackages(self, chroot_path):
    env = os.environ.copy()
    env['DEBIAN_FRONTEND'] = 'noninteractive'

    self._ExecChroot(
        chroot_path,
        'apt-get',
        'update',
        env=env)
    self._ExecChroot(
        chroot_path,
        'apt-get',
        'install',
        '--assume-yes',
        *(self._BASE_PACKAGES | self._RELEASE_PACKAGES.get(self._release, set())),
        env=env)

  def _WriteVersion(self, chroot_path, timestamp):
    with open(os.path.join(chroot_path, 'etc', 'iconograph.json'), 'w') as fh:
      info = {
        'image_type': self._image_type,
        'timestamp': timestamp,
      }
      if self._volume_id:
        info['volume_id'] = self._volume_id
      json.dump(info, fh, sort_keys=True, indent=4)
      fh.write('\n')

  def _RunModules(self, chroot_path):
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), 'module_lib'))

    for module in self._modules:
      self._Exec(
          '%(module)s --chroot-path=%(chroot_path)s' % {
            'module': module,
            'chroot_path': chroot_path,
          },
          shell=True,
          env=env)

  def _CleanPackages(self, chroot_path):
    self._ExecChroot(
        chroot_path,
        'apt-get',
        'clean')

  def _RemoveDiversions(self, chroot_path):
    for source in self._DIVERSIONS:
      self._ExecChroot(
          chroot_path,
          'rm',
          source)
      self._ExecChroot(
          chroot_path,
          'dpkg-divert',
          '--rename',
          '--remove',
         source)
    os.unlink(os.path.join(chroot_path, 'usr', 'sbin', 'policy-rc.d'))

  def _Unmount(self, path):
    self._Exec(
        'umount',
        path)
    self._umount.remove(path)

  def _Squash(self, chroot_path, union_path):
    self._Exec(
        'mksquashfs',
        chroot_path,
        os.path.join(union_path, 'casper', 'filesystem.squashfs'),
        '-noappend')

  def _CopyISOFiles(self, union_path):
    for source, dest in self._ISO_COPIES.items():
      source_path = os.path.join(self._ico_server_path, 'iso_files', source)
      dest_path = os.path.join(union_path, dest)
      with open(source_path, 'r') as source_fh, open(dest_path, 'w') as dest_fh:
        for line in source_fh:
          dest_fh.write(line.replace('$KERNEL_ARGS', ' '.join(self._kernel_args)))

  def _CreateISO(self, union_path, timestamp):
    dest_iso = os.path.join(self._image_dir, self._image_type, '%d.iso' % timestamp)
    args = [
        '--output=%s' % dest_iso,
        '--',
    ]
    if self._volume_id:
      args.extend(['-V', self._volume_id])
    args.append(union_path)

    self._Exec('grub-mkrescue', *args)
    return dest_iso

  def _BuildImage(self):
    timestamp = int(time.time())
    root = self._CreateRoot(timestamp)
    print('Building image in:', root)

    chroot_path = self._Debootstrap(root)
    union_path = self._CreateUnion(root)
    proc_path = self._MountProc(chroot_path)
    self._FixSourcesList(chroot_path)
    self._AddDiversions(chroot_path)
    self._InstallPackages(chroot_path)
    self._WriteVersion(chroot_path, timestamp)
    if FLAGS.pre_module_shell:
      self._Exec('bash', cwd=root)
    self._RunModules(chroot_path)
    self._CleanPackages(chroot_path)
    self._RemoveDiversions(chroot_path)
    if FLAGS.post_module_shell:
      self._Exec('bash', cwd=root)
    self._Unmount(proc_path)
    self._Squash(chroot_path, union_path)
    self._CopyISOFiles(union_path)
    iso_path = self._CreateISO(union_path, timestamp)

    print("""

========================
Successfully built image:
\033[91m%s\033[00m
========================
""" % iso_path)

  def BuildImage(self):
    self._umount = []
    self._rmtree = []
    try:
      self._BuildImage()
    finally:
      for path in reversed(self._umount):
        self._Exec('umount', path)
      for path in self._rmtree:
        shutil.rmtree(path)


def main():
  builder = ImageBuilder(
      FLAGS.source_iso,
      FLAGS.image_dir,
      FLAGS.image_type,
      FLAGS.archive,
      FLAGS.arch,
      FLAGS.release,
      FLAGS.modules,
      FLAGS.kernel_args,
      FLAGS.volume_id)
  builder.BuildImage()


if __name__ == '__main__':
  main()
