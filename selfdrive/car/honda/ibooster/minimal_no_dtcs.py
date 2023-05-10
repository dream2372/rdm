#!/usr/bin/env python3

import cereal.messaging as messaging
from opendbc.can.packer import CANPacker
from selfdrive.boardd.boardd import can_list_to_can_capnp
from selfdrive.car.car_helpers import get_one_can

brake_range = []
rate = 500
step = 10

for a in range(0, rate, step):
    brake_range.append(a)

for b in range(rate, -rate, -step):
    brake_range.append(b)

for c in range(-rate, 0, step):
    brake_range.append(c)
    

class FakeHonda:
  def __init__(self):

    self.idx = 0
    self.frame = 0
    self.packer = CANPacker('HONDA_MASTER')
    self.pm = messaging.PubMaster(['sendcan'])
    self.carType = 'CRV' # or ACCORD

    # Initial values
    self.braking = False
    self.computer_brake = 0
    self.speed = 0.

    self.ignition = True
    self.driver_door = False

    self.idx_100 = 0
    self.idx_50 = 0
    self.idx_25 = 0
    self.idx_10 = 0
    self.idx_5 = 0
    self.idx_3 = 0
    self.idx_2 = 0
    self.idx_1 = 0

    self.brake_rate = 1000 # what's the unit?
  
  def get_computer_brake(self):
    # Wait 3 seconds for the init to finish
    # if self.frame == 1300:
    #   self.frame = 0
    # elif self.frame > 1000:
    #   self.braking = False
    #   self.computer_brake = 0
    if self.frame > 300:
      self.braking = True
      self.computer_brake = brake_range[(self.frame - 300) % len(brake_range)] # 3500 is near max. 4000 is too much
      self.computer_brake = self.computer_brake if self.computer_brake != 0 else -1
    print(self.computer_brake)
    return self.computer_brake
    

  def send(self):
    can_sends = []

    ###### 100hz #####
    # REQUIRED on bus 0 TO NOT SET PCM LOSS DTC
    can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_POWERTRAIN_DATA", 0, {'BOH_17C': 1,
                                                                                            'COUNTER':self.idx_100})) # 380
    # REQUIRED on bus 0 for CAN control
    can_sends.append(self.packer.make_can_msg("VSA_C7", 0, {'IGN':int(self.ignition),
                                                              'NEW_SIGNAL_3': 24,
                                                              'NEW_SIGNAL_5': 1,
                                                              'WTF_IS_THIS': 2,
                                                              'COUNTER':self.idx_100})) # 199
    # REQUIRED on bus 0 for CAN control, DUH
    can_sends.append(self.packer.make_can_msg("VSA_IBOOSTER_COMMAND", 0, {'LIMIT_TRAVEL': 1,
                                                                            'COMPUTER_BRAKE': self.get_computer_brake(),
                                                                            'COMPUTER_BRAKE_REQUEST': self.braking,
                                                                            'COUNTER':self.idx_100})) # 232
     
    self.idx_100 = (self.idx_100+1) % 4

    ###### 50hz #####
    if (self.frame % 2) == 0:
      # REQUIRED on bus 2 for CAN control
      can_sends.append(self.packer.make_can_msg("VSA_WHEEL_TICKS", 2, {'COUNTER':self.idx_50})) # 441
      self.idx_50 = (self.idx_50+1) % 4

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