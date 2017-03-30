#!/usr/bin/python3

import argparse
import os

import icon_lib


parser = argparse.ArgumentParser(description='iconograph persistent')
parser.add_argument(
    '--chroot-path',
    dest='chroot_path',
    action='store',
    required=True)
FLAGS = parser.parse_args()


def main():
  module = icon_lib.IconModule(FLAGS.chroot_path)

  os.mkdir(os.path.join(FLAGS.chroot_path, 'persistent'))

  tool_path = os.path.join(FLAGS.chroot_path, 'icon', 'persistent')
  os.makedirs(tool_path, exist_ok=True)

  script = os.path.join(tool_path, 'startup.sh')
  with open(script, 'w') as fh:
    os.chmod(fh.fileno(), 0o755)
    fh.write("""\
#!/bin/bash
set -ex
e2fsck -a /persistent
mount -o noatime LABEL=PERSISTENT /persistent
""")

  with module.ServiceFile('persistent.service') as fh:
    fh.write("""
[Unit]
Description=Mount /persistent
DefaultDependencies=no
Conflicts=shutdown.target
After=systemd-remount-fs.service
Before=sysinit.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/icon/persistent/startup.sh

[Install]
WantedBy=sysinit.target
""")
  module.EnableService('persistent.service')


if __name__ == '__main__':
  main()
