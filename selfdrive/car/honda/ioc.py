from selfdrive.car.honda.hondacan import bcm_io_over_can
from cereal import log, body, car
from opendbc.can.packer import CANPacker

# TODO: Make platform agnostic. Generate all of this file in openioc

# 10ms is a typical response time
MAX_SEND_CNT = 4 * 10

Desire = log.LateralPlan.Desire
IoCState = body.BodyState.IocState.State
Event = car.CarEvent.EventName

class IOC():
  class Command():
    # A minimal safe command set
    # command_id, control_type
    Cancel = [0x0, 0x0]
    SignalLeft = [0x0a, 0x0f]
    SignalRight = [0x0b, 0x0f]
    SignalHazards = [0x08, 0x0f]
    DomeLight = [0x02, 0x1e]

  class MsgType():
    Start = 0x30
    Stop = 0x20
    Started = 0x70
    Stopped = 0x60
    Failed = 0x7f

class IOCController(IOC):
  def __init__(self, dbc_name, CP):
    self.state = IoCState.stopping
    self.sendCnt = 0
    self.packer = CANPacker(dbc_name)

    # adaptive signal timing
    # self.turnSignalOnPeriod = 0.0
    # self.turnSignalOffPeriod = 0.0

  def append(self, idx, cmd_type, cmd_id, commands):
    if idx % 10 == 0:
      return commands.append([cmd_type, cmd_id])

  def update(self, frame, CS, LateralDesire, DM, BD=None, BS=None):
    if CS is None or Desire is None or DM is None:
      return

    # Permanent lockout
    if self.sendCnt >= MAX_SEND_CNT:
      self.state = IoCState.lockout

    # Debug
    if self.state == IoCState.lockout:
      print('No response from BCM. lockout!')

    # TODO: control each flash
    # TODO: interior lights + hazards on terminal DM
    # TODO: gateway firmware
    # # TODO: support multiple commands
    ret = []
    commands = []
    # # TODO: check that our last command is the one the is being acknowledged (BD.BS.iocFeedback[0])
    active = LateralDesire != Desire.none

    # ready the state machine to send
    if active and self.state == IoCState.idle:
      self.state = IoCState.starting
    if not active and self.state == IoCState.userOverride:
      self.state = IoCState.idle

    if frame % 10 == 0 and self.state != 0:
      print('state: ', end=''), print(self.state)

    # send the ioc command
    if self.state == IoCState.starting:
      if CS.iocFeedback['D0'] == IOC.MsgType.Started:
        self.state = IoCState.waiting
        self.sendCnt = 0
      else:
        self.sendCnt +=1
        # TODO: check elapsed time since sent vs reply
        # TODO: combine this with the user override check
        if LateralDesire in [Desire.turnLeft, Desire.laneChangeLeft, Desire.keepLeft]:
          self.append(frame, IOC.MsgType.Start, IOC.Command.SignalLeft, commands)
        elif LateralDesire in [Desire.turnRight, Desire.laneChangeRight, Desire.keepRight]:
          self.append(frame, IOC.MsgType.Start, IOC.Command.SignalRight, commands)
        else:
          pass

    if not active and self.state in [IoCState.starting, IoCState.waiting]:
      self.state = IoCState.stopping

    # check for user override
    if self.state in [IoCState.starting, IoCState.waiting]:
      if LateralDesire in [Desire.turnLeft, Desire.laneChangeLeft, Desire.keepLeft] and CS.out.rightBlinker or \
        LateralDesire in [Desire.turnRight, Desire.laneChangeRight, Desire.keepRight] and CS.out.leftBlinker:
        self.state = IoCState.userOverride
      if [Event.driverDistracted, Event.driverUnresponsive] in DM.events:
        self.state = IoCState.driverUnresponsive

    # waiting to cancel
    if self.state == IoCState.waiting:
      if not active:
        self.state = IoCState.stopping

    # cancelling / handle user override
    if self.state in [IoCState.stopping, IoCState.userOverride]:
      if CS.iocFeedback['D0'] == IOC.MsgType.Stopped:
        self.sendCnt = 0
        # if userOverride, don't resignal until state goes back to idle
        if self.state == IoCState.stopping:
          self.state = IoCState.idle
      else:
        # This cancels ALL active tests per module
        self.sendCnt +=1
        self.append(frame, IOC.MsgType.Stop, IOC.Command.Cancel, commands)

    if self.sendCnt > 1:
      print("self.sendCnt: ", end=''),print(self.sendCnt)
      print('state: ', end=''), print(self.state)

    if commands:
      for msg in commands:
        ret.append(bcm_io_over_can(self.packer, msg))

    return ret, bool(self.state == IoCState.lockout)
