#!/usr/bin/env python3

import cereal.messaging as messaging
from opendbc.can.packer import CANPacker
from selfdrive.boardd.boardd import can_list_to_can_capnp
from selfdrive.car.car_helpers import get_one_can
import time

class FakeHonda:
  def __init__(self):

    self.idx = 0
    self.frame = 0
    self.packer = CANPacker('HONDA_MASTER')
    self.pm = messaging.PubMaster(['sendcan'])
    self.carType = 'CRV' # or ACCORD

    self.ignition = True
    self.braking = False
    self.computer_brake = 0
    self.speed = 0.
    self.driver_door = True

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
      can_sends.append(self.packer.make_can_msg("SRS_KINEMATICS", bus, {'LAT_ACCEL': 0.035,
                                                                        'LONG_ACCEL': 0.070,
                                                                        'NEW_SIGNAL_2': 436,
                                                                        'NEW_SIGNAL_1': 513,
                                                                        'NEW_SIGNAL_5': 3,
                                                                        'NEW_SIGNAL_3': 1,
                                                                        'COUNTER':self.idx_100})) # 148
      can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_GAS_PEDAL_2", bus, {'ENGINE_TORQUE_REQUEST': -1,
                                                                                        'NEW_SIGNAL_2': 2,
                                                                                        'NEW_SIGNAL_2A': 1,
                                                                                        'COUNTER':self.idx_100})) # 304
      can_sends.append(self.packer.make_can_msg("EPS_STEERING_SENSORS_A", bus, {'STEER_SENSOR_STATUS_3': 1,
                                                                                'STEER_SENSOR_STATUS_1': 1,
                                                                                'COUNTER':self.idx_100})) # 330
      can_sends.append(self.packer.make_can_msg("TCM_GATEWAYFORWARD_ENGINE_DATA", bus, {'COUNTER':self.idx_100})) # 344
      can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_POWERTRAIN_DATA", bus, {'BOH_17C': 1,
                                                                                              'COUNTER':self.idx_100})) # 380
      can_sends.append(self.packer.make_can_msg("TCM_GATEWAYFORWARD_GEARBOX_CVT", bus, {'GEAR_SHIFTER': 1,
                                                                                        'BOH': 33,
                                                                                        'NEW_SIGNAL_6': 1,
                                                                                        'COUNTER':self.idx_100})) # 401
      if bus == 0:
        if self.carType == 'CRV':
          can_sends.append(self.packer.make_can_msg("CRV_IDK_154", 0, {'NEW_SIGNAL_2': 255,
                                                                        'NEW_SIGNAL_3': 93,
                                                                        'COUNTER':self.idx_100})) # 340
        can_sends.append(self.packer.make_can_msg("RADAR_STEERING_CONTROL", 0, {'COUNTER':self.idx_100})) # 228
        can_sends.append(self.packer.make_can_msg("VSA_IBOOSTER_COMMAND", 0, {'NEW_SIGNAL_1': 256,
                                                                              'COMPUTER_BRAKE': self.computer_brake,
                                                                              'COMPUTER_BRAKE_REQUEST': self.braking,
                                                                              'COUNTER':self.idx_100})) # 232
        can_sends.append(self.packer.make_can_msg("EPS_STEER_STATUS", 0, {'STEER_TORQUE_SENSOR': 0.111,
                                                                          'STEER_STATUS': 3,
                                                                          'STEER_CONFIG_INDEX': 1,
                                                                          'COUNTER':self.idx_100})) # 399
      else:
        can_sends.append(self.packer.make_can_msg("VSA_C7", 2, {'IGN':int(self.ignition),
                                                                'NEW_SIGNAL_3': 24,
                                                                'NEW_SIGNAL_5': 1,
                                                                'WTF_IS_THIS': 2,
                                                                'COUNTER':self.idx_100})) # 199
    self.idx_100 = (self.idx_100+1) % 4

    ###### 50hz #####
    if (self.frame % 2) == 0:
      for bus in [0,2]:
        
        can_sends.append(self.packer.make_can_msg("VSA_STATUS", bus, {'BRAKE_PEDAL_TRAVEL': 18.65,
                                                                      'NEW_SIGNAL_4': 32,
                                                                      'NEW_SIGNAL_7': 1,
                                                                      'TCS_DISABLED': 1,
                                                                      'TCS_LIGHT': 1,
                                                                      'COUNTER':self.idx_50})) # 420
        can_sends.append(self.packer.make_can_msg("OBD2_TCM_1A7", bus, {'COUNTER':self.idx_50})) # 423
        can_sends.append(self.packer.make_can_msg("VSA_STANDSTILL", bus, {'NEW_SIGNAL_5': 1,
                                                                          'NEW_SIGNAL_4': 1,
                                                                          'NEW_SIGNAL_1': 1,
                                                                          'COUNTER':self.idx_50})) # 432
        can_sends.append(self.packer.make_can_msg("VSA_GATEWAYFORWARD_EPB_STATUS", bus, {'COUNTER':self.idx_50})) # 450
        can_sends.append(self.packer.make_can_msg("VSA_WHEEL_SPEEDS", bus, {'WHEEL_SPEED_FL': self.speed,
                                                                            'WHEEL_SPEED_FR': self.speed,
                                                                            'WHEEL_SPEED_RL': self.speed,
                                                                            'WHEEL_SPEED_RR': self.speed})) # 464
        can_sends.append(self.packer.make_can_msg("EPS_STEER_MOTOR_TORQUE", bus, {'CONFIG_VALID': 1,
                                                                                  'OUTPUT_DISABLED': 1,
                                                                                  'STEERING_PRESSED': 1,
                                                                                  'COUNTER':self.idx_50})) # 450                   
        if self.carType == 'CRV':
          can_sends.append(self.packer.make_can_msg("CRV_IDK_1DA", 0, {'NEW_SIGNAL_1': 25,
                                                                       'NEW_SIGNAL_3': 250,
                                                                       'COUNTER':self.idx_50})) # 474
        can_sends.append(self.packer.make_can_msg("RADAR_ACC_CONTROL", bus, {'COUNTER':self.idx_50})) # 479
        can_sends.append(self.packer.make_can_msg("RADAR_ACC_CONTROL_ON", bus, {'COUNTER':self.idx_50})) # 495
        if bus == 0:
          can_sends.append(self.packer.make_can_msg("VSA_WHEEL_TICKS", bus, {'COUNTER':self.idx_50})) # 441
          can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_1DD", bus, {'NEW_SIGNAL_1': 216,
                                                                                    'NEW_SIGNAL_2': 3055,
                                                                                    'COUNTER':self.idx_50})) # 477
          can_sends.append(self.packer.make_can_msg("VSA_KINEMATICS", bus, {'LAT_ACCEL': 0.,
                                                                            'LONG_ACCEL': 0.,
                                                                            'COUNTER':self.idx_50})) # 490
        else:
          can_sends.append(self.packer.make_can_msg("VSA_GATEWAYFORWARD_1AC", bus, {'BOH': 32767,
                                                                                    'COUNTER':self.idx_50})) # 428
          can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_1D6", bus, {'NEW_SIGNAL_1': 320,
                                                                                    'COUNTER':self.idx_50})) # 470
          can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_ENGINE_DATA_2", bus, {'IGN_OR_MODULEPINGSTATE': self.ignition,
                                                                                              'NEW_SIGNAL_1': 1,
                                                                                              'COUNTER':self.idx_50})) # 476
          can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_ACC_CONTROL_ON_2", bus, {'COUNTER':self.idx_50})) # 493
          can_sends.append(self.packer.make_can_msg("OBD2_IDK_1FB", bus, {'COUNTER':self.idx_50})) # 507
      self.idx_50 = (self.idx_50+1) % 4
      
    ###### 25hz #####
    if (self.frame % 4) == 0:
      for bus in [0,2]:
        can_sends.append(self.packer.make_can_msg("METER_221", bus, {'NEW_SIGNAL_4': 11,
                                                                     'NEW_SIGNAL_1': 120,
                                                                     'COUNTER':self.idx_25})) # 545
        can_sends.append(self.packer.make_can_msg("SRS_39", bus, {'COUNTER':self.idx_25})) # 57
        can_sends.append(self.packer.make_can_msg("VSA_ROUGH_WHEEL_SPEED", bus, {'SET_TO_X55': 85,
                                                                                 'SET_TO_X55_2': 85,
                                                                                 'LONG_COUNTER': 124,
                                                                                 'SLOW_COUNTER': 3,
                                                                                 'COUNTER':self.idx_25})) # 597
        can_sends.append(self.packer.make_can_msg("METER_SCM_BUTTONS", bus, {'COUNTER':self.idx_25})) # 662
        if bus == 2 and self.carType == 'CRV':
          can_sends.append(self.packer.make_can_msg("CRV_IDK_295", 0, {'COUNTER':self.idx_25})) # 661
      self.idx_25 = (self.idx_25+1) % 4
      
    ###### 10hz #####
    if (self.frame % 10) == 0:
      for bus in [0,2]:
        can_sends.append(self.packer.make_can_msg("SRS_SEATBELT_STATUS", bus, {'NEW_SIGNAL_1': 1,
                                                                               'SEATBELT_DRIVER_LAMP': 1,
                                                                               'SEATBELT_DRIVER_UNLATCHED': 1,
                                                                               'SEATBELT_PASS_UNLATCHED': 1,
                                                                               'PASS_AIRBAG_OFF': 1,
                                                                               'COUNTER':self.idx_10})) # 773
        can_sends.append(self.packer.make_can_msg("METER_CAR_SPEED", bus, {'NEW_SIGNAL_2': 1,
                                                                           'LOCK_STATUS': 1,
                                                                           'NEW_SIGNAL_2': 2,
                                                                           'COUNTER':self.idx_10})) # 777
        can_sends.append(self.packer.make_can_msg("RADAR_ACC_HUD", bus, {'COUNTER':self.idx_10})) # 780
        can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_320", bus, {'COUNTER':self.idx_10})) # 800
        can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_CRUISE", bus, {'TEMP_RELATED': 95.1,
                                                                                     'NEW_SIGNAL_5': 1,
                                                                                     'NEW_SIGNAL_6': 1,
                                                                                     'COUNTER':self.idx_10})) # 804
        can_sends.append(self.packer.make_can_msg("METER_SCM_FEEDBACK", bus, {'FUEL_LEVEL': 26901,
                                                                              'DRIVERS_DOOR_OPEN': self.driver_door,
                                                                              # 'MAIN_ON'
                                                                              'COUNTER':self.idx_10})) # 806
        can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_328", bus, {'COUNTER':self.idx_10})) # 808
        if self.carType == 'CRV':
          can_sends.append(self.packer.make_can_msg("CRV_IDK_32E", 0, {'NEW_SIGNAL_1': 132,
                                                                       'NEW_SIGNAL_3': 2,
                                                                       'COUNTER':self.idx_10})) # 814
        can_sends.append(self.packer.make_can_msg("RADAR_LKAS_HUD", bus, {'COUNTER':self.idx_10})) # 829
        can_sends.append(self.packer.make_can_msg("CAMERA_MESSAGES", bus, {'ZEROS_BOH': 2,
                                                                           'COUNTER':self.idx_10})) # 862
        can_sends.append(self.packer.make_can_msg("METER_STALK_STATUS", bus, {'NEW_SIGNAL_7': 53,
                                                                              'NEW_SIGNAL_8': 96,
                                                                              'NEW_SIGNAL_9': 7,
                                                                              'NEW_SIGNAL_1': 222,
                                                                              'COUNTER':self.idx_10})) # 884
        can_sends.append(self.packer.make_can_msg("METER_STALK_STATUS_2", bus, {'NEW_SIGNAL_3': 1,
                                                                                'COUNTER':self.idx_10})) # 891
        can_sends.append(self.packer.make_can_msg("RADAR_HUD", bus, {'COUNTER':self.idx_10})) # 927
        if bus == 2:
          can_sends.append(self.packer.make_can_msg("VSA_GATEWAYFORWARD_31B", bus, {'NEW_SIGNAL_5': 90,
                                                                                    'NEW_SIGNAL_6': 64,
                                                                                    'COUNTER':self.idx_10})) # 795
          can_sends.append(self.packer.make_can_msg("OBD2_PCM_32F", bus, {'COUNTER':self.idx_10})) # 815
          if self.carType == 'CRV':
            can_sends.append(self.packer.make_can_msg("CRV_IDK_331", bus, {'NEW_SIGNAL_1': 88,
                                                                           'COUNTER':self.idx_10})) # 817
          can_sends.append(self.packer.make_can_msg("OBD2_PCM_339", bus, {'NEW_SIGNAL_1': 254,
                                                                          'NEW_SIGNAL_2': 24,
                                                                          'NEW_SIGNAL_3': 112,
                                                                          'COUNTER':self.idx_10})) # 825
          can_sends.append(self.packer.make_can_msg("OBD2_METER_371", bus, {'COUNTER':self.idx_10})) # 881
          can_sends.append(self.packer.make_can_msg("OBD2_METER_372", bus, {'NEW_SIGNAL_1': 232,
                                                                            'COUNTER':self.idx_10})) # 882
          can_sends.append(self.packer.make_can_msg("OBD2_METER_378", bus, {'NEW_SIGNAL_2': 44,
                                                                            'NEW_SIGNAL_5': 1,
                                                                            'COUNTER':self.idx_10})) # 888
          can_sends.append(self.packer.make_can_msg("OBD2_METER_396", bus, {'NEW_SIGNAL_1': 44,
                                                                            'NEW_SIGNAL_2': 53,
                                                                            'COUNTER':self.idx_10})) # 918
      self.idx_10 = (self.idx_10+1) % 4
      
    ###### 5hz #####
    if (self.frame % 20) == 0:
      for bus in [0,2]:
        can_sends.append(self.packer.make_can_msg("METER_3A1", bus, {'NEW_SIGNAL_6': 60,
                                                                     'NEW_SIGNAL_4': 1,
                                                                     'NEW_SIGNAL_8': 16,
                                                                     'NEW_SIGNAL_9': 2,
                                                                     'NEW_SIGNAL_10': 1,
                                                                     'COUNTER':self.idx_5})) # 929
        if bus == 0:
          can_sends.append(self.packer.make_can_msg("VSA_3D9", bus, {'NEW_SIGNAL_2': 132,
                                                                     'NEW_SIGNAL_3': 1,
                                                                     'COUNTER':self.idx_5})) # 985
        else:
          can_sends.append(self.packer.make_can_msg("OBD2_PCM_3D7", bus, {'NEW_SIGNAL_1': 176,
                                                                          'COUNT_A': 0,
                                                                          'COUNT_B': 6})) # 983
      self.idx_5 = (self.idx_5+1) % 4

    ###### 3hz #####
    if (self.frame % 33) == 0:
      for bus in [0,2]:
        can_sends.append(self.packer.make_can_msg("TCM_GATEWAYFORWARD_403", bus, {'COUNTER':self.idx_3})) # 1027
        can_sends.append(self.packer.make_can_msg("METER_DOORS_STATUS", bus, {'DOOR_OPEN_FL': self.driver_door,
                                                                              'COUNTER':self.idx_3})) # 1029
        # TODO: USE ACCORD FRAMES
        can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_40C", bus, {'COUNTER':self.idx_3})) # 1036
        # TODO: USE ACCORD FRAMES
        can_sends.append(self.packer.make_can_msg("TCM_GATEWAYFORWARD_40F", bus, {'COUNTER':self.idx_3})) # 1039
        if self.carType == 'CRV':
          can_sends.append(self.packer.make_can_msg("CRV_IDK_445", bus, {'NEW_SIGNAL_1': 65,
                                                                         'COUNTER':self.idx_3})) # 1093
        can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_454", bus, {'NEW_SIGNAL_1': 39,
                                                                                  'NEW_SIGNAL_4': 239,
                                                                                  'NEW_SIGNAL_5': 1,
                                                                                  'NEW_SIGNAL_6': 18,
                                                                                  'NEW_SIGNAL_7': 126,
                                                                                  'NEW_SIGNAL_10': 1,
                                                                                  'NEW_SIGNAL_9': 1,
                                                                                  'COUNTER':self.idx_3})) # 1108
        if bus == 0:
          can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_400", bus, {'NEW_SIGNAL_5': 2,
                                                                                    'COUNTER':self.idx_3})) # 1024
        else:
          can_sends.append(self.packer.make_can_msg("OBD2_METER_428", bus, {'NEW_SIGNAL_1': 1,
                                                                            'NEW_SIGNAL_5': 193,
                                                                            'NEW_SIGNAL_6': 195,
                                                                            'COUNTER':self.idx_3})) # 1064
          can_sends.append(self.packer.make_can_msg("OBD2_METER_444", bus, {'COUNTER':self.idx_3})) # 1092
          can_sends.append(self.packer.make_can_msg("OBD2_IDK_45B", bus, {'COUNTER':self.idx_3})) # 1115
          can_sends.append(self.packer.make_can_msg("OBD2_PCM_465", bus, {'NEW_SIGNAL_2': 1,
                                                                          'COUNTER':self.idx_3})) # 1125
          can_sends.append(self.packer.make_can_msg("OBD2_PCM_467", bus, {'NEW_SIGNAL_1': 32,
                                                                          'COUNTER':self.idx_3})) # 1127
      self.idx_3 = (self.idx_3+1) % 4

    ###### 2hz #####
    if (self.frame % 50) == 0:
      for bus in [0,2]:
        can_sends.append(self.packer.make_can_msg("METER_516", bus, {'NEW_SIGNAL_3': 193,
                                                                     'NEW_SIGNAL_4': 195,
                                                                     'NEW_SIGNAL_1': 3,                                                                    
                                                                     'NEW_SIGNAL_6': 4096,
                                                                     'COUNTER':self.idx_2})) # 1302
        if bus == 0:
          can_sends.append(self.packer.make_can_msg("METER_52A", bus, {'NEW_SIGNAL_4': 4,
                                                                       'COUNTER':self.idx_2})) # 1322
          can_sends.append(self.packer.make_can_msg("EPS_MAYBE_551", bus, {'NEW_SIGNAL_4': 4,
                                                                           'COUNTER':self.idx_2})) # 1361
          can_sends.append(self.packer.make_can_msg("SRS_555", bus, {'NEW_SIGNAL_4': 4,
                                                                     'COUNTER':self.idx_2})) # 1365
          can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_661", bus, {'COUNTER':self.idx_2})) # 1633
        else:
          can_sends.append(self.packer.make_can_msg("OBD2_METER_510", bus, {'NEW_SIGNAL_6': 1,
                                                                            'NEW_SIGNAL_11': 1,
                                                                            'NEW_SIGNAL_10': 1,
                                                                            'COUNTER':self.idx_2})) # 1296
      self.idx_2 = (self.idx_2+1) % 4

    ###### 1hz #####
    if (self.frame % 100) == 0:
      bus = 0
      can_sends.append(self.packer.make_can_msg("VSA_590", bus, {'NEW_SIGNAL_4': 4,
                                                                 'COUNTER':self.idx_1})) # 1424
      can_sends.append(self.packer.make_can_msg("RADAR_640", bus, {'NEW_SIGNAL_3': 170,
                                                                   'NEW_SIGNAL_4': 112,
                                                                   'NEW_SIGNAL_5': 18,
                                                                   'NEW_SIGNAL_6': 6,
                                                                   'COUNTER':self.idx_1})) # 1600
      # TODO SEND ACCORDS FRAME LIST
      can_sends.append(self.packer.make_can_msg("RADAR_641", bus, {'NEW_SIGNAL_1': 5,
                                                                   'COUNTER':self.idx_1})) # 1601
      if self.carType == 'CRV':
        can_sends.append(self.packer.make_can_msg("CRV_IDK_652", bus, {'NEW_SIGNAL_4': 4,
                                                                       'COUNTER':self.idx_1})) # 1618
      self.idx_1 = (self.idx_1+1) % 4

    if len(can_sends):
      self.pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan', valid=True))

    return

def nav_thread():
  can_sock = messaging.sub_sock('can')
  fake_car = FakeHonda()
  while 1:
    get_one_can(can_sock)
    fake_car.send()
    fake_car.frame += 1

if __name__ == '__main__':
  nav_thread()