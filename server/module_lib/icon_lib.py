#!/usr/bin/python3

import os
import shutil
import subprocess
import sys


class Error(Exception):
  pass

class SubprocessFailure(Error):
  pass


class IconModule(object):

  def __init__(self, chroot_path):
    self._chroot_path = chroot_path

  def Exec(self, *args, **kwargs):
    print('+', args)
    try:
      subprocess.check_call(args, **kwargs)
    except subprocess.CalledProcessError as e:
      print('ERROR:', e)
      raise SubprocessFailure(e)

  def ExecChroot(self, *args, **kwargs):
    self.Exec('chroot', self._chroot_path, *args, **kwargs)

  def CopyRootFSOverlay(self, source_dir):
    start_pos = len(source_dir) + 1
    for dirpath, dirnames, filenames in os.walk(source_dir):
      dest_dir = os.path.join(self._chroot_path, dirpath[start_pos:])
      # pylint: disable=unexpected-keyword-arg
      os.makedirs(dest_dir, exist_ok=True)
      shutil.copystat(dirpath, dest_dir)
      for dirname in dirnames:
        source_path = os.path.join(dirpath, dirname)
        dest_path = os.path.join(dest_dir, dirname)
        try:
          link = os.readlink(source_path)
          os.symlink(link, dest_path)
        except OSError:
          pass
      for filename in filenames:
        source_path = os.path.join(dirpath, filename)
        dest_path = os.path.join(dest_dir, filename)
        try:
          link = os.readlink(source_path)
          os.symlink(link, dest_path)
        except OSError:
          shutil.copy(source_path, dest_path)

    # In case we copied libraries
    self.ExecChroot('ldconfig')

  def InstallPackages(self, *packages):
    env = os.environ.copy()
    env['DEBIAN_FRONTEND'] = 'noninteractive'
    self.ExecChroot('apt-get', 'install', '--assume-yes', '--no-install-recommends', *packages, env=env)

  def InstallPythonPackages(self, *packages):
    self.InstallPackages('python-pip')
    self.ExecChroot('pip', 'install', *packages)

  def AddSystemUsers(self, *users):
    for user in users:
      self.ExecChroot('adduser', '--system', '--group', '--no-create-home', '--disabled-login', user)

  def AddKernelModules(self, *modules):
    with open(os.path.join(self._chroot_path, 'etc', 'modules'), 'a') as fh:
      for module in modules:
        fh.write('%s\n' % module)
