#!/usr/bin/env python3

import cereal.messaging as messaging
from opendbc.can.packer import CANPacker
from selfdrive.boardd.boardd import can_list_to_can_capnp
from selfdrive.car.car_helpers import get_one_can
    

class FakeHonda:
  def __init__(self):

    self.frame = 0
    self.packer = CANPacker('HONDA_MASTER')
    self.pm = messaging.PubMaster(['sendcan'])

    # Initial values
    self.braking = False
    self.computer_brake = 0
    # zero speed after hitting the travel out of bounds results in travel limited again
    self.speed = 256. # set to 0. kph later. This gets rid of the limited travel in CAN control mode

    self.ignition = False

    self.idx_100 = 0
    self.idx_50 = 0

    self.brake_rate = 1000 # what's the unit?
  
  def get_computer_brake(self):
    if self.frame == 5: # frame 3 seems to work okay
      self.speed = 0.
    # Wait 3 seconds for the init to finish
    # if self.frame == 1300:
    #   # reset
    #   self.frame = 0
    # elif self.frame > 1100:
    #   self.braking = False
    #   self.computer_brake = 0
    # elif self.frame > 1000:
    #   self.computer_brake = -1000
    if self.frame == 999:
      self.frame = 0
    elif self.frame == 800:
      self.computer_brake = 0
      print('stop')
    elif self.frame == 700:
      self.computer_brake = -500
      print('out') 
    elif self.frame == 500:
      self.computer_brake = 0
      print('stop')
    elif self.frame == 400:
      self.computer_brake = 500
      print('in')

    elif self.frame == 300:
      self.braking = True
      self.computer_brake = 50 #brake_range[(self.frame - 300) % len(brake_range)] # 3500 is near max. 4000 is too much
    # print(self.frame)
    elif self.frame == 1:
      self.braking = False
      self.computer_brake = -3000
    return self.computer_brake
    

  def send(self, command=True):
    can_sends = []

    ###### 100hz #####
    # REQUIRED on bus 0 TO NOT SET PCM LOSS DTC
    can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_POWERTRAIN_DATA", 0, {#'BOH_17C': 1,
                                                                                            'COUNTER':self.idx_100})) # 380
    # REQUIRED on bus 0 for CAN control
    can_sends.append(self.packer.make_can_msg("VSA_C7", 0, {#'IGN':int(self.ignition),
                                                              # 'NEW_SIGNAL_3': 24,
                                                              # 'NEW_SIGNAL_5': 1,
                                                              # 'WTF_IS_THIS': 2,
                                                              'COUNTER':self.idx_100})) # 199
    # REQUIRED on bus 0 for CAN control, DUH
    if command:
      can_sends.append(self.packer.make_can_msg("VSA_IBOOSTER_COMMAND", 0, {'XMISSION_SPEED2_SMOOTHED': self.speed,
                                                                            'SET_1_0': 1,
                                                                            'COMPUTER_BRAKE': self.get_computer_brake(),
                                                                            'COMPUTER_BRAKE_REQUEST': self.braking,
                                                                            'COUNTER':self.idx_100})) # 232
     
    self.idx_100 = (self.idx_100+1) % 4

    ###### 50hz #####
    if (self.frame % 2) == 0:
      # REQUIRED on bus 2 for CAN control
      can_sends.append(self.packer.make_can_msg("VSA_WHEEL_TICKS", 2, {'COUNTER':self.idx_50})) # 441
      self.idx_50 = (self.idx_50+1) % 4

    if command:
      if len(can_sends):
        self.pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan', valid=True))
      return
    else:
      return can_sends

def nav_thread():
  can_sock = messaging.sub_sock('can')
  fake_car = FakeHonda()
  while 1:
    get_one_can(can_sock)
    fake_car.send()
    fake_car.frame += 1

if __name__ == '__main__':
  nav_thread()