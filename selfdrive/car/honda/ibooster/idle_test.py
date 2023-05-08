#!/usr/bin/env python3

import cereal.messaging as messaging

from opendbc.can.packer import CANPacker

from selfdrive.boardd.boardd import can_list_to_can_capnp

import time

class FakeHonda:
  def __init__(self):

    self.idx = 0
    self.frame = 0
    self.packer = CANPacker('HONDA_MASTER')
    self.pm = messaging.PubMaster(['sendcan'])
    self.carType = 'CRV' # or ACCORD

    self.idx_100 = 0
    self.idx_50 = 0
    self.idx_25 = 0
    self.idx_10 = 0
    self.idx_5 = 0
    self.idx_3 = 0
    self.idx_2 = 0
    self.idx_1 = 0
    

  def send(self):
    can_sends = []

    ###### 100hz #####
    for bus in [0,2]:
      # can_sends.append(self.packer.make_can_msg("SRS_KINEMATICS", bus, {'COUNTER':self.idx_100})) # 148
      can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_GAS_PEDAL_2", bus, {'COUNTER':self.idx_100})) # 304
      # can_sends.append(self.packer.make_can_msg("EPS_STEERING_SENSORS_A", bus, {'COUNTER':self.idx_100})) # 330
      can_sends.append(self.packer.make_can_msg("TCM_GATEWAYFORWARD_ENGINE_DATA", bus, {'COUNTER':self.idx_100})) # 344
      # can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_POWERTRAIN_DATA", bus, {'COUNTER':self.idx_100})) # 380
      # can_sends.append(self.packer.make_can_msg("TCM_GATEWAYFORWARD_GEARBOX_CVT", bus, {'COUNTER':self.idx_100})) # 401
      if bus == 0:
        # if self.carType == 'CRV':
        #   can_sends.append(self.packer.make_can_msg("CRV_IDK_154", 0, {'COUNTER':self.idx_100})) # 340
        # can_sends.append(self.packer.make_can_msg("RADAR_STEERING_CONTROL", 0, {'COUNTER':self.idx_100})) # 228
        can_sends.append(self.packer.make_can_msg("VSA_IBOOSTER_COMMAND", 0, {'COUNTER':self.idx_100})) # 232
      # can_sends.append(self.packer.make_can_msg("EPS_STEER_STATUS", 0, {'COUNTER':self.idx_100})) # 399
      # else:
        # can_sends.append(self.packer.make_can_msg("VSA_C7", 2, {'COUNTER':self.idx_100})) # 199
    self.idx_100 = (self.idx_100+1) % 4

    ###### 50hz #####
    if (self.frame % 2) == 0:
      for bus in [0,2]:
        
        # can_sends.append(self.packer.make_can_msg("VSA_STATUS", bus, {'COUNTER':self.idx_50})) # 420
        can_sends.append(self.packer.make_can_msg("OBD2_TCM_1A7", bus, {'COUNTER':self.idx_50})) # 423
        can_sends.append(self.packer.make_can_msg("VSA_STANDSTILL", bus, {'COUNTER':self.idx_50})) # 432
        # can_sends.append(self.packer.make_can_msg("VSA_GATEWAYFORWARD_EPB_STATUS", bus, {'COUNTER':self.idx_50})) # 450
        # can_sends.append(self.packer.make_can_msg("VSA_WHEEL_SPEEDS", bus, {'COUNTER':self.idx_50})) # 464
        # if self.carType == 'CRV':
          # can_sends.append(self.packer.make_can_msg("CRV_IDK_1DA", 0, {'COUNTER':self.idx_50})) # 474
        # can_sends.append(self.packer.make_can_msg("RADAR_ACC_CONTROL", bus, {'COUNTER':self.idx_50})) # 479
        # can_sends.append(self.packer.make_can_msg("RADAR_ACC_CONTROL_ON", bus, {'COUNTER':self.idx_50})) # 495
        if bus == 0:
          can_sends.append(self.packer.make_can_msg("VSA_WHEEL_TICKS", bus, {'COUNTER':self.idx_50})) # 441
          # can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_1DD", bus, {'COUNTER':self.idx_50})) # 477
          can_sends.append(self.packer.make_can_msg("VSA_KINEMATICS", bus, {'COUNTER':self.idx_50})) # 490
        else:
          can_sends.append(self.packer.make_can_msg("VSA_GATEWAYFORWARD_1AC", bus, {'COUNTER':self.idx_50})) # 428
          can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_1D6", bus, {'COUNTER':self.idx_50})) # 470
          can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_ENGINE_DATA_2", bus, {'COUNTER':self.idx_50})) # 476
          can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_ACC_CONTROL_ON_2", bus, {'COUNTER':self.idx_50})) # 493
          can_sends.append(self.packer.make_can_msg("OBD2_IDK_1FB", bus, {'COUNTER':self.idx_50})) # 507
      self.idx_50 = (self.idx_50+1) % 4
      
    ###### 25hz #####
    if (self.frame % 4) == 0:
      for bus in [0,2]:
        can_sends.append(self.packer.make_can_msg("METER_221", bus, {'COUNTER':self.idx_25})) # 545
        # can_sends.append(self.packer.make_can_msg("SRS_39", bus, {'COUNTER':self.idx_25})) # 57
        # can_sends.append(self.packer.make_can_msg("VSA_ROUGH_WHEEL_SPEED", bus, {'COUNTER':self.idx_25})) # 597
        can_sends.append(self.packer.make_can_msg("METER_SCM_BUTTONS", bus, {'COUNTER':self.idx_25})) # 662
        if bus == 2 and self.carType == 'CRV':
          can_sends.append(self.packer.make_can_msg("CRV_IDK_295", 0, {'COUNTER':self.idx_25})) # 661
      self.idx_25 = (self.idx_25+1) % 4
      
    ###### 10hz #####
    if (self.frame % 10) == 0:
      for bus in [0,2]:
        # can_sends.append(self.packer.make_can_msg("SRS_SEATBELT_STATUS", bus, {'COUNTER':self.idx_10})) # 773
        can_sends.append(self.packer.make_can_msg("METER_CAR_SPEED", bus, {'COUNTER':self.idx_10})) # 777
        can_sends.append(self.packer.make_can_msg("RADAR_ACC_HUD", bus, {'COUNTER':self.idx_10})) # 780
        can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_320", bus, {'COUNTER':self.idx_10})) # 800
        # can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_CRUISE", bus, {'COUNTER':self.idx_10})) # 804
        # can_sends.append(self.packer.make_can_msg("METER_SCM_FEEDBACK", bus, {'COUNTER':self.idx_10})) # 806
        can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_328", bus, {'COUNTER':self.idx_10})) # 808
        # if self.carType == 'CRV':
          # can_sends.append(self.packer.make_can_msg("CRV_IDK_32E", 0, {'COUNTER':self.idx_10})) # 814
        # can_sends.append(self.packer.make_can_msg("RADAR_LKAS_HUD", bus, {'COUNTER':self.idx_10})) # 829
        # can_sends.append(self.packer.make_can_msg("CAMERA_MESSAGES", bus, {'COUNTER':self.idx_10})) # 862
        # can_sends.append(self.packer.make_can_msg("METER_STALK_STATUS", bus, {'COUNTER':self.idx_10})) # 884
        can_sends.append(self.packer.make_can_msg("METER_STALK_STATUS_2", bus, {'COUNTER':self.idx_10})) # 891
        # can_sends.append(self.packer.make_can_msg("RADAR_HUD", bus, {'COUNTER':self.idx_10})) # 927
        if bus == 2:
          # can_sends.append(self.packer.make_can_msg("VSA_GATEWAYFORWARD_31B", bus, {'COUNTER':self.idx_10})) # 795
          can_sends.append(self.packer.make_can_msg("OBD2_PCM_32F", bus, {'COUNTER':self.idx_10})) # 815
          # if self.carType == 'CRV':
            # can_sends.append(self.packer.make_can_msg("CRV_IDK_331", bus, {'COUNTER':self.idx_10})) # 817
          can_sends.append(self.packer.make_can_msg("OBD2_PCM_339", bus, {'COUNTER':self.idx_10})) # 825
          can_sends.append(self.packer.make_can_msg("OBD2_METER_371", bus, {'COUNTER':self.idx_10})) # 881
          can_sends.append(self.packer.make_can_msg("OBD2_METER_372", bus, {'COUNTER':self.idx_10})) # 882
          # can_sends.append(self.packer.make_can_msg("OBD2_METER_378", bus, {'COUNTER':self.idx_10})) # 888
          # can_sends.append(self.packer.make_can_msg("OBD2_METER_396", bus, {'COUNTER':self.idx_10})) # 918
      self.idx_10 = (self.idx_10+1) % 4
      
    ###### 5hz #####
    # if (self.frame % 20) == 0:
      # for bus in [0,2]:
      #   can_sends.append(self.packer.make_can_msg("METER_3A1", bus, {'COUNTER':self.idx_5})) # 929
      #   if bus == 0:
      #     can_sends.append(self.packer.make_can_msg("VSA_3D9", bus, {'COUNTER':self.idx_5})) # 985
      #   else:
      #     can_sends.append(self.packer.make_can_msg("OBD2_PCM_3D7", bus, {'COUNTER':self.idx_5})) # 983
      # self.idx_5 = (self.idx_5+1) % 4

    ###### 3hz #####
    if (self.frame % 33) == 0:
      for bus in [0,2]:
        # can_sends.append(self.packer.make_can_msg("TCM_GATEWAYFORWARD_403", bus, {'COUNTER':self.idx_3})) # 1027
        can_sends.append(self.packer.make_can_msg("METER_DOORS_STATUS", bus, {'COUNTER':self.idx_3})) # 1029
        # can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_40C", bus, {'COUNTER':self.idx_3})) # 1036
        # can_sends.append(self.packer.make_can_msg("TCM_GATEWAYFORWARD_40F", bus, {'COUNTER':self.idx_3})) # 1039
        if self.carType == 'CRV':
          can_sends.append(self.packer.make_can_msg("CRV_IDK_445", bus, {'COUNTER':self.idx_3})) # 1093
        can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_454", bus, {'COUNTER':self.idx_3})) # 1108
        if bus == 0:
          can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_400", bus, {'COUNTER':self.idx_3})) # 1024
        else:
          can_sends.append(self.packer.make_can_msg("OBD2_METER_428", bus, {'COUNTER':self.idx_3})) # 1064
          can_sends.append(self.packer.make_can_msg("OBD2_METER_444", bus, {'COUNTER':self.idx_3})) # 1092
          # can_sends.append(self.packer.make_can_msg("OBD2_IDK_45B", bus, {'COUNTER':self.idx_3})) # 1115
          can_sends.append(self.packer.make_can_msg("OBD2_PCM_465", bus, {'COUNTER':self.idx_3})) # 1125
          can_sends.append(self.packer.make_can_msg("OBD2_PCM_467", bus, {'COUNTER':self.idx_3})) # 1127
      self.idx_3 = (self.idx_3+1) % 4

    ###### 2hz #####
    if (self.frame % 50) == 0:
      for bus in [0,2]:
        can_sends.append(self.packer.make_can_msg("METER_516", bus, {'COUNTER':self.idx_2})) # 1302
        if bus == 0:
          can_sends.append(self.packer.make_can_msg("METER_52A", bus, {'COUNTER':self.idx_2})) # 1322
          can_sends.append(self.packer.make_can_msg("EPS_MAYBE_551", bus, {'COUNTER':self.idx_2})) # 1361
          can_sends.append(self.packer.make_can_msg("SRS_555", bus, {'COUNTER':self.idx_2})) # 1365
          can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_661", bus, {'COUNTER':self.idx_2})) # 1633
        else:
          can_sends.append(self.packer.make_can_msg("OBD2_METER_510", bus, {'COUNTER':self.idx_2})) # 1296
      self.idx_2 = (self.idx_2+1) % 4

    ###### 1hz #####
    if (self.frame % 100) == 0:
      bus = 0
      can_sends.append(self.packer.make_can_msg("VSA_590", bus, {'COUNTER':self.idx_1})) # 1424
      # can_sends.append(self.packer.make_can_msg("RADAR_640", bus, {'COUNTER':self.idx_1})) # 1600
      # can_sends.append(self.packer.make_can_msg("RADAR_641", bus, {'COUNTER':self.idx_1})) # 1601
      # if self.carType == 'CRV':
        # can_sends.append(self.packer.make_can_msg("CRV_IDK_652", bus, {'COUNTER':self.idx_1})) # 1618
      self.idx_1 = (self.idx_1+1) % 4

    if len(can_sends):
      self.pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan', valid=True))

    return

def nav_thread():
  fake_car = FakeHonda()
  while 1:
    # TODO: trigger off of 0xe7 on bus 2 instead
    # 100hz loop
    fake_car.send()
    fake_car.frame += 1
    time.sleep(0.00975)

if __name__ == '__main__':
  nav_thread()