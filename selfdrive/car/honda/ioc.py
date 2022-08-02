from selfdrive.car.honda.hondacan import bcm_io_over_can
from cereal import log, body, car
from opendbc.can.packer import CANPacker
from selfdrive.config import Conversions as CV
from common.params import Params

# TODO: Make platform agnostic. Generate all of this file in openioc

# 10ms is a typical response time
MAX_SEND_CNT = 4 * 10
MIN_FOG_ANGLE = 35. # deg
FOG_DELAY = 200 # steps

Desire = log.LateralPlan.Desire
IoCState = body.BodyState.IocState.State
Event = car.CarEvent.EventName

# def process_driver(self, DM):
#     DM.events in [Event.driverDistracted, Event.driverUnresponsive]:
#       self.state = IoCState.driverUnresponsive


def process_turn_signals(signal, CS, lateralDesire):
  cmd = []
  # adaptive signal timing
  # self.turnSignalOnPeriod = 0.0
  # self.turnSignalOffPeriod = 0.0
  # left

  print('desire ', end=' '), print(lateralDesire)
  print('blinker_l ', end=' '), print(CS.out.leftBlinker)
  print('blinker_r ', end=' '), print(CS.out.leftBlinker)
  print('state ', end=' '), print(signal.state)

  if lateralDesire in [Desire.turnLeft, Desire.laneChangeLeft, Desire.keepLeft]:
    if CS.out.rightBlinker:
      signal.state = IoCState.userOverride
    elif signal.state == IoCState.idle:
      signal.state = IoCState.starting
      print('Left signal...')
      cmd = signal.start()
  # right
  elif lateralDesire in [Desire.turnRight, Desire.laneChangeRight, Desire.keepRight]:
    if CS.out.leftBlinker:
      signal.state = IoCState.userOverride
    elif signal.state == IoCState.idle:
      signal.state = IoCState.starting
      print('Right signal...')
      cmd = signal.start()
  # cancel
  else:
    if signal.state in [IoCState.starting, IoCState.waiting]:
      signal.state = IoCState.stopping
  return cmd

def process_foglights(fogs, CS, lateralControl):
  cmd = []
  steer_exceeded = ((abs(lateralControl.steeringAngleDesiredDeg) + abs(lateralControl.steeringAngleDeg)) / 2) >= MIN_FOG_ANGLE
  # this should be gated on ambient light too (from car or device)
  lighting_acceptable = CS.lighting_auto and not CS.lighting_fog and CS.lighting_low
  override = not lighting_acceptable or CS.out.vEgo > (fogs.maxSpeed * CV.MPH_TO_MS)
  fog = steer_exceeded and lighting_acceptable and not override
  if fog and fogs.state == IoCState.idle:
      print('Fogging...')
      cmd = fogs.start()
  return cmd

class IOC():
  class Command():
    # A minimal safe command set. Limited in OP's panda
    # command_id, control_type
    Cancel = [0x20, 0x0, 0x0]
    SignalLeft = [0x0, 0x0a, 0x0f]
    SignalRight = [0x0, 0x0b, 0x0f]
    FrontFogLamps = [0x0, 0x20, 0x0f]

    # TODO: implement
    # DomeLight = [0x02, 0x1e]
    # SignalHazards = [0x08, 0x0f]

  class MsgType():
    Start = 0x30
    Stop = 0x20
    Started = 0x70
    Stopped = 0x60
    Failed = 0x7f

  class Function():
    def __init__(self, command, packer, max_speed=0, delayFrames=0, startup_test=False):
      self.command = command
      self.packer = packer
      self.delayFrames = delayFrames # hysteresis for delay

      # always init idle (except CAN tester)
      self.state = IoCState.stopping if startup_test else IoCState.idle
      self.state_last  = None
      self.delay = 0 # at trailing edge of an active state
      self.lastFrame = 0

      self.attempts = 0 # of frames sent to the test module
      self.maxSpeed = max_speed

    def update(self, frame, CS):
      cmd = []

      if self.attempts >= MAX_SEND_CNT and self.state not in [IoCState.lockout, IoCState.unsupported]:
        self.state = IoCState.lockout

      # permanent
      if self.state in [IoCState.lockout, IoCState.unsupported]:
        return cmd

      # time is up. cancelling
      if self.state == IoCState.waiting and self.delayFrames:
        if frame - self.lastFrame > self.delayFrames:
          self.state = IoCState.stopping

      if self.state in [IoCState.stopping, IoCState.userOverride]:
        cmd.append(self.stop())

      # state update

      active = self.state in [IoCState.starting, IoCState.waiting]
      if active:
        if self.state == IoCState.starting:
          if CS.iocFeedback['D0'] == IOC.MsgType.Started and \
             CS.iocFeedback['D1'] == self.command[1] and \
             CS.iocFeedback['D2'] == self.command[2]:
            self.state = IoCState.waiting
      else:
        if self.state not in [IoCState.idle, IoCState.lockout, IoCState.stopping, IoCState.unsupported]:
          self.state = IoCState.stopping
        # cancel / handle user override
        if self.state in [IoCState.stopping, IoCState.userOverride]:
          if CS.iocFeedback['D0'] == IOC.MsgType.Stopped:
            self.state = IoCState.idle
          else:
            # This cancels ALL active tests per module
            cmd.append(self.stop())

      return cmd

    def start(self):
      self.attempts += 1
      return bcm_io_over_can(self.packer, [IOC.MsgType.Start, self.command])

    def stop(self):
      self.attempts += 1
      # appending the command doesn't do anything. for debugging via CAN
      return bcm_io_over_can(self.packer, [IOC.MsgType.Stop, self.command])



class IOCController(IOC):
  def __init__(self, dbc_name):
    packer = CANPacker(dbc_name)
    self.cornering_fogs = IOC.Function(IOC.Command.FrontFogLamps, packer, delayFrames=FOG_DELAY, max_speed=20.) \
                            if Params().get_bool('AF_CorneringFogLights') else None
    self.turn_signal_left = IOC.Function(IOC.Command.SignalLeft, packer) if Params().get_bool('AF_TurnSignalControl') else None
    self.turn_signal_right = IOC.Function(IOC.Command.SignalRight, packer)  if Params().get_bool('AF_TurnSignalControl') else None

  def update(self, frame, CS, lateralDesire, DM, lateralControl):
    commands = []
    lockout = False
    # dirty
    if self.cornering_fogs is not None:
      f = process_foglights(self.cornering_fogs, CS, lateralControl)
      if len(f) != 0:
        commands.append(f)
      self.cornering_fogs.update(frame, CS)
      if self.cornering_fogs.state == IoCState.lockout:
        lockout = True

    if self.turn_signal_left and self.turn_signal_right is not None:
      tl = process_turn_signals(self.turn_signal_left, CS, lateralDesire)
      if len(tl) != 0:
        commands.append(tl)

      tr = process_turn_signals(self.turn_signal_right, CS, lateralDesire)
      if len(tr) != 0:
        commands.append(tr)

      if self.turn_signal_left.state == IoCState.lockout or self.turn_signal_right.state == IoCState.lockout:
        lockout = True


    # TODO: control each flash
    # TODO: interior lights + hazards on terminal DM
    # TODO: gateway firmware

    # lockout variable is for controlsd
    print(commands)
    return commands, lockout

# def test():
#
#
# if __name__ == '__main__':
#   test()
