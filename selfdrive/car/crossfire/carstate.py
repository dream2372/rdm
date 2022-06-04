from cereal import car
from collections import defaultdict, deque
from common.numpy_fast import interp
from opendbc.can.can_define import CANDefine
from opendbc.can.parser import CANParser
from selfdrive.config import Conversions as CV
from selfdrive.car.interfaces import CarStateBase
from selfdrive.car.crossfire.values import CAR, DBC
from selfdrive.car.honda.body import get_body_parser

import cereal.messaging as messaging


TransmissionType = car.CarParams.TransmissionType

TONE_WHEEL_CNT = 48
TIRE_SIZE = 29 # inches
WHEEL_UPDATE_FREQ = 50 #hz
# degrees in circle / encoder counts
DEG_PER_TICK = 360 / TONE_WHEEL_CNT

MPH_DEG = 4.375
rpm_to_radians = 0.10471975512


class Wheel():
  def __init__(self, tiresize, updatefreq):
    self.cnts = deque([0], maxlen=WHEEL_UPDATE_FREQ)
    self.speeds = deque([0], maxlen=WHEEL_UPDATE_FREQ)
    self.update_freq = updatefreq
    self.tire_size = TIRE_SIZE
    self.tone_cnt = TONE_WHEEL_CNT
    self.circumference = 2 * 3.14 * (self.tire_size / 2)
    self.in_per_cnt = self.circumference / self.tone_cnt

  def update(self, cnt):
    cnts_moved = 0
    if cnt > self.cnts[-1]:
      cnts_moved = cnt - self.cnts[-1]
    if cnt < self.cnts[-1]:
      cnts_moved = 256 - self.cnts[-1] + cnt
    # print(self.cnts[-1], end=' ')
    # print(cnt)
    # print(self.cnts)

    inches_rotated = cnts_moved * self.in_per_cnt
    # print(inches_rotated, end=' ')
    # print(full_rotations, end=' ')
    if cnts_moved != 0:
      self.speeds.append((inches_rotated * 1.578283e-5) *  (WHEEL_UPDATE_FREQ * 60 * 60) * CV.MPH_TO_MS)
      self.cnts.append(cnt)
      speed = 0.
      for i in range(-len(self.speeds), -1+1):
        speed += self.speeds[i]
        # print(self.speeds[i])
      speed = speed / max(WHEEL_UPDATE_FREQ, len(self.speeds))
    else:
      speed = self.speeds[-1]
      # return avg speed over last 10 samples
      # print(speed)
    return speed


def get_can_signals(CP):
  signals = [
    ("LF", "WHEELS_LEFT"),
    ("LR", "WHEELS_LEFT"),
    ("RF", "WHEELS_RIGHT"),
    ("RR", "WHEELS_RIGHT"),
    ("GEAR_ASCII", "TRANS_1"),
    ("USER_BRAKE_1", "BRAKE_1"),
    ("USER_BRAKE_2", "BRAKE_1"),
    ("DRIVERS_DOOR_OPEN", "BCM_1"),
    ("CRUISE_ON", "GAS_1"),
    ("STEER_ANGLE","STEER_1"),
    ("STEER_DIR", "STEER_1"),
  ]

  checks = [
    ("TRANS_1", 50),
    ("BRAKE_1", 50),
    ("BCM_1", 10),
    ("GAS_1", 50),
    ("WHEELS_LEFT", 50),
    ("WHEELS_RIGHT", 50),
    ("STEER_1", 50),
  ]

  # add gas interceptor reading if we are using it
  if CP.enableGasInterceptor:
    signals.append(("INTERCEPTOR_GAS", "GAS_SENSOR"))
    signals.append(("INTERCEPTOR_GAS2", "GAS_SENSOR"))
    checks.append(("GAS_SENSOR", 50))

  return signals, checks


class CarState(CarStateBase):
  def __init__(self, CP):
    super().__init__(CP)
    can_define = CANDefine(DBC[CP.carFingerprint]["pt"])
    self.frame = 0

    self.cruise_speed_prev = 0
    self.steer_angle_prev = 0.

    self.LF_wheel = Wheel(TIRE_SIZE,WHEEL_UPDATE_FREQ)
    self.RF_wheel = Wheel(TIRE_SIZE,WHEEL_UPDATE_FREQ)
    self.LR_wheel = Wheel(TIRE_SIZE,WHEEL_UPDATE_FREQ)
    self.RR_wheel = Wheel(TIRE_SIZE,WHEEL_UPDATE_FREQ)

    self.gps = messaging.sub_sock('gpsLocationExternal')


  def update(self, cp, cp_cam, cp_body):
    ret = car.CarState.new_message()
    self.frame += 1
    # car params
    v_weight_v = [0., 1.]  # don't trust smooth speed at low values to avoid premature zero snapping
    v_weight_bp = [1., 6.]   # smooth blending, below ~0.6m/s the smooth speed snaps to zero

    # ******************* parse out can *******************
    ret.doorOpen = bool(cp.vl["BCM_1"]["DRIVERS_DOOR_OPEN"])

    ret.steerError = False
    self.steer_not_allowed = False
    ret.steerWarning = False

    ret.wheelSpeeds = car.CarState.WheelSpeeds.new_message()
    if self.frame % 100 / (1 * .020):
      ret.wheelSpeeds.fl = self.LF_wheel.update(int(cp.vl["WHEELS_LEFT"]["LF"]))
      # ret.wheelSpeeds.fr = ret.wheelSpeeds.fl
      # ret.wheelSpeeds.rl = ret.wheelSpeeds.fl
      # ret.wheelSpeeds.rr = ret.wheelSpeeds.fl
      ret.wheelSpeeds.fr = self.LR_wheel.update(int(cp.vl["WHEELS_LEFT"]["LR"]))
      ret.wheelSpeeds.rl = self.RF_wheel.update(int(cp.vl["WHEELS_RIGHT"]["RF"]))
      ret.wheelSpeeds.rr = self.RR_wheel.update(int(cp.vl["WHEELS_RIGHT"]["RR"]))
      # print(ret.wheelSpeeds.fl)
    v_wheel = (ret.wheelSpeeds.fl + ret.wheelSpeeds.fr + ret.wheelSpeeds.rl + ret.wheelSpeeds.rr) / 4.0
    # print(ret.wheelSpeeds.fl)
    # blend in transmission speed at low speed, since it has more low speed accuracy
    # v_weight = interp(v_wheel, v_weight_bp, v_weight_v)
    ret.vEgoRaw = self.CP.wheelSpeedFactor * v_wheel
    ret.vEgo, ret.aEgo = self.update_speed_kf(ret.vEgoRaw)
    ret.steeringAngleDeg = -cp.vl["STEER_1"]["STEER_ANGLE"] if cp.vl["STEER_1"]["STEER_DIR"] else cp.vl["STEER_1"]["STEER_ANGLE"]

    gps = messaging.recv_sock(self.gps)
    if gps is not None:
      gps_speed = gps.gpsLocationExternal.speed
      print(gps_speed - ret.vEgo)

    gear = chr(int(cp.vl["TRANS_1"]["GEAR_ASCII"]))
    # force disengagement if we've overridden the gear, are in manual mode, or ESP is off
    if gear in ['1', '2', '3', '4', '5']:
      gear = 'S'
    if gear in ['S', 'A', 'C']:
      gear = 'D'
    ret.gearShifter = self.parse_gear_shifter(gear)

    ret.gas = (cp.vl["GAS_SENSOR"]["INTERCEPTOR_GAS"] + cp.vl["GAS_SENSOR"]["INTERCEPTOR_GAS2"]) / 2.
    ret.gasPressed = ret.gas > -50

    # crude. may go false negative
    ret.steeringPressed = ret.steeringAngleDeg != self.steer_angle_prev

    ret.brakePressed = bool(cp.vl["BRAKE_1"]["USER_BRAKE_1"]) or bool(cp.vl["BRAKE_1"]["USER_BRAKE_2"])
    ret.brake = int(ret.brakePressed)
    # hack
    ret.cruiseState.enabled = bool(-cp.vl["GAS_1"]["CRUISE_ON"])
    ret.cruiseState.available = True

    # # if gas override while cruise is engaged, set speed = vego
    # if ret.cruiseState.enabled:
    #   if ret.gasPressed:
    #     ret.cruiseState.speed = ret.vEgo
    #   else:
    #     ret.cruiseState.speed = self.cruise_speed_prev

    # self.cruise_speed_prev = ret.cruiseState.speed
    self.steer_angle_prev = ret.steeringAngleDeg

    return ret

  def get_can_parser(self, CP):
    signals, checks = get_can_signals(CP)
    return CANParser(DBC[CP.carFingerprint]["pt"], signals, checks, 0)
