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

  with module.ServiceFile('systemid.service') as fh:
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
  module.EnableService('systemid.service')


if __name__ == '__main__':
  main()
