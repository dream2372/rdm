#!/usr/bin/env python
import os
import time
from cereal import car
from selfdrive.can.parser import CANParser
from common.realtime import sec_since_boot
from selfdrive.services import service_list
import selfdrive.messaging as messaging
from selfdrive.car.honda.readconfig import CarSettings


#RADAR_A_MSGS = list(range(0x371, 0x37F , 3))
#RADAR_B_MSGS = list(range(0x372, 0x37F, 3))
BOSCH_MAX_DIST = 150. #max distance for radar
RADAR_A_MSGS = list(range(0x310, 0x36F , 3))
RADAR_B_MSGS = list(range(0x311, 0x36F, 3))
OBJECT_MIN_PROBABILITY = 20.
CLASS_MIN_PROBABILITY = 20.

# Tesla Bosch firmware has 32 objects in all objects or a selected set of the 5 we should look at
# definetly switch to all objects when calibrating but most likely use select set of 5 for normal use
USE_ALL_OBJECTS = False


def _create_nidec_can_parser():
  dbc_f = 'acura_ilx_2016_nidec.dbc'
  radar_messages = [0x400] + range(0x430, 0x43A) + range(0x440, 0x446)
  signals = list(zip(['RADAR_STATE'] +
                ['LONG_DIST'] * 16 + ['NEW_TRACK'] * 16 + ['LAT_DIST'] * 16 +
                ['REL_SPEED'] * 16,
                [0x400] + radar_messages[1:] * 4,
                [0] + [255] * 16 + [1] * 16 + [0] * 16 + [0] * 16))
  checks = list(zip([0x445], [20]))

  return CANParser(os.path.splitext(dbc_f)[0], signals, checks, 1)


def _create_radard_can_parser():
  dbc_f = 'teslaradar.dbc'
  # # TODO: make smarter
  bus = 2
  msg_a_n = len(RADAR_A_MSGS)
  msg_b_n = len(RADAR_B_MSGS)

  signals = zip(['LongDist'] * msg_a_n +  ['LatDist'] * msg_a_n +
                ['LongSpeed'] * msg_a_n + ['LongAccel'] * msg_a_n +
                ['Valid'] * msg_a_n + ['Tracked'] * msg_a_n +
                ['Meas'] * msg_a_n + ['ProbExist'] * msg_a_n +
                ['Index'] * msg_a_n + ['ProbObstacle'] * msg_a_n +
                ['LatSpeed'] * msg_b_n + ['Index2'] * msg_b_n +
                ['Class'] * msg_b_n + ['ProbClass'] * msg_b_n +
                ['Length'] * msg_b_n + ['dZ'] * msg_b_n + ['MovingState'] * msg_b_n,
                RADAR_A_MSGS * 10 + RADAR_B_MSGS * 7,
                [255.] * msg_a_n + [0.] * msg_a_n + [0.] * msg_a_n + [0.] * msg_a_n +
                [0] * msg_a_n + [0] * msg_a_n + [0] * msg_a_n + [0.] * msg_a_n +
                [0] * msg_a_n + [0.] * msg_a_n + [0.] * msg_b_n + [0] * msg_b_n +
                [0] * msg_b_n + [0.] * msg_b_n + [0.] * msg_b_n +[0.] * msg_b_n + [0]* msg_b_n)

  checks = zip(RADAR_A_MSGS + RADAR_B_MSGS, [20]*(msg_a_n + msg_b_n))

  return CANParser(os.path.splitext(dbc_f)[0], signals, checks, bus)


class RadarInterface(object):
  def __init__(self, CP):
    # check for tesla radar
    self.useTeslaRadar = CarSettings().get_value("useTeslaRadar")

    if self.useTeslaRadar:
      # Tesla radar
      self.TRACK_LEFT_LANE = True
      self.TRACK_RIGHT_LANE = True
      self.pts = {}
      self.extPts = {}
      self.valid_cnt = {key: 0 for key in RADAR_A_MSGS}
      self.delay = 0.1  # Delay of radar
      self.rcp = _create_radard_can_parser()
      self.logcan = messaging.sub_sock(service_list['can'].port)
      self.radar_off_can = CP.radarOffCan
      self.radarOffset = CarSettings().get_value("radarOffset")
      self.trackId = 1
      self.trigger_msg = RADAR_B_MSGS[-1]
      self.updated_messages = set()
    else:
      # Nidec radar
      self.TRACK_LEFT_LANE = False
      self.TRACK_RIGHT_LANE = False
      self.pts = {}
      self.track_id = 0
      self.radar_fault = False
      self.radar_wrong_config = False
      self.radar_off_can = CP.radarOffCan
      self.delay = 0.1  # Delay of radar
      # Nidec
      self.rcp = _create_nidec_can_parser()
      self.trigger_msg = 0x445
      self.updated_messages = set()

  def update(self, can_strings):
    # in Bosch radar and we are only steering for now, so sleep 0.05s to keep
    # radard at 20Hz and return no points
    if self.radar_off_can or not self.useTeslaRadar:
      time.sleep(0.05)
      return car.RadarData.new_message()

    tm = int(sec_since_boot() * 1e9)
    if can_strings != None:
      vls = self.rcp.update_strings(tm, can_strings)
      self.updated_messages.update(vls)

    if self.trigger_msg not in self.updated_messages:
      return None

    rr = self._update(self.updated_messages)
    self.updated_messages.clear()
    return rr


  def _update(self, updated_messages):
    ret = car.RadarData.new_message()
    if self.useTeslaRadar:
      # Tesla
      for message in updated_messages:
        if not(message in RADAR_A_MSGS):
          if message in self.pts:
            del self.pts[message]
          continue
        cpt = self.rcp.vl[message]
        if (cpt['LongDist'] >= BOSCH_MAX_DIST) or (cpt['LongDist']==0) or (not cpt['Tracked']):
          self.valid_cnt[message] = 0    # reset counter
          if message in self.pts:
            del self.pts[message]
        elif cpt['Valid'] and (cpt['LongDist'] < BOSCH_MAX_DIST) and (cpt['LongDist'] > 0) and (cpt['ProbExist'] >= OBJECT_MIN_PROBABILITY):
          self.valid_cnt[message] += 1
        else:
          self.valid_cnt[message] = max(self.valid_cnt[message] -1, 0)
          if (self.valid_cnt[message]==0) and (message in self.pts):
            del self.pts[message]

        #score = self.rcp.vl[ii+16]['SCORE']
        #print ii, self.valid_cnt[ii], cpt['Valid'], cpt['LongDist'], cpt['LatDist']

        # radar point only valid if it's a valid measurement and score is above 50
        # bosch radar data needs to match Index and Index2 for validity
        # also for now ignore construction elements
        if (cpt['Valid'] or cpt['Tracked'])and (cpt['LongDist']>0) and (cpt['LongDist'] < BOSCH_MAX_DIST) and \
            (cpt['Index'] == self.rcp.vl[message+1]['Index2']) and (self.valid_cnt[message] > 5) and \
            (cpt['ProbExist'] >= OBJECT_MIN_PROBABILITY): # and (self.rcp.vl[ii+1]['Class'] < 4): # and ((self.rcp.vl[ii+1]['MovingState']<3) or (self.rcp.vl[ii+1]['Class'] > 0)):
          if message not in self.pts and ( cpt['Tracked']):
            self.pts[message] = car.RadarData.RadarPoint.new_message()
            self.pts[message].trackId = self.trackId
            self.trackId = (self.trackId + 1) & 0xFFFFFFFFFFFFFFFF
            if self.trackId ==0:
              self.trackId = 1
          if message in self.pts:
            self.pts[message].dRel = cpt['LongDist']  # from front of car
            self.pts[message].yRel = cpt['LatDist']  - self.radarOffset # in car frame's y axis, left is positive
            self.pts[message].vRel = cpt['LongSpeed']
            self.pts[message].aRel = cpt['LongAccel']
            self.pts[message].yvRel = self.rcp.vl[message+1]['LatSpeed']
            self.pts[message].measured = bool(cpt['Meas'])


      ret.points = self.pts.values()
      errors = []
      if not self.rcp.can_valid:
        errors.append("canError")
      ret.errors = errors
      return ret
    else:
      # Nidec
      for ii in updated_messages:
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

      ret.points = self.pts.values()

      return ret
