#!/usr/bin/python3

import argparse
import os

import icon_lib


parser = argparse.ArgumentParser(description='iconograph systemid')
parser.add_argument(
    '--chroot-path',
    dest='chroot_path',
    action='store',
    required=True)
FLAGS = parser.parse_args()


def main():
  module = icon_lib.IconModule(FLAGS.chroot_path)

  os.mkdir(os.path.join(FLAGS.chroot_path, 'systemid'))

  tool_path = os.path.join(FLAGS.chroot_path, 'icon', 'systemid')
  os.makedirs(tool_path, exist_ok=True)

  script = os.path.join(tool_path, 'startup.sh')
  with open(script, 'w') as fh:
    os.fchmod(fh.fileno(), 0o755)
    fh.write("""\
#!/bin/bash
mount -o data=journal,noatime,sync LABEL=SYSTEMID /systemid
. /systemid/systemid
echo ${SYSTEMID} > /etc/hostname
hostname --file /etc/hostname
grep ${SYSTEMID} /etc/hosts >/dev/null || echo "127.0.2.1 ${SYSTEMID}" >> /etc/hosts
""")

  upstart = os.path.join(FLAGS.chroot_path, 'etc', 'init', 'systemid.conf')
  with open(upstart, 'w') as fh:
    fh.write("""
description "Mount /systemid"

start on filesystem
task

emits systemid-ready

script
  /icon/systemid/startup.sh
  initctl emit --no-wait systemid-ready
end script
""")

  systemd = os.path.join(FLAGS.chroot_path, 'lib', 'systemd', 'system', 'systemid.service')
  with open(systemd, 'w') as fh:
    fh.write("""
[Unit]
Description=Mount /systemid and configure from it
DefaultDependencies=no
Conflicts=shutdown.target
After=systemd-remount-fs.service
Before=sysinit.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/icon/systemid/startup.sh

[Install]
WantedBy=sysinit.target
""")
  try:
    module.ExecChroot(
        'systemctl',
        'unmask',
        'systemid.service')
    module.ExecChroot(
        'systemctl',
        'enable',
        'systemid.service')
  except icon_lib.SubprocessFailure:
    # trusty backwards-compat
    pass

if __name__ == '__main__':
  main()
