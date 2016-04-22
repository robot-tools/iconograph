#!/bin/bash

set -ex

BASE=$(dirname $0)

IMAGES="/isodevice/iconograph"
mkdir -p "${IMAGES}"

BOOT="/isodevice"

FETCHER_FLAGS="$(cat /icon/config/fetcher.flags)"
if -f /icon/config/update_grub.flags; then
  UPDATE_GRUB_FLAGS="$(cat /icon/config/update_grub.flags)"
fi
CA_CERT="/icon/config/ca.image.cert.pem"

HTTPS_CLIENT_KEY="/systemid/$(hostname).www.key.pem"
HTTPS_CLIENT_CERT="/systemid/$(hostname).www.cert.pem"
HTTPS_CA_CERT="/icon/config/ca.www.cert.pem"

if test -e "${HTTPS_CLIENT_KEY}" -a -e "${HTTPS_CLIENT_CERT}"; then
  HTTPS_CLIENT_FLAGS="--https-client-cert=${HTTPS_CLIENT_CERT} --https-client-key=${HTTPS_CLIENT_KEY}"
fi
if test -e "${HTTPS_CA_CERT}"; then
  HTTPS_CA_FLAGS="--https-ca-cert=${HTTPS_CA_CERT}"
fi

"${BASE}/fetcher.py" --image-dir="${IMAGES}" --ca-cert="${CA_CERT}" ${FETCHER_FLAGS} ${HTTPS_CLIENT_FLAGS} ${HTTPS_CA_FLAGS}
"${BASE}/update_grub.py" --image-dir="${IMAGES}" --boot-dir="${BOOT}" ${UPDATE_GRUB_FLAGS} > "${BOOT}/grub/grub.cfg.tmp" && mv "${BOOT}/grub/grub.cfg.tmp" "${BOOT}/grub/grub.cfg"
