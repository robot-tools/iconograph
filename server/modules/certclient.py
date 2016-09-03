#!/usr/bin/python3

import argparse
import os
import shutil
import subprocess

import icon_lib


parser = argparse.ArgumentParser(description='iconograph certclient')
parser.add_argument(
    '--chroot-path',
    dest='chroot_path',
    action='store',
    required=True)
parser.add_argument(
    '--ca-cert',
    dest='ca_cert',
    action='store',
    required=True)
parser.add_argument(
    '--client-cert',
    dest='client_cert',
    action='store',
    required=True)
parser.add_argument(
    '--client-key',
    dest='client_key',
    action='store',
    required=True)
parser.add_argument(
    '--generate-dh',
    dest='generate_dh',
    action='store_true',
    default=False)
parser.add_argument(
    '--subject',
    dest='subject',
    action='store',
    required=True)
parser.add_argument(
    '--tag',
    dest='tag',
    action='store',
    required=True)
parser.add_argument(
    '--server',
    dest='server',
    action='store',
    required=True)
FLAGS = parser.parse_args()


def main():
  module = icon_lib.IconModule(FLAGS.chroot_path)
  module.InstallPackages('git', 'python3-requests', 'openssl')

  os.makedirs(os.path.join(FLAGS.chroot_path, 'icon', 'config'), exist_ok=True)

  if not os.path.exists(os.path.join(FLAGS.chroot_path, 'icon', 'iconograph')):
    module.ExecChroot(
        'git',
        'clone',
        'https://github.com/robot-tools/iconograph.git',
        'icon/iconograph')

  if not os.path.exists(os.path.join(FLAGS.chroot_path, 'icon', 'certserver')):
    module.ExecChroot(
        'git',
        'clone',
        'https://github.com/robot-tools/certserver.git',
        'icon/certserver')

  ca_cert_path = os.path.join('icon', 'config', 'ca.%s.certserver.cert.pem' % FLAGS.tag)
  shutil.copyfile(
    FLAGS.ca_cert,
    os.path.join(FLAGS.chroot_path, ca_cert_path))

  client_cert_path = os.path.join('icon', 'config', 'client.%s.certserver.cert.pem' % FLAGS.tag)
  shutil.copyfile(
    FLAGS.client_cert,
    os.path.join(FLAGS.chroot_path, client_cert_path))
  client_key_path = os.path.join('icon', 'config', 'client.%s.certserver.key.pem' % FLAGS.tag)
  shutil.copyfile(
    FLAGS.client_key,
    os.path.join(FLAGS.chroot_path, client_key_path))
  os.chmod(os.path.join(FLAGS.chroot_path, client_key_path), 0o400)

  tags = {
      'dh': 'y' if FLAGS.generate_dh else 'n',
      'server': FLAGS.server,
      'subject': FLAGS.subject,
      'tag': FLAGS.tag,
  }

  tool_path = os.path.join(FLAGS.chroot_path, 'icon', 'certclient-%(tag)s' % tags)
  os.makedirs(tool_path, exist_ok=True)

  script = os.path.join(tool_path, 'startup.sh')
  with open(script, 'w') as fh:
    os.chmod(fh.fileno(), 0o755)
    fh.write("""\
#!/bin/bash

exec </dev/tty9 >/dev/tty9 2>&1
chvt 9

DH="/systemid/$(hostname).%(tag)s.dh.pem"
DH_LINK="/systemid/%(tag)s.dh.pem"
KEY="/systemid/$(hostname).%(tag)s.key.pem"
KEY_LINK="/systemid/%(tag)s.key.pem"
CERT="/systemid/$(hostname).%(tag)s.cert.pem"
CERT_LINK="/systemid/%(tag)s.cert.pem"
SUBJECT="$(echo '%(subject)s' | sed s/SYSTEMID/$(hostname)/g)"

if test ! -s "${KEY}"; then
  openssl ecparam -name secp384r1 -genkey | openssl ec -out "${KEY}"
  chmod 0444 "${KEY}"
fi

chvt 9
/icon/iconograph/client/wait_for_service.py --host=%(server)s --service=https
chvt 9

if test ! -s "${CERT}"; then
  openssl req -new -key "${KEY}" -subj "${SUBJECT}" | /icon/certserver/certclient.py --ca-cert=/icon/config/ca.%(tag)s.certserver.cert.pem --client-cert=/icon/config/client.%(tag)s.certserver.cert.pem --client-key=/icon/config/client.%(tag)s.certserver.key.pem --server=%(server)s > "${CERT}"
  chmod 0444 "${CERT}"
fi

if test "%(dh)s" = "y"; then
  if test ! -s "${DH}"; then
    openssl dhparam -out "${DH}" 2048
  fi
  ln --symbolic --force $(basename "${DH}") "${DH_LINK}"
fi

ln --symbolic --force $(basename "${KEY}") "${KEY_LINK}"
ln --symbolic --force $(basename "${CERT}") "${CERT_LINK}"

chvt 9

echo
echo "=================="
echo "certclient %(tag)s complete"
echo "=================="
""" % tags)

  with module.ServiceFile('certclient-%(tag)s.service' % tags) as fh:
    fh.write("""
[Unit]
Description=CertClient %(tag)s

[Service]
Type=simple
RemainAfterExit=yes
ExecStart=/icon/certclient-%(tag)s/startup.sh

[Install]
WantedBy=multi-user.target
""" % tags)
  module.EnableService('certclient-%(tag)s.service' % tags)


if __name__ == '__main__':
  main()
