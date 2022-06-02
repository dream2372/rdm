#!/usr/bin/env python3
from cereal import car
from panda import Panda
from common.numpy_fast import interp
from common.params import Params
from selfdrive.car.crossfire.values import CAR
from selfdrive.car import STD_CARGO_KG, CivicParams, scale_rot_inertia, scale_tire_stiffness, gen_empty_fingerprint, get_safety_config
from selfdrive.car.interfaces import CarInterfaceBase
from selfdrive.car.disable_ecu import disable_ecu
from selfdrive.config import Conversions as CV


ButtonType = car.CarState.ButtonEvent.Type
EventName = car.CarEvent.EventName
TransmissionType = car.CarParams.TransmissionType


class CarInterface(CarInterfaceBase):
  # @staticmethod
  # def get_pid_accel_limits(CP, current_speed, cruise_speed):
  #   if CP.carFingerprint in HONDA_BOSCH:
  #     return CarControllerParams.BOSCH_ACCEL_MIN, CarControllerParams.BOSCH_ACCEL_MAX
  #   else:
  #     # NIDECs don't allow acceleration near cruise_speed,
  #     # so limit limits of pid to prevent windup
  #     ACCEL_MAX_VALS = [CarControllerParams.NIDEC_ACCEL_MAX, 0.2]
  #     ACCEL_MAX_BP = [cruise_speed - 2., cruise_speed - .2]
  #     return CarControllerParams.NIDEC_ACCEL_MIN, interp(current_speed, ACCEL_MAX_BP, ACCEL_MAX_VALS)

  @staticmethod
  def get_params(candidate, fingerprint=gen_empty_fingerprint(), car_fw=[]):  # pylint: disable=dangerous-default-value
    ret = CarInterfaceBase.get_std_params(candidate, fingerprint)
    ret.carName = "crossfire"

    ret.safetyConfigs = [get_safety_config(car.CarParams.SafetyModel.crossfire)]
    ret.radarOffCan = True
    ret.enableGasInterceptor = 0x201 in fingerprint[0]
    ret.openpilotLongitudinalControl = ret.enableGasInterceptor
    ret.pcmCruise = not ret.enableGasInterceptor

    # Certain Hondas have an extra steering sensor at the bottom of the steering rack,
    # which improves controls quality as it removes the steering column torsion from feedback.
    # Tire stiffness factor fictitiously lower if it includes the steering column torsion effect.
    # For modeling details, see p.198-200 in "The Science of Vehicle Dynamics (2014), M. Guiggiani"
    ret.lateralParams.torqueBP, ret.lateralParams.torqueV = [[0], [0]]
    ret.lateralTuning.pid.kiBP, ret.lateralTuning.pid.kpBP = [[0.], [0.]]
    ret.lateralTuning.pid.kf = 0.00006  # conservative feed-forward

    ret.longitudinalTuning.kpV = [0.25]
    ret.longitudinalTuning.kiV = [0.05]
    ret.longitudinalActuatorDelayUpperBound = 0.5 # s

    if candidate == CAR.CROSSFIRE:
      stop_and_go = True
      ret.mass = CivicParams.MASS
      ret.wheelbase = CivicParams.WHEELBASE
      ret.centerToFront = CivicParams.CENTER_TO_FRONT
      ret.steerRatio = 15.38  # 10.93 is end-to-end spec
      ret.lateralParams.torqueBP, ret.lateralParams.torqueV = [[0, 0], [0, 0]]
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.], [0.]]
      tire_stiffness_factor = 1.

    else:
      raise ValueError(f"unsupported car {candidate}")

    ret.minEnableSpeed = -1. if (stop_and_go or ret.enableGasInterceptor) else 100

    # TODO: get actual value, for now starting with reasonable value for
    # civic and scaling by mass and wheelbase
    ret.rotationalInertia = scale_rot_inertia(ret.mass, ret.wheelbase)

    # TODO: start from empirically derived lateral slip stiffness for the civic and scale by
    # mass and CG position, so all cars will have approximately similar dyn behaviors
    ret.tireStiffnessFront, ret.tireStiffnessRear = scale_tire_stiffness(ret.mass, ret.wheelbase, ret.centerToFront,
                                                                         tire_stiffness_factor=tire_stiffness_factor)

    ret.steerActuatorDelay = 0.1
    ret.steerRateCost = 0.5
    ret.steerLimitTimer = 0.8

    return ret

  @staticmethod
  def init(CP, logcan, sendcan):
    pass

  # returns a car.CarState
  def update(self, c, can_strings):
    # ******************* do can recv *******************
    self.cp.update_strings(can_strings)

    ret = self.CS.update(self.cp, self.cp_cam, self.cp_body)

    # TODO: Discover more B-CAN frame timing
    ret.canValid = self.cp.can_valid

    buttonEvents = []

    if self.CS.cruise_buttons != self.CS.prev_cruise_buttons:
      be = car.CarState.ButtonEvent.new_message()
      be.type = ButtonType.unknown
      if self.CS.cruise_buttons != 0:
        be.pressed = True
        but = self.CS.cruise_buttons
      else:
        be.pressed = False
        but = self.CS.prev_cruise_buttons
      if but == CruiseButtons.RES_ACCEL:
        be.type = ButtonType.accelCruise
      elif but == CruiseButtons.DECEL_SET:
        be.type = ButtonType.decelCruise
      elif but == CruiseButtons.CANCEL:
        be.type = ButtonType.cancel
      elif but == CruiseButtons.MAIN:
        be.type = ButtonType.altButton3
      buttonEvents.append(be)

    if self.CS.cruise_setting != self.CS.prev_cruise_setting:
      be = car.CarState.ButtonEvent.new_message()
      be.type = ButtonType.unknown
      if self.CS.cruise_setting != 0:
        be.pressed = True
        but = self.CS.cruise_setting
      else:
        be.pressed = False
        but = self.CS.prev_cruise_setting
      if but == 1:
        be.type = ButtonType.altButton1
      # TODO: more buttons?
      buttonEvents.append(be)
    ret.buttonEvents = buttonEvents

    # events
    events = self.create_common_events(ret, pcm_enable=False)
    if self.CS.brake_error:
      events.add(EventName.brakeUnavailable)
    if self.CS.park_brake:
      events.add(EventName.parkBrake)

    if self.CP.pcmCruise and ret.vEgo < self.CP.minEnableSpeed:
      events.add(EventName.belowEngageSpeed)

    if self.CP.pcmCruise:
      # we engage when pcm is active (rising edge)
      if ret.cruiseState.enabled and not self.CS.out.cruiseState.enabled:
        events.add(EventName.pcmEnable)
      elif not ret.cruiseState.enabled and (c.actuators.accel >= 0. or not self.CP.openpilotLongitudinalControl):
        # it can happen that car cruise disables while comma system is enabled: need to
        # keep braking if needed or if the speed is very low
        if ret.vEgo < self.CP.minEnableSpeed + 2.:
          # non loud alert if cruise disables below 25mph as expected (+ a little margin)
          events.add(EventName.speedTooLow)
        else:
          events.add(EventName.cruiseDisabled)
    if self.CS.CP.minEnableSpeed > 0 and ret.vEgo < 0.001:
      events.add(EventName.manualRestart)

    # handle button presses
    for b in ret.buttonEvents:

      # do enable on both accel and decel buttons
      if b.type in (ButtonType.accelCruise, ButtonType.decelCruise) and not b.pressed:
        if not self.CP.pcmCruise:
          events.add(EventName.buttonEnable)

      # do disable on button down
      if b.type == ButtonType.cancel and b.pressed:
        events.add(EventName.buttonCancel)

    ret.events = events.to_msg()

    self.CS.out = ret.as_reader()
    return self.CS.out

  # pass in a car.CarControl
  # to be called @ 100hz
  def apply(self, c):
    hud_control = c.hudControl
    if hud_control.speedVisible:
      hud_v_cruise = hud_control.setSpeed * CV.MS_TO_KPH
    else:
      hud_v_cruise = 255

    ret = self.CC.update(c.enabled, c.active, self.CS, self.frame,
                         c.actuators,
                         c.cruiseControl.cancel,
                         hud_v_cruise,
                         hud_control.lanesVisible,
                         hud_show_car=hud_control.leadVisible,
                         hud_alert=hud_control.visualAlert)

    self.frame += 1
    return ret
