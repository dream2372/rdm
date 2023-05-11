#!/usr/bin/env python3

import cereal.messaging as messaging
from opendbc.can.packer import CANPacker
from selfdrive.boardd.boardd import can_list_to_can_capnp
# from common.numpy_fast import clip

# 4650 works but is A LOT. A max of 3500 is reasonable with no push rod load. 
# With load, high values like these could damage the booster. It only seems to have brown out protection.
BRAKE_RATE_LIMIT = 200


class IBoosterController:
  def __init__(self, can_sock=None):
    self.frame = 0
    self.packer = CANPacker('honda_ibooster')
    # self.parser = CANParser('honda_ibooster')
    self.can_sock = can_sock if can_sock is not None else messaging.sub_sock('can')
    self.pm = messaging.PubMaster(['sendcan'])

    self.ignition = False

    # zero speed after hitting the travel out of bounds results in travel limited again
    self.speed = 256. # set to 0. kph later. This gets rid of the limited travel in CAN control mode

    self.braking = False
    self.computer_brake = 0

    self.idx_100 = 0
    self.idx_50 = 0


  def get_speed(self):
    # Send non-zero speed for a few frames at bootup, otherwise user travel is severely limited.
    if self.frame == 5: # frame 3 seems to work okay too
      self.speed = 0.
    return self.speed


  def get_computer_brake(self):
    print(f'braking on: {self.braking}', end=' ')
    print(self.computer_brake)
    return self.computer_brake
  

  def send(self):
    can_sends = []

    ### This is where the magic happens ###
    command_values = {'SPEED': self.get_speed(),
                      'SET_1_0': 1,
                      'COMPUTER_BRAKE': self.get_computer_brake(),
                      'COMPUTER_BRAKE_REQUEST': self.braking,
                      'COUNTER':self.idx_100}
    
    can_sends.append(self.packer.make_can_msg("VSA_IBOOSTER_COMMAND", 0, command_values)) # 232 @ 100hz

    ### The rest is fluff ###
    # REQUIRED on bus 0 TO NOT SET PCM LOSS DTC.
    can_sends.append(self.packer.make_can_msg("PCM_GATEWAYFORWARD_POWERTRAIN_DATA", 0, {#'BOH_17C': 1,
                                                                                            'COUNTER':self.idx_100})) # 380 @ 100hz
    can_sends.append(self.packer.make_can_msg("VSA_C7", 0, {#'IGN':int(self.ignition),
                                                              # 'NEW_SIGNAL_3': 24,
                                                              # 'NEW_SIGNAL_5': 1,
                                                              # 'WTF_IS_THIS': 2,
                                                              'COUNTER':self.idx_100})) # 199 @ 100hz

    self.idx_100 = (self.idx_100+1) % 4

    if (self.frame % 2) == 0:
      can_sends.append(self.packer.make_can_msg("VSA_WHEEL_TICKS", 0, {'COUNTER':self.idx_50})) # 441 @ 50hz
      self.idx_50 = (self.idx_50+1) % 4

    ### End Fluff ###

    if len(can_sends):
      self.pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan', valid=True))
    return


  def update(self, CC=None):
    self.send()
    # TODO: read can for lockouts, faults, travel out of bounds, etc
    # update sockets
    # self.sm.update(0)
    # self.braking = bool(CC.actuators.accel < 0.)
    # self.computer_brake = clip(int(self.brake_rate * clip(self.sm['testJoystick'].axes[0], -1, 1)), -3500, 3500)