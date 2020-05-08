#!/usr/bin/env python3
from common.params import Params
from common.realtime import sec_since_boot
from selfdrive.boardd.boardd import can_list_to_can_capnp
import cereal.messaging as messaging
import time
from selfdrive.bodyd.lib.bodyd_helpers import load_body, is_offroad, get_fingerprint


class BodyD:
  """Class to communicate with the car's body functions when offroad."""

  def __init__(self, CP):
    self.params = Params()
    self.supported = None
    self.offroad = False
    self.busAwake = False
    self.busTime = 0
    self.busWakeCount = 0

    self.currentCommand = None

    self.CP = CP
    self.BD = None
    self.BS = None
    # gets deleted after each use
    self.cm = None
    # body.py for our car
    Body, Ioc = load_body(self.CP)
    # no ioc offroad yet
    del Ioc

    if Body is None:
      return

    self.BD = Body(self.CP)
    self.IOC = None

    # setup sockets
    self.offroad_can = self.params.get("AF_OffroadCAN") == b"1"
    self.pm = messaging.PubMaster(['bodyState'])

    if not len(self.CP.carFingerprint) == 0 and self.BD:
      self.can_sock = messaging.sub_sock('can', timeout=100)
      self.sm = messaging.SubMaster(['clocks', 'bodyControl', 'can'])

    return

  def send_can(self, msg):
    if msg is None:
      return
    can_sends = []
    can_sends.append(msg)
    self.cm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan', valid=True))

  def wake_bus(self):
    if not self.busAwake:
      if self.busWakeCount < 12:
        self.busWakeCount += 1
        msg = self.BD.CAN.wakeup
        return msg
      #else:
        #self.currentCommand = None

  def update_pub_bodystate(self):
    # 100hz onroad. 10hz offroad.
    timeout = 10 if self.offroad else 100

    self.sm.update(timeout)

    if self.offroad:
      if self.offroad_can:
        if self.sm.updated['bodyControl']:
          self.currentCommand = self.sm['bodyControl'].command
          print(self.currentCommand)
        self.bodycontrol()
    can_strings = messaging.drain_sock_raw(self.can_sock)
    if can_strings and len(self.sm['can']) > 0:
      self.busTime = sec_since_boot()
      self.BD.cp_body.update_strings(can_strings)
      self.BS = self.BD.update(self.CP, self.BD.cp_body)

    # must see one can frame before sending
    if self.BS is not None:
      bs = messaging.new_message('bodyState')
      bs.bodyState = self.BS
      bs.bodyState.busAwake = self.busAwake

      self.pm.send('bodyState', bs)

  def bodycontrol(self):
    if self.currentCommand is not None and self.offroad:
      if self.cm is None:
        self.cm = messaging.PubMaster(['sendcan'])
        time.sleep(1)
      if not self.busAwake:
        print('bus asleep')
        self.send_can(self.wake_bus())
        time.sleep(0.05)
      else:
        print('bus awake')
        self.busWakeCount = 0
        # use something else to determine these
        if self.currentCommand  == 1:
          print('unlock')
          self.send_can(self.BD.SecurityControl.doorUnlockAll)
        if self.currentCommand == 2:
          print('locking')
          self.send_can(self.BD.SecurityControl.doorLockAll)
        self.currentCommand = None
        del self.cm
        self.cm = None

  def bodyd_thread(self):
    while 1:
      time.sleep(0.01)
      t = sec_since_boot()

      self.offroad = is_offroad(self.params)
      self.busAwake = (t - self.busTime) < 0.1
      self.update_pub_bodystate()

def main():
  while 1:
    CP = get_fingerprint()
    b = BodyD(CP)
    if b.BD is None:
      print("bodyd: Car not recognized. Start vehicle. Retrying in 5 seconds")
      time.sleep(5)
    else:
      b.bodyd_thread()


if __name__ == "__main__":
    main()
