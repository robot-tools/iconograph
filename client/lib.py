import os
import re
import subprocess


_VOLUME_ID_REGEX = re.compile(b'^Volume id: (?P<volume_id>.+)$', re.MULTILINE)


def GetVolumeID(path):
  isoinfo = subprocess.check_output([
    'isoinfo',
    '-d',
    '-i', path,
  ])
  match = _VOLUME_ID_REGEX.search(isoinfo)
  return match.group('volume_id').decode('ascii')


def GetCurrentImage(image_dir='/isodevice/iconograph'):
  current_path = os.path.join(image_dir, 'current')
  return os.path.basename(os.readlink(current_path))
