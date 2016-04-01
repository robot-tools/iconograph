#!/usr/bin/python3

import argparse
import os
import shutil
import stat
import subprocess
import sys
import tempfile


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
    '--dest-iso',
    dest='dest_iso',
    action='store',
    required=True)
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
    '--shell',
    dest='shell',
    action='store_true',
    default=False)
parser.add_argument(
    '--source-iso',
    dest='source_iso',
    action='store',
    required=True)
FLAGS = parser.parse_args()


class ImageBuilder(object):

  _BASE_PACKAGES = [
    'devscripts',
    'nano',
    'iputils-ping',
    'linux-firmware',
    'linux-firmware-nonfree',
    'openssh-server',
    'ubuntu-minimal',
    'ubuntu-standard',
    'user-setup',
  ]

  _SUITES = [
    '%(release)s',
    '%(release)s-updates',
  ]

  _SECTIONS = [
    'main',
    'restricted',
    'universe',
    'multiverse',
  ]

  _DIVERSIONS = {
    '/sbin/initctl': '/bin/true',
    '/etc/init.d/systemd-logind': '/bin/true',
  }

  _ISO_COPIES = {
    'loopback.cfg': 'boot/grub/loopback.cfg',
  }

  def __init__(self, source_iso, dest_iso, archive, arch, release, modules):
    self._source_iso = source_iso
    self._dest_iso = dest_iso
    self._archive = archive
    self._arch = arch
    self._release = release
    self._modules = modules

    self._ico_server_path = os.path.dirname(sys.argv[0])

  def _Exec(self, *args, **kwargs):
    print('+', args)
    subprocess.check_call(args, **kwargs)

  def _ExecChroot(self, chroot_path, *args, **kwargs):
    self._Exec('chroot', chroot_path, *args, **kwargs)

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
      os.fchmod(fh.fileno(), stat.S_IRWXU)

  def _InstallPackages(self, chroot_path):
    os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
    self._ExecChroot(
        chroot_path,
        'apt-get',
        'update')
    self._ExecChroot(
        chroot_path,
        'apt-get',
        'install',
        '--assume-yes',
        *self._BASE_PACKAGES)

  def _RunModules(self, chroot_path):
    for module in self._modules:
      self._Exec(
          '%(module)s --chroot-path=%(chroot_path)s' % {
            'module': module,
            'chroot_path': chroot_path,
          },
          shell=True)

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

  def _Squash(self, chroot_path, union_path):
    self._Exec(
        'mksquashfs',
        chroot_path,
        os.path.join(union_path, 'casper', 'filesystem.squashfs'),
        '-noappend')

  def _CopyISOFiles(self, union_path):
    for source, dest in self._ISO_COPIES.items():
      shutil.copyfile(
          os.path.join(self._ico_server_path, 'iso_files', source),
          os.path.join(union_path, dest))

  def _CreateISO(self, union_path):
    self._Exec(
        'grub-mkrescue',
        '--output=%s' % self._dest_iso,
        union_path)

  def _BuildImage(self):
    root = tempfile.mkdtemp()
    self._rmtree.append(root)

    print('Building image in:', root)

    self._Exec(
        'mount',
        '--types', 'tmpfs',
        'none',
        root)
    self._umount.append(root)

    chroot_path = self._Debootstrap(root)
    union_path = self._CreateUnion(root)
    self._FixSourcesList(chroot_path)
    self._AddDiversions(chroot_path)
    self._InstallPackages(chroot_path)
    self._RunModules(chroot_path)
    self._CleanPackages(chroot_path)
    self._RemoveDiversions(chroot_path)
    if FLAGS.shell:
      self._Exec('bash', cwd=root)
    self._Squash(chroot_path, union_path)
    self._CopyISOFiles(union_path)
    self._CreateISO(union_path)

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
      FLAGS.dest_iso,
      FLAGS.archive,
      FLAGS.arch,
      FLAGS.release,
      FLAGS.modules)
  builder.BuildImage()


if __name__ == '__main__':
  main()
