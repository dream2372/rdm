#!/usr/bin/env python3

import cereal.messaging as messaging
from selfdrive.boardd.boardd import can_list_to_can_capnp
import time


packer = ()

def FakeHonda(pm, frame, idx):
  can_sends = []
  ###### 100hz #####
  for bus in [0,2]:
    # can_sends.append(packer.make_can_msg("SRS_KINEMATICS", bus, {})) # 148
    can_sends.append(packer.make_can_msg("PCM_METERFORWARD_GAS_PEDAL_2", bus, {})) # 304
    # can_sends.append(packer.make_can_msg("EPS_STEERING_SENSORS_A", bus, {})) # 330
    can_sends.append(packer.make_can_msg("TCM_METERFORWARD_ENGINE_DATA", bus, {})) # 344
    # can_sends.append(packer.make_can_msg("PCM_METERFORWARD_POWERTRAIN_DATA", bus, {})) # 380
    # can_sends.append(packer.make_can_msg("TCM_METERFORWARD_GEARBOX_CVT", bus, {})) # 401
    if bus == 0:
      # bus 0
      can_sends.append(packer.make_can_msg("RADAR_STEERING_CONTROL", 0, {})) # 228
      can_sends.append(packer.make_can_msg("VSA_IBOOSTER_COMMAND", 0, {})) # 232
      # 340 not found
      # can_sends.append(packer.make_can_msg("EPS_STEER_STATUS", 0, {})) # 399
    else:
      # bus 2
      # can_sends.append(packer.make_can_msg("VSA_C7", 2, {})) # 199
      pass

  ###### 50hz #####
  if (frame % 2) == 0:
    for bus in [0,2]:
      # can_sends.append(packer.make_can_msg("VSA_STATUS", bus, {})) # 420
      can_sends.append(packer.make_can_msg("OBD2_TCM_1A7", bus, {})) # 423
      can_sends.append(packer.make_can_msg("VSA_STANDSTILL", bus, {})) # 432
      # can_sends.append(packer.make_can_msg("VSA_METERFORWARD_EPB_STATUS", bus, {})) # 450
      # can_sends.append(packer.make_can_msg("VSA_WHEEL_SPEEDS", bus, {})) # 464
      # can_sends.append(packer.make_can_msg("RADAR_ACC_CONTROL", bus, {})) # 479
      can_sends.append(packer.make_can_msg("RADAR_ACC_CONTROL_ON", bus, {})) # 495
      if bus == 0:
        can_sends.append(packer.make_can_msg("VSA_WHEEL_TICKS", bus, {})) # 441
        # can_sends.append(packer.make_can_msg("PCM_METERFORWARD_1DD", bus, {})) # 477
        can_sends.append(packer.make_can_msg("VSA_KINEMATICS", bus, {})) # 490
      else:
        can_sends.append(packer.make_can_msg("VSA_METERFORWARD_1AC", bus, {})) # 428
        can_sends.append(packer.make_can_msg("PCM_METERFORWARD_1D6", bus, {})) # 470
        can_sends.append(packer.make_can_msg("PCM_METERFORWARD_ENGINE_DATA_2", bus, {})) # 476
        can_sends.append(packer.make_can_msg("PCM_METERFORWARD_ACC_CONTROL_ON_2", bus, {})) # 493
        can_sends.append(packer.make_can_msg("OBD2_IDK_1FB", bus, {})) # 507
    
  ###### 25hz #####
  if (frame % 4) == 0:
    for bus in [0,2]:
      can_sends.append(packer.make_can_msg("METER_221", bus, {})) # 545
      # can_sends.append(packer.make_can_msg("SRS_39", bus, {})) # 57
      # can_sends.append(packer.make_can_msg("VSA_ROUGH_WHEEL_SPEED", bus, {})) # 597
      can_sends.append(packer.make_can_msg("METER_SCM_BUTTONS", bus, {})) # 662
      if bus == 2:
        # 661 not found
        pass
    
  ###### 10hz #####
  if (frame % 10) == 0:
    for bus in [0,2]:
      # can_sends.append(packer.make_can_msg("SRS_SEATBELT_STATUS", bus, {})) # 773
      can_sends.append(packer.make_can_msg("METER_CAR_SPEED", bus, {})) # 777
      can_sends.append(packer.make_can_msg("RADAR_ACC_HUD", bus, {})) # 780
      can_sends.append(packer.make_can_msg("PCM_METERFORWARD_320", bus, {})) # 800
      # can_sends.append(packer.make_can_msg("PCM_METERFORWARD_CRUISE", bus, {})) # 804
      # can_sends.append(packer.make_can_msg("METER_SCM_FEEDBACK", bus, {})) # 806
      can_sends.append(packer.make_can_msg("PCM_METERFORWARD_328", bus, {})) # 808
      # can_sends.append(packer.make_can_msg("RADAR_LKAS_HUD", bus, {})) # 829
      # can_sends.append(packer.make_can_msg("CAMERA_MESSAGES", bus, {})) # 862
      # can_sends.append(packer.make_can_msg("METER_STALK_STATUS", bus, {})) # 884
      can_sends.append(packer.make_can_msg("METER_STALK_STATUS_2", bus, {})) # 891
      # can_sends.append(packer.make_can_msg("RADAR_HUD", bus, {})) # 927
      if bus == 2:
        # can_sends.append(packer.make_can_msg("VSA_METERFORWARD_31B", bus, {})) # 795
        can_sends.append(packer.make_can_msg("OBD2_PCM_32F", bus, {})) # 815
        can_sends.append(packer.make_can_msg("OBD2_PCM_339", bus, {})) # 825
        can_sends.append(packer.make_can_msg("OBD2_METER_371", bus, {})) # 881
        can_sends.append(packer.make_can_msg("OBD2_METER_372", bus, {})) # 882
        # can_sends.append(packer.make_can_msg("OBD2_METER_378", bus, {})) # 888
        # can_sends.append(packer.make_can_msg("OBD2_METER_396", bus, {})) # 918
    
  ###### 5hz #####
  # if (frame % 20) == 0:
    # for bus in [0,2]:
    #   can_sends.append(packer.make_can_msg("METER_3A1", bus, {})) # 929
    #   if bus == 0:
    #     can_sends.append(packer.make_can_msg("VSA_3D9", bus, {})) # 985
    #   else:
    #     can_sends.append(packer.make_can_msg("OBD2_PCM_3D7", bus, {})) # 983
  ###### 3hz #####
  if (frame % 33) == 0:
    for bus in [0,2]:
      # can_sends.append(packer.make_can_msg("TCM_METERFORWARD_403", bus, {})) # 1027
      can_sends.append(packer.make_can_msg("METER_DOORS_STATUS", bus, {})) # 1029
      # can_sends.append(packer.make_can_msg("PCM_METERFORWARD_40C", bus, {})) # 1036
      # can_sends.append(packer.make_can_msg("TCM_METERFORWARD_40F", bus, {})) # 1039
      can_sends.append(packer.make_can_msg("NEW_MSG_445", bus, {})) # 1093
      can_sends.append(packer.make_can_msg("PCM_METERFORWARD_454", bus, {})) # 1108
    if bus == 0:
      can_sends.append(packer.make_can_msg("PCM_METERFORWARD_400", bus, {})) # 1024
    else:
      can_sends.append(packer.make_can_msg("OBD2_METER_428", bus, {})) # 1064
      can_sends.append(packer.make_can_msg("OBD2_METER_444", bus, {})) # 1092
      # can_sends.append(packer.make_can_msg("OBD2_IDK_45B", bus, {})) # 1115
      can_sends.append(packer.make_can_msg("OBD2_PCM_465", bus, {})) # 1125
      can_sends.append(packer.make_can_msg("OBD2_PCM_467", bus, {})) # 1127
  ###### 2hz #####
  if (frame % 50) == 0:
    for bus in [0,2]:
      can_sends.append(packer.make_can_msg("METER_516", bus, {})) # 1302
    if bus == 0:
      can_sends.append(packer.make_can_msg("METER_52A", bus, {})) # 1322
      can_sends.append(packer.make_can_msg("EPS_MAYBE_551", bus, {})) # 1361
      can_sends.append(packer.make_can_msg("SRS_555", bus, {})) # 1365
      can_sends.append(packer.make_can_msg("PCM_METERFORWARD_661", bus, {})) # 1633
    else:
      can_sends.append(packer.make_can_msg("OBD2_METER_510", bus, {})) # 1296
  ###### 1hz #####
  if (frame % 100) == 0:
    can_sends.append(packer.make_can_msg("VSA_590", bus, {})) # 1424
    # can_sends.append(packer.make_can_msg("RADAR_640", bus, {})) # 1600
    # can_sends.append(packer.make_can_msg("RADAR_641", bus, {})) # 1601
    can_sends.append(packer.make_can_msg("NEW_MSG_652", bus, {})) # 1618


    # if idx == 0:
    #   can_sends.append(NAV_C_1_0)
    # elif idx == 1:
    #   can_sends.append(NAV_C_1_1)
    # elif idx == 2:
    #   can_sends.append(NAV_C_1_2)
    # else:
    #   can_sends.append(NAV_C_1_3)


    # # tick counter
    idx = (idx+1) % 4

  if len(can_sends) != 0:
    # print(can_sends)
    pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan', valid=True))

  return idx

def nav_thread():
    idx = 0
    frame = 0

    pm = messaging.PubMaster(['sendcan'])

    while 1:
      # 100hz loop
      frame += 1
      idx = FakeHonda(pm, frame, idx)
      time.sleep(0.01)

if __name__ == '__main__':
  nav_thread()