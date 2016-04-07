#!/bin/bash

set -ex

BASE=$(dirname $0)

IMAGES="/isodevice/iconograph"
mkdir -p "${IMAGES}"

BOOT="/isodevice"

FLAGS="$(cat /icon/config/fetcher.flags)"
CA_CERT="/icon/config/ca.image.cert.pem"

"${BASE}/fetcher.py" --image-dir="${IMAGES}" --ca-cert="${CA_CERT}" ${FLAGS}
"${BASE}/update_grub.py" --image-dir="${IMAGES}" --boot-dir="${BOOT}" > "${BOOT}/grub/grub.cfg.tmp" && mv "${BOOT}/grub/grub.cfg.tmp" "${BOOT}/grub/grub.cfg"
