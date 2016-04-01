# Iconograph

Iconograph ("icon") is a system for building and deploying Linux system images.
It allows you to distribute your software intended to run on real hardware or
inside a container as a single unit with its system dependencies, and to roll
forward and backward in a secure, repeatable manner.

## Setup

```bash
sudo apt-get install --assume-yes git grub-pc xorriso squashfs-tools openssl python3-openssl debootstrap
git clone https://github.com/robot-tools/iconograph.git
cd iconograph
```
