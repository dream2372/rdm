#!/usr/bin/env python3
from cereal import car
from opendbc.can.parser import CANParser
# from cereal.services import service_list
# import cereal.messaging as messaging
from selfdrive.car.interfaces import RadarInterfaceBase
from selfdrive.car.honda.values import DBC
from common.params import Params


# HACK: put your dongle here if your radar thinks its alignment is wack#
# hint: check out ['RADC_SGUFail'] in ['TeslaRadarSguInfo']
MY_ALIGNMENT_IS_BAD_AND_I_SHOULD_FEEL_BAD = [b'8a5868733a518b54', b'3bf43be62b59afd6']

## NIDEC
def _create_nidec_can_parser(car_fingerprint):
  radar_messages = [0x400] + list(range(0x430, 0x43A)) + list(range(0x440, 0x446))
  signals = list(zip(['RADAR_STATE'] +
                ['LONG_DIST'] * 16 + ['NEW_TRACK'] * 16 + ['LAT_DIST'] * 16 +
                ['REL_SPEED'] * 16,
                [0x400] + radar_messages[1:] * 4,
                [0] + [255] * 16 + [1] * 16 + [0] * 16 + [0] * 16))
  checks = [(s[1], 20) for s in signals]
  return CANParser(DBC[car_fingerprint]['radar'], signals, checks, 1)


## Tesla
# TODO: UNUSED! Move to standalone script.
# For calibration we only want fixed objects within 2 m of the center line and between 2.5 and 4.5 m far from radar
CALIBRATION = False
MINX = 1
MAXX = 6
MINY = -2.0
MAXY = 2.0

TESLA_RADAR_MSGS_A = list(range(0x310, 0x36E, 3))
TESLA_RADAR_MSGS_B = list(range(0x311, 0x36F, 3))
NUM_TESLA_POINTS = len(TESLA_RADAR_MSGS_A)

def _create_tesla_can_parser(CP):
  # Status messages
  signals = [
    ('RADC_HWFail', 'TeslaRadarSguInfo', 0),
    ('RADC_SGUFail', 'TeslaRadarSguInfo', 0),
    ('RADC_SensorDirty', 'TeslaRadarSguInfo', 0),
    ('RADC_a012_espMIA', 'TeslaRadarAlertMatrix', 0),
    ('RADC_a013_gtwMIA', 'TeslaRadarAlertMatrix', 0),
    ('RADC_a014_sccmMIA', 'TeslaRadarAlertMatrix', 0),
    ('RADC_a042_xwdValidity', 'TeslaRadarAlertMatrix', 0),
  ]

  checks = [
    ('TeslaRadarSguInfo', 10),
    ('TeslaRadarAlertMatrix', 10),
  ]

  # Radar tracks
  for i in range(NUM_TESLA_POINTS):
    msg_id_a = TESLA_RADAR_MSGS_A[i]
    msg_id_b = TESLA_RADAR_MSGS_B[i]

    # There is a bunch more info in the messages,
    # but these are the only things actually used in openpilot
    signals.extend([
      ('LongDist', msg_id_a, 255),
      ('LongSpeed', msg_id_a, 0),
      ('LatDist', msg_id_a, 0),
      ('LongAccel', msg_id_a, 0),
      ('Meas', msg_id_a, 0),
      ('Tracked', msg_id_a, 0),
      ('Index', msg_id_a, 0),

      ('LatSpeed', msg_id_b, 0),
      ('Index2', msg_id_b, 0),
    ])

    checks.extend([
      (msg_id_a, 8),
      (msg_id_b, 8),
    ])

  return CANParser(DBC[CP.carFingerprint]['radar'], signals, checks, 0)


class RadarInterface(RadarInterfaceBase):
  def __init__(self, CP):
    super().__init__(CP)
    self.useTeslaRadar = Params().get_bool("TeslaRadarActivate")
    self.ignoreSGUAlignment = Params().get("DongleId") in MY_ALIGNMENT_IS_BAD_AND_I_SHOULD_FEEL_BAD
    self.updated_messages = set()
    self.track_id = 0
    self.radar_off_can = CP.radarOffCan

    if self.radar_off_can:
      self.rcp = None
    elif self.useTeslaRadar:
      self.rcp = _create_tesla_can_parser(CP)
      self.radarOffset = float(Params().get("TeslaRadarOffset"))
      self.trigger_msg = TESLA_RADAR_MSGS_B[-1]
    else:
      # Nidec
      print("nidec radar!")
      self.radar_fault = False
      self.radar_wrong_config = False
      self.rcp = _create_nidec_can_parser(CP.carFingerprint)
      self.trigger_msg = 0x445
  def update(self, can_strings):
    # in Honda Bosch radar and we are only steering for now, so sleep 0.05s to keep
    # radard at 20Hz and return no points
    if self.radar_off_can:
      print("no radar!")
      return super().update(None)

    vls = self.rcp.update_strings(can_strings)
    self.updated_messages.update(vls)

    if self.trigger_msg not in self.updated_messages:
      return None

    if self.useTeslaRadar:
      rr = self._update_tesla(self.updated_messages)

      self.updated_messages.clear()
    else:
      rr = self._update_nidec(self.updated_messages)
      self.updated_messages.clear()
    return rr

  def _update_nidec(self, updated_messages):
    ret = car.RadarData.new_message()

    for ii in sorted(updated_messages):
      cpt = self.rcp.vl[ii]
      if ii == 0x400:
        # check for radar faults
        self.radar_fault = cpt['RADAR_STATE'] != 0x79
        self.radar_wrong_config = cpt['RADAR_STATE'] == 0x69
      elif cpt['LONG_DIST'] < 255:
        if ii not in self.pts or cpt['NEW_TRACK']:
          self.pts[ii] = car.RadarData.RadarPoint.new_message()
          self.pts[ii].trackId = self.track_id
          self.track_id += 1
        self.pts[ii].dRel = cpt['LONG_DIST']  # from front of car
        self.pts[ii].yRel = -cpt['LAT_DIST']  # in car frame's y axis, left is positive
        self.pts[ii].vRel = cpt['REL_SPEED']
        self.pts[ii].aRel = float('nan')
        self.pts[ii].yvRel = float('nan')
        self.pts[ii].measured = True
      else:
        if ii in self.pts:
          del self.pts[ii]

    errors = []
    if not self.rcp.can_valid:
      errors.append("canError")
    if self.radar_fault:
      errors.append("fault")
    if self.radar_wrong_config:
      errors.append("wrongConfig")
    ret.errors = errors

    ret.points = list(self.pts.values())

    return ret

  def _update_tesla(self, can_strings):
    ret = car.RadarData.new_message()

    # Errors
    errors = []
    sgu_info = self.rcp.vl['TeslaRadarSguInfo']
    alert_info = self.rcp.vl['TeslaRadarAlertMatrix']

    if not self.rcp.can_valid:
      errors.append('canError')

    faked_modules_missing = alert_info['RADC_a012_espMIA'] or alert_info['RADC_a013_gtwMIA'] or alert_info['RADC_a014_sccmMIA']
    xwd_panda_setting_bad = alert_info['RADC_a042_xwdValidity']

    if sgu_info['RADC_HWFail'] or \
      (not self.ignoreSGUAlignment and sgu_info['RADC_SGUFail']) \
      or sgu_info['RADC_SensorDirty'] \
      or faked_modules_missing \
      or xwd_panda_setting_bad:
      print("Radar fault!")

      if sgu_info['RADC_HWFail']:
        print("Radar hardware fault!")
      if (not self.ignoreSGUAlignment and sgu_info['RADC_SGUFail']):
        print("SGU alignment error. Check alignment. If OK, add your dongle ID to the list at the top of selfdrive/car/honda/radar_interface.py")
      if sgu_info['RADC_SensorDirty']:
        print("Error. Clean radar to continue.")
      if faked_modules_missing:
        print("Faked Tesla modules missing. Check panda firmware.")
      if xwd_panda_setting_bad:
        print("xwd setting is incorrect for this radar. Change in panda and try again.")
      errors.append('fault')
    ret.errors = errors

    # Radar tracks
    for i in range(NUM_TESLA_POINTS):
      msg_a = self.rcp.vl[TESLA_RADAR_MSGS_A[i]]
      msg_b = self.rcp.vl[TESLA_RADAR_MSGS_B[i]]

      # Make sure msg A and B are together
      if msg_a['Index'] != msg_b['Index2']:
        continue

      # Check if it's a valid track
      if not msg_a['Tracked']:
        if i in self.pts:
          del self.pts[i]
        continue

      # New track!
      if i not in self.pts:
        self.pts[i] = car.RadarData.RadarPoint.new_message()
        self.pts[i].trackId = self.track_id
        self.track_id += 1

      # Parse track data
      self.pts[i].dRel = msg_a['LongDist']
      self.pts[i].yRel = msg_a['LatDist'] + self.radarOffset  # in car frame's y axis, left is positive.
      self.pts[i].vRel = msg_a['LongSpeed']
      self.pts[i].aRel = msg_a['LongAccel']
      self.pts[i].yvRel = msg_b['LatSpeed']
      self.pts[i].measured = bool(msg_a['Meas'])

    ret.points = list(self.pts.values())
    self.updated_messages.clear()
    return ret
