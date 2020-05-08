from cereal import body
from opendbc.can.parser import CANParser
from selfdrive.car.honda.values import DBC, BODY_SUNROOF_ON_CAN


BodyState = body.BodyState
Door = BodyState.Door
Window = BodyState.Window
Lighting = BodyState.Lighting


def get_body_parser(CP, offroad=False):
  signals = []
  checks = []

  # IOC feedback
  checks += [("IOC_BCM_FDBK", 0)]
  signals += [("D0", "IOC_BCM_FDBK"),
              ("D1", "IOC_BCM_FDBK")]
  # bsm
  if CP.enableBsm:
    signals += [("BSM_ALERT", "BSM_STATUS_RIGHT"),
              ("BSM_ALERT", "BSM_STATUS_LEFT"),
              ("BSM_MODE", "BSM_STATUS_RIGHT"),
              ("BSM_MODE", "BSM_STATUS_LEFT")
              ]
    checks += [("BSM_STATUS_LEFT", 3),
               ("BSM_STATUS_RIGHT", 3)]
  # generic
  signals += [# ajar state
             ('LF_OPEN', 'LEFT_DOORS'),
             ('LR_OPEN', 'LEFT_DOORS'),
             ('RF_OPEN', 'RIGHT_DOORS'),
             ('RR_OPEN', 'RIGHT_DOORS'),
             ('TRUNK_OPEN', 'TRUNK_2'),
             # locks
             ('LF_UNLOCKED', 'LF_DOOR'),
             ('UNLOCKED', 'RF_DOOR'),
             ('UNLOCKED', 'LR_DOOR'),
             ('UNLOCKED', 'RR_DOOR'),
             # windows
             ('LF_WINDOWSTATE', 'FRONT_WINDOWS'),
             ('RF_WINDOWSTATE', 'FRONT_WINDOWS'),
             # lighting
             ('LEFTSIGNAL', 'LIGHTING_3'),
             ('RIGHTSIGNAL', 'LIGHTING_3'),
             ('HAZARDS_ENABLE', 'LIGHTING_3'),
             ('REVERSE', 'LIGHTING_3'),
             ('BRAKES', 'LIGHTING_3'),
             ('PARKING_LIGHTS', 'LIGHTING_4'),
             ('HIGH_BEAMS', 'LIGHTING_1'),
             # ('LOW_BEAMS', 'LIGHTING_1'),
             ]

  if CP.carFingerprint in BODY_SUNROOF_ON_CAN:
    signals += [('SUNROOF_CLOSED', 'FRONT_WINDOWS')]

  if not offroad:
    checks += [
      # TODO: ADD MORE FREQUENCY.
      ("LEFT_DOORS", 0),
      ("RIGHT_DOORS", 0),
      ("TRUNK_2", 0),
      ("LF_DOOR", 0),
      ("RF_DOOR", 0),
      ("LR_DOOR", 0),
      ("RR_DOOR", 0),
      ("FRONT_WINDOWS", 0),
      ("LIGHTING_1", 3), # at least 3.33hz. faster if signals are changing
      ("LIGHTING_3", 3), # at least 3.33hz. faster if signals are changing
      ("LIGHTING_4", 3), # at least 3.33hz. faster if signals are changing
    ]
  else:
    checks += [
      ("LEFT_DOORS", 0),
      ("RIGHT_DOORS", 0),
      ("TRUNK_2", 0),
      ("LF_DOOR", 0),
      ("RF_DOOR", 0),
      ("LR_DOOR", 0),
      ("RR_DOOR", 0),
      ("FRONT_WINDOWS", 0),
      ("LIGHTING_1", 0), # at least 3.33hz. faster if signals are changing
      ("LIGHTING_3", 0), # at least 3.33hz. faster if signals are changing
      ("LIGHTING_4", 0), # at least 3.33hz. faster if signals are changing
    ]

  bus_body = 0 # B-CAN is forwarded to CAN 0 on fake ethernet port
  return CANParser(DBC[CP.carFingerprint]["body"], signals, checks, bus_body)


class Body():
  class SecurityControl:
    # must match body.capnp
    na = None
    doorUnlockAll = [0xef81218, 0, b"\x04\x20", 0] # unlock
    doorLockAll = [0xef81218, 0, b"\x01\x00", 0] # lock


  class CAN:
    wakeup = [0x1e12ff18, 0, b"", 0]

  def __init__(self, CP=None, fingerprint=None, cache=None):
    self.cp_body = get_body_parser(CP)

  def update(self, CP, cp_body):
    ret = body.BodyState.new_message()

    # ajar state
    ret.frontLeftDoor.state = Door.State.open if bool(cp_body.vl["LEFT_DOORS"]['LF_OPEN']) else Door.State.closed
    ret.frontRightDoor.state = Door.State.open if bool(cp_body.vl["RIGHT_DOORS"]['RF_OPEN']) else Door.State.closed
    ret.rearLeftDoor.state = Door.State.open if bool(cp_body.vl["LEFT_DOORS"]['LR_OPEN']) else Door.State.closed
    ret.rearRightDoor.state = Door.State.open if bool(cp_body.vl["RIGHT_DOORS"]['RR_OPEN']) else Door.State.closed
    # ret.hood # TODO: find this
    ret.trunk.state = Door.State.open if bool(cp_body.vl["TRUNK_2"]['TRUNK_OPEN']) else Door.State.closed

    # locks
    ret.frontLeftDoor.lock = Door.Lock.unlocked if bool(cp_body.vl["LF_DOOR"]['LF_UNLOCKED']) else Door.Lock.locked
    ret.frontRightDoor.lock = Door.Lock.unlocked if bool(cp_body.vl["RF_DOOR"]['UNLOCKED']) else Door.Lock.locked
    ret.rearLeftDoor.lock = Door.Lock.unlocked if bool(cp_body.vl["LR_DOOR"]['UNLOCKED']) else Door.Lock.locked
    ret.rearRightDoor.lock = Door.Lock.unlocked if bool(cp_body.vl["RR_DOOR"]['UNLOCKED']) else Door.Lock.locked

    # windows
    ret.frontLeftWindow = Window.closed if bool(cp_body.vl["FRONT_WINDOWS"]["LF_WINDOWSTATE"]) else Window.open
    ret.frontRightWindow = Window.closed if bool(cp_body.vl["FRONT_WINDOWS"]["RF_WINDOWSTATE"]) else Window.open

    # not on CAN for at least Civic
    # ret.backLeftWindow = Window.closed if bool(cp_body.vl["FRONT_WINDOWS"]["LF_WINDOWSTATE"]) else Window.open
    # ret.backRightWindow = Window.closed if bool(cp_body.vl["FRONT_WINDOWS"]["LF_WINDOWSTATE"]) else Window.open

    # Accord reports sunroof state on CAN
    if CP.carFingerprint in BODY_SUNROOF_ON_CAN:
      ret.sunroof = Window.closed if bool(cp_body.vl["FRONT_WINDOWS"]["SUNROOF_CLOSED"]) else Window.open

    # bsm
    if CP.enableBsm:
      ret.leftBlindSpot.warning = bool(cp_body.vl["BSM_STATUS_LEFT"]["BSM_ALERT"])
      ret.leftBlindSpot.mode = cp_body.vl["BSM_STATUS_LEFT"]["BSM_MODE"]
      ret.rightBlindSpot.warning = bool(cp_body.vl["BSM_STATUS_RIGHT"]["BSM_ALERT"])
      ret.rightBlindSpot.mode = cp_body.vl["BSM_STATUS_RIGHT"]["BSM_MODE"]

    # lighting
    # the bulb state, not stalk position
    ret.lighting.leftBlinker = bool(cp_body.vl["LIGHTING_3"]["LEFTSIGNAL"])
    ret.lighting.rightBlinker = bool(cp_body.vl["LIGHTING_3"]["RIGHTSIGNAL"])

    ret.lighting.hazards = bool(cp_body.vl["LIGHTING_3"]["HAZARDS_ENABLE"])
    ret.lighting.parking = bool(cp_body.vl["LIGHTING_4"]["PARKING_LIGHTS"])
    # ret.lighting.lowBeams =
    ret.lighting.highBeams = bool(cp_body.vl["LIGHTING_1"]["HIGH_BEAMS"])
    ret.lighting.reverse = bool(cp_body.vl["LIGHTING_3"]["REVERSE"])
    # TODO: find real brake lights, not the pedal
    # ret.lighting.brake = bool(cp_body.vl["LIGHTING_3"]["BRAKES"])
    # ret.lighting.drl = ?

    self.iocFeedback = cp_body.vl["IOC_BCM_FDBK"]

    BSout = ret.as_reader()
    return BSout
