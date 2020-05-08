import os
import cereal.messaging as messaging
from cereal import car
from selfdrive.hardware import PC
from common.params import Params


if not PC:
  OP_DIR = '/data/openpilot/'
else:
  OP_DIR = '/home/pi/openpilot/'


def get_fingerprint():
  p = Params()
  CP = car.CarParams.new_message()
  cp_sock = messaging.SubMaster(['carParams'])

  fixed_fingerprint = os.environ.get('FINGERPRINT', "")
  if len(fixed_fingerprint) > 0:
    print('bodyd fp by fixed env')
    CP.carFingerprint = fixed_fingerprint
  else:
    while len(CP.carFingerprint) == 0 or 'mock' in CP.carFingerprint:
      cp_sock.update()
      cp, cp_cache = p.get("CarParams"), p.get("CarParamsCache")
      if cp is not None:
        print('bodyd fp by CarParams')
        CP = car.CarParams.from_bytes(cp)
      elif cp_cache is not None:
        print('bodyd fp by CarParamsCache')
        CP = car.CarParams.from_bytes(cp_cache)
      else:
        if cp_sock.updated['carParams']:
          CP = cp_sock['carParams']


  print(CP.carFingerprint)
  return CP

def load_body(CP):
  """Get lists of supported cars and load the cached car's values."""
  fingerprint = None
  supported = []
  body = None
  ioc = None

  # get all cars, iterate if the values.py has the BODY_SUPPORTED list, and then check a match
  for root, dirs, files in os.walk(OP_DIR + 'selfdrive/car'):
    del root
    del files
    for m in dirs:
      _path = None
      make = os.path.basename(m)
      if make.upper() in CP.carFingerprint:
          _path = ('selfdrive.car.%s' % make)
          if _path is not None:
            try:
              supported = __import__(_path + '.values', fromlist=['BODY_SUPPORTED']).BODY_SUPPORTED
            except (ModuleNotFoundError, AttributeError):
              print ('body.py not found in %s', m)
            for m in supported:
              if str(CP.carFingerprint) == m:
                fingerprint = m
                print(fingerprint)
                body = __import__(_path + '.body', fromlist=['Body']).Body
                ioc = __import__(_path + '.ioc', fromlist=['IOC']).IOC
                break
  return body, ioc


def is_offroad(p):
  if os.environ.get('ONROAD', ""):
    offroad = False
  else:
    offroad = True if p.get("IsOffroad") == b"1" else False
  return offroad


def is_panda_connected(p):
  panda = True if p.get("PandaHeartbeatLost") is None else False
  return panda


def allowed():
  """Check if we're offroad and have a connected panda."""
  p = Params()
  offroad = is_offroad(p)
  panda = is_panda_connected(p)

  if offroad and panda:
    return True
  else:
    return False
