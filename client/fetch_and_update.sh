#!/bin/sh

set -ex

BASE=$(dirname $0)

IMAGES=/isodevice/iconograph
mkdir -p "${IMAGES}"

BOOT=/isodevice

FLAGS=$(<${BASE}/flags)

${BASE}/fetcher.py --image-dir="${IMAGES}" --ca-cert=../config/ca.cert.pem ${FLAGS}
${BASE}/update_grub.py --image-dir="${IMAGES}" --boot-dir="${BOOT}" > ${BOOT}/grub/grub.cfg.tmp && mv ${BOOT}/grub/grub.cfg.tmp ${BOOT}/grub/grub.cfg
