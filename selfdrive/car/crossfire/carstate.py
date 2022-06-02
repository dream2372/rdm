from cereal import car
from collections import defaultdict
from common.numpy_fast import interp
from opendbc.can.can_define import CANDefine
from opendbc.can.parser import CANParser
from selfdrive.config import Conversions as CV
from selfdrive.car.interfaces import CarStateBase
from selfdrive.car.crossfire.values import CAR, DBC
from selfdrive.car.honda.body import get_body_parser

TransmissionType = car.CarParams.TransmissionType
ROTATION_SCALE_FACTOR  = 1.
# degrees in circle / encoder counts
TONE_WHEEL_CNT = 80
DEGREES_PER_TICK = 360 / TONE_WHEEL_CNT
MPH_DEG = 4.375
rpm_to_radians = 0.10471975512


def speeds_from_encoder(self, lf, lr, rf, rr, d, rate=50, ticks_rotation=255):
  lf_d = lf
  wheelSpeeds = car.CarState.WheelSpeeds.new_message()
  lf_deg = lf % TONE_WHEEL_CNT # = ((lf - self.lf_prev) * DEGREES_PER_TICK) % 360

  if lf_deg - self.lf_prev < 0:
    tone_degs = abs(self.lf_prev - lf_deg - 80)
    x = 1
  else:
    tone_degs = lf_deg - self.lf_prev
    x = 0
  rotation_speed = tone_degs * MPH_DEG
  # print(degs)
  # print(rotation_speed)
  print(lf_deg, end=' ')
  print(self.lf_prev, end=' ')
  print(tone_degs, end=' ')
  print(bool(x))
  # print(rad_seconds, end= ' ')
  # print(self.lf_)
  # rad_fl = deg_fl *
  # print(x)
  wheelSpeeds.fl = rotation_speed
  # print(wheelSpeeds.fl)
  # print(lf + self.lf_prev, end= ' ')
  # print(self.lf_prev)
  wheelSpeeds.fr = wheelSpeeds.fl
  wheelSpeeds.rl = wheelSpeeds.fl
  wheelSpeeds.rr = wheelSpeeds.fl
  self.lf_prev = lf_deg
  self.lr_prev = self.lr_prev + lr
  self.rf_prev = self.rf_prev + rf
  self.rr_prev = self.rr_prev + rr

  return wheelSpeeds


def get_can_signals(CP):
  signals = [
    ("LF", "WHEELS_LEFT"),
    ("LR", "WHEELS_LEFT"),
    ("RF", "WHEELS_RIGHT"),
    ("RR", "WHEELS_RIGHT"),
    # ("STEER_ANGLE", "STEERING_SENSORS"),
    # ("STEER_ANGLE_RATE", "STEERING_SENSORS"),
    # ("STEER_TORQUE_SENSOR", "STEER_STATUS"),
    ("GEAR_ASCII", "TRANS_1"),
    ("USER_BRAKE_1", "BRAKE_1"),
    ("USER_BRAKE_2", "BRAKE_1"),
    # ("CRUISE_BUTTONS", "SCM_BUTTONS"),
    # ("ESP_DISABLED", "VSA_STATUS"),
    ("USER_GAS", "GAS_1"),
    # ("CRUISE_SETTING", "SCM_BUTTONS"),
    # ("CRUISE_SPEED_PCM", "CRUISE"),
    # ("CRUISE_SPEED_OFFSET", "CRUISE_PARAMS"),
    ("DRIVERS_DOOR_OPEN", "BCM_1"),
  ]

  checks = [
    ("TRANS_1", 50),
    ("BRAKE_1", 50),
    ("BCM_1", 10),
    ("GAS_1", 50),
    ("WHEELS_LEFT", 50),
    ("WHEELS_RIGHT", 50),
  ]

  # signals += [("CRUISE_SPEED_PCM", "CRUISE"),
  #             ("CRUISE_SPEED_OFFSET", "CRUISE_PARAMS")]


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

    self.brake_error = False
    self.brake_switch_prev = False
    self.brake_switch_active = False
    self.cruise_setting = 0
    self.v_cruise_pcm_prev = 0

    self.lf_prev = 0.
    self.lr_prev = 0.
    self.rf_prev = 0.
    self.rr_prev = 0.


  def update(self, cp, cp_cam, cp_body):
    ret = car.CarState.new_message()
    self.frame += 1
    # car params
    v_weight_v = [0., 1.]  # don't trust smooth speed at low values to avoid premature zero snapping
    v_weight_bp = [1., 6.]   # smooth blending, below ~0.6m/s the smooth speed snaps to zero

    # update prevs, update must run once per loop
    self.prev_cruise_buttons = self.cruise_buttons
    self.prev_cruise_setting = self.cruise_setting

    # ******************* parse out can *******************
    ret.doorOpen = bool(cp.vl["BCM_1"]["DRIVERS_DOOR_OPEN"])

    ret.steerError = False
    self.steer_not_allowed = False
    ret.steerWarning = False

    # TODO: speed!
    if self.frame % 2 == 0:
      ret.wheelSpeeds = speeds_from_encoder(self,
        cp.vl["WHEELS_LEFT"]["LF"],
        cp.vl["WHEELS_LEFT"]["LR"],
        cp.vl["WHEELS_RIGHT"]["RF"],
        cp.vl["WHEELS_RIGHT"]["RR"],
        26
      )

    v_wheel = (ret.wheelSpeeds.fl + ret.wheelSpeeds.fr + ret.wheelSpeeds.rl + ret.wheelSpeeds.rr) / 4.0

    # blend in transmission speed at low speed, since it has more low speed accuracy
    # v_weight = interp(v_wheel, v_weight_bp, v_weight_v)
    # ret.vEgoRaw = (1. - v_weight) * cp.vl["ENGINE_DATA"]["XMISSION_SPEED"] * CV.KPH_TO_MS * self.CP.wheelSpeedFactor + v_weight * v_wheel
    ret.vEgo, ret.aEgo = self.update_speed_kf(v_wheel)
    #
    # ret.steeringAngleDeg = cp.vl["STEERING_SENSORS"]["STEER_ANGLE"]
    # ret.steeringRateDeg = cp.vl["STEERING_SENSORS"]["STEER_ANGLE_RATE"]

    # self.cruise_setting = cp.vl["SCM_BUTTONS"]["CRUISE_SETTING"]
    # self.cruise_buttons = cp.vl["SCM_BUTTONS"]["CRUISE_BUTTONS"]

    self.park_brake = 0  # TODO

    gear = ascii(cp.vl["TRANS_1"]["GEAR_ASCII"])
    ret.gearShifter = self.parse_gear_shifter(gear)

    if self.CP.enableGasInterceptor:
      ret.gas = (cp.vl["GAS_SENSOR"]["INTERCEPTOR_GAS"] + cp.vl["GAS_SENSOR"]["INTERCEPTOR_GAS2"]) / 2.
    else:
      ret.gas = 0
    ret.gasPressed = ret.gas > 1e-5

    # ret.steeringPressed = abs(ret.steeringTorque) > STEER_THRESHOLD.get(self.CP.carFingerprint, 1200)
    # ret.cruiseState.speed = cp.vl["CRUISE"]["CRUISE_SPEED_PCM"] * CV.KPH_TO_MS
    ret.brakePressed = bool(cp.vl["BRAKE_1"]["USER_BRAKE_1"]) or bool(cp.vl["BRAKE_1"]["USER_BRAKE_2"])
    ret.brake = int(ret.brakePressed)
    # ret.cruiseState.enabled = cp.vl["POWERTRAIN_DATA"]["ACC_STATUS"] != 0
    ret.cruiseState.available = True

    return ret

  def get_can_parser(self, CP):
    signals, checks = get_can_signals(CP)
    return CANParser(DBC[CP.carFingerprint]["pt"], signals, checks, 0)
