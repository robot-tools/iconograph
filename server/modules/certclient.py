#!/usr/bin/python3

import argparse
import os
import shutil
import subprocess
from urllib import parse


parser = argparse.ArgumentParser(description='iconograph autoimage')
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


def Exec(*args, **kwargs):
  print('+', args)
  subprocess.check_call(args, **kwargs)


def ExecChroot(*args, **kwargs):
  Exec('chroot', FLAGS.chroot_path, *args, **kwargs)


def main():
  ExecChroot(
      'apt-get',
      'install',
      '--assume-yes',
      'git', 'python3-requests', 'openssl')

  os.makedirs(os.path.join(FLAGS.chroot_path, 'icon', 'config'), exist_ok=True)

  if not os.path.exists(os.path.join(FLAGS.chroot_path, 'icon', 'iconograph')):
    ExecChroot(
        'git',
        'clone',
        'https://github.com/robot-tools/iconograph.git',
        'icon/iconograph')

  if not os.path.exists(os.path.join(FLAGS.chroot_path, 'icon', 'certserver')):
    ExecChroot(
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

  parsed = parse.urlparse(FLAGS.server)

  init = os.path.join(FLAGS.chroot_path, 'etc', 'init', 'certclient.%s.conf' % FLAGS.tag)
  with open(init, 'w') as fh:
    fh.write("""
description "CertClient %(tag)s"

start on systemid-ready

script
  exec </dev/tty8 >/dev/tty8 2>&1
  chvt 8

  KEY="/systemid/$(hostname).%(tag)s.key.pem"
  CERT="/systemid/$(hostname).%(tag)s.cert.pem"
  SUBJECT="$(echo '%(subject)s' | sed s/SYSTEMID/$(hostname)/g)"

  if test ! -e "${KEY}"; then
    openssl ecparam -name secp384r1 -genkey | openssl ec -out "${KEY}"
    chmod 0400 "${KEY}"
  fi

  chvt 8
  /icon/iconograph/client/wait_for_service.py --host=%(host)s --service=%(service)s
  chvt 8

  if test ! -e "${CERT}"; then
    openssl req -new -key "${KEY}" -subj "${SUBJECT}" | /icon/certserver/certclient.py --ca-cert=/icon/config/ca.%(tag)s.certserver.cert.pem --client-cert=/icon/config/client.%(tag)s.certserver.cert.pem --client-key=/icon/config/client.%(tag)s.certserver.key.pem --server=%(server)s > "${CERT}"
    chmod 0444 "${CERT}"
  fi

  chvt 8

  echo
  echo "=================="
  echo "certclient %(tag)s complete"
  echo "=================="
end script
""" % {
      'host': parsed.hostname,
      'service': parsed.port or parsed.scheme,
      'subject': FLAGS.subject,
      'tag': FLAGS.tag,
      'server': FLAGS.server,
    })


if __name__ == '__main__':
  main()
