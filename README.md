# Iconograph

Iconograph ("icon") is a system for building and deploying Unbut system images.
It allows you to distribute your software intended to run on real hardware or
inside a container as a single unit with its system dependencies, and to roll
forward and backward in a secure, repeatable, staged manner.

## Setup

```bash
sudo apt-get install --assume-yes git grub-pc xorriso squashfs-tools openssl python3-openssl debootstrap
git clone https://github.com/robot-tools/iconograph.git
cd iconograph
```

## Image creation

### Overview

Icon creates images by merging the kernel and boot system of a desktop live CD
with a server/custom filesystem. You'll need to download the desktop live CD
ISO for the version that you're building. You can get them [http://mirror.pnl.gov/releases/](here).

### Serving

Images are fetched via HTTP. You should write images to a directory accessible
via HTTP.

### Simple image build

```bash
# Must run as sudo to mount/umount images, tmpfs, and overlayfs
sudo server/build_image.py --image-dir=/output/path --release=trusty --source-iso=path/to/ubuntu-14.04.4-desktop-amd64.iso
```
