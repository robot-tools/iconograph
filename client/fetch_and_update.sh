#!/bin/sh

set -ex

IMAGES=/isodevice/iconograph
mkdir -p "${IMAGES}"

BOOT=/isodevice

FLAGS=$(<flags)

./fetcher.py --image-dir="${IMAGES}" --ca-cert=../config/ca.cert.pem ${FLAGS}
./update_grub.py --image-dir="${IMAGES}" --boot-dir="${BOOT}" > ${BOOT}/grub/grub.cfg.tmp && mv ${BOOT}/grub/grub.cfg.tmp ${BOOT}/grub/grub.cfg
