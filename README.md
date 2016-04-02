# Iconograph

Iconograph ("icon") is a system for building and deploying Unbut system images.
It allows you to distribute your software intended to run on real hardware or
inside a container as a single unit with its system dependencies, and to roll
forward and backward in a secure, repeatable, staged manner.

Images utilize a tmpfs overlay filesystem, so by default changes are discarded.

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
ISO for the version that you're building. You can get them [here](http://mirror.pnl.gov/releases/).

### Serving

Images are fetched via HTTP. You should write images to a directory accessible
via HTTP. Install apache2 if need be.

### Simple image build

```bash
# Must run as sudo to mount/umount images, tmpfs, and overlayfs
sudo server/build_image.py --image-dir=/output/path --release=trusty --source-iso=path/to/ubuntu-14.04.4-desktop-amd64.iso
```

### Modules

Modules are scripts run after the chroot has been created. They can install
packages, do configuration, etc. Icon has several stock packages, but you can
also create your own using them as examples. You can pass multiple --module
flags to build_image.py as long as the modules are compatible with each other.

#### iconograph.py

Install icon inside the image. This allows the image to auto-update over HTTP.
Use the build_image.py flag:

```bash
--module="server/modules/iconograph.py --base-url=http://yourhost/ --ca-cert=/path/to/signing/cert.pem"
```

#### persistent.py

Mount a /persistent partition from a filesystem with LABEL=PERSISTENT. Allows
data to persist across reboots, when it would normally be wiped by tmpfs.
Use the build_image.py flag:

```bash
--module="server/modules/persistent.py"
```

#### autoimage.py

Build an image that will partition, mkfs, and install an image from a different
URL onto a target system. Used to create install USB drives, PXE boot, etc.
Use the build_image.py flag:

```bash
--module="server/modules/autoimage.py --base-url=http://yourhost/ --ca-cert=/path/to/signing/cert.pem --device=/dev/sdx --persistent-percent=50"
```

`--device` specifies the device to partition and install to on the target
system.

`--persistent-percent`, if non-zero, specifies the percent of the target
device to allocate to a LABEL=PERSISTENT filesystem. If the inner image uses
persistent.py, this filesystem will be automatically mounted.
