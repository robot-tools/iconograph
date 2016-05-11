#!/usr/bin/python3

import lib
import os
import string
import tempfile


class GrubUpdater(object):

  _HOTKEYS = string.digits + string.ascii_letters

  def __init__(self, image_dir, boot_dir):
    self._image_dir = image_dir
    self._boot_dir = boot_dir

    assert self._image_dir.startswith(self._boot_dir)

    self._image_path = '/' + os.path.relpath(self._image_dir, self._boot_dir)

  def Update(self):
    grub_dir = os.path.join(self._boot_dir, 'grub')

    with tempfile.NamedTemporaryFile('w', dir=grub_dir, delete=False) as fh:
      try:
        files = []
        for filename in os.listdir(self._image_dir):
          if not filename.endswith('.iso'):
            continue
          files.append(filename)

        default_entry = None
        current = lib.GetCurrentImage(self._image_dir)
        for i, filename in enumerate(sorted(files, reverse=True)):
          if filename == current:
            default_entry = i
          fh.write("""
menuentry "%(image_filename)s (%(volume_id)s)" --hotkey=%(hotkey)s {
  search --no-floppy --file --set=root %(image_path)s/%(image_filename)s
  iso_path="%(image_path)s/%(image_filename)s"
  export iso_path
  loopback loop "%(image_path)s/%(image_filename)s"
  set root=(loop)
  configfile /boot/grub/loopback.cfg
}
""" % {
            'image_filename': filename,
            'image_path': self._image_path,
            'hotkey': self._HOTKEYS[i],
            'volume_id': lib.GetVolumeID(os.path.join(self._image_dir, filename)),
          })

        fh.write("""
set timeout=5
set default=%(default_entry)d
""" % {
          'default_entry': default_entry,
        })

        fh.flush()
        os.rename(fh.name, os.path.join(grub_dir, 'grub.cfg'))
      except:
        os.unlink(fh.name)
        raise
