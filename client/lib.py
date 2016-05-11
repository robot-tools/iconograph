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
