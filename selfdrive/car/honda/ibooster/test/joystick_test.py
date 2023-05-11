#!/usr/bin/env python3

import cereal.messaging as messaging
from opendbc.can.packer import CANPacker
from selfdrive.boardd.boardd import can_list_to_can_capnp
from selfdrive.car.car_helpers import get_one_can
from common.numpy_fast import clip
    

# The accel stick determines what direction and how quickly
# The steer stick increases or decreases the rate
# The cancel button must be held to enable control

class FakeHonda:
  def __init__(self, can_sock=None):

    self.frame = 0
    self.packer = CANPacker('HONDA_MASTER')
    self.can_sock = can_sock if can_sock is not None else None
    self.sm = messaging.SubMaster(['testJoystick'])
    self.pm = messaging.PubMaster(['sendcan'])

    self.braking = False
    self.computer_brake = 0
    # zero speed after hitting the travel out of bounds results in travel limited again
    self.speed = 256. # set to 0. kph later. This gets rid of the limited travel in CAN control mode
    self.ignition = False

    self.idx_100 = 0
    self.idx_50 = 0

    self.brake_rate = 1 # 4650 is A LOT. max of 3500 is reasonable with no push rod load. real limit is probably much lower IRL

  def get_speed(self):
    if self.frame == 5: # frame 3 seems to work okay too
      self.speed = 0.
    return self.speed


  def get_computer_brake(self):
    print(f'braking on: {self.braking}', end=' ')
    print(self.computer_brake, end=' ')
    print(self.brake_rate)
    return self.computer_brake
    

  def send(self, command=True):
    can_sends = []

    # update sockets
    self.sm.update(0)

    if self.sm.rcv_frame['testJoystick'] > 0:
      self.braking = bool(self.sm['testJoystick'].buttons[0])
      right = clip(self.sm['testJoystick'].axes[1], -1, 1)
      if right > 0:
        self.brake_rate = clip(self.brake_rate + 25, -3500, 3500)
      if right < 0:
        self.brake_rate = clip(self.brake_rate - 25, -3500, 3500)

      self.computer_brake = clip(int(self.brake_rate * clip(self.sm['testJoystick'].axes[0], -1, 1)), -3500, 3500)

    ###### 100hz #####
    # REQUIRED on bus 0 TO NOT SET PCM LOSS DTC. BRAKE HOLD UNTESTED!
    can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_POWERTRAIN_DATA", 0, {#'BOH_17C': 1,
                                                                                            'COUNTER':self.idx_100})) # 380
    # REQUIRED on bus 0 for CAN control
    # Blank works. BRAKE HOLD UNTESTED!
    can_sends.append(self.packer.make_can_msg("VSA_C7", 0, {#'IGN':int(self.ignition),
                                                              # 'NEW_SIGNAL_3': 24,
                                                              # 'NEW_SIGNAL_5': 1,
                                                              # 'WTF_IS_THIS': 2,
                                                              'COUNTER':self.idx_100})) # 199
    # REQUIRED on bus 0 for CAN control, DUH. BRAKE HOLD UNTESTED!
    if command:
      can_sends.append(self.packer.make_can_msg("VSA_IBOOSTER_COMMAND", 0, {'SPEED': self.get_speed(),
                                                                            'SET_1_0': 1,
                                                                            'COMPUTER_BRAKE': self.get_computer_brake(),
                                                                            'COMPUTER_BRAKE_REQUEST': self.braking,
                                                                            'COUNTER':self.idx_100})) # 232
     
    self.idx_100 = (self.idx_100+1) % 4

    ###### 50hz #####
    if (self.frame % 2) == 0:
      # REQUIRED on bus 2 for CAN control. BRAKE HOLD UNTESTED!
      can_sends.append(self.packer.make_can_msg("VSA_WHEEL_TICKS", 0, {'COUNTER':self.idx_50})) # 441
      # can_sends.append(self.packer.make_can_msg("VSA_WHEEL_TICKS", 2, {'COUNTER':self.idx_50})) # 441
      self.idx_50 = (self.idx_50+1) % 4

    if command:
      if len(can_sends):
        self.pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan', valid=True))
      return
    else:
      return can_sends

def nav_thread():
  can_sock = messaging.sub_sock('can')
  fake_car = FakeHonda(can_sock)
  print('waiting for can...')
  while 1:
    get_one_can(can_sock)
    fake_car.send()
    fake_car.frame += 1

if __name__ == '__main__':
  nav_thread()