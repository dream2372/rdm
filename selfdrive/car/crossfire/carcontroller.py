from collections import namedtuple
from cereal import car
from common.realtime import DT_CTRL
from selfdrive.controls.lib.drive_helpers import rate_limit
from common.numpy_fast import clip, interp
from selfdrive.car import create_gas_interceptor_command
from selfdrive.car.honda import hondacan
from selfdrive.car.honda.values import CruiseButtons, VISUAL_HUD, HONDA_BOSCH, HONDA_NIDEC_ALT_PCM_ACCEL, CarControllerParams
from opendbc.can.packer import CANPacker

VisualAlert = car.CarControl.HUDControl.VisualAlert
LongCtrlState = car.CarControl.Actuators.LongControlState

def compute_gb_honda_bosch(accel, speed):
  #TODO returns 0s, is unused
  return 0.0, 0.0


def compute_gb_honda_nidec(accel, speed):
  creep_brake = 0.0
  creep_speed = 2.3
  creep_brake_value = 0.15
  if speed < creep_speed:
    creep_brake = (creep_speed - speed) / creep_speed * creep_brake_value
  gb = float(accel) / 4.8 - creep_brake
  return clip(gb, 0.0, 1.0), clip(-gb, 0.0, 1.0)


def compute_gas_brake(accel, speed, fingerprint):
  if fingerprint in HONDA_BOSCH:
    return compute_gb_honda_bosch(accel, speed)
  else:
    return compute_gb_honda_nidec(accel, speed)


class CarController():
  def __init__(self, dbc_name, CP, VM):
    self.braking = False
    self.brake_steady = 0.
    self.brake_last = 0.
    self.apply_brake_last = 0
    self.last_pump_ts = 0.

    self.packer = CANPacker(dbc_name)
    self.packer_body = CANPacker(dbc_name)

    self.accel = 0
    self.speed = 0
    self.gas = 0
    self.brake = 0

    self.params = CarControllerParams(CP)

  def update(self, enabled, active, CS, frame, actuators, pcm_cancel_cmd,
             hud_v_cruise, hud_show_lanes, hud_show_car, hud_alert):

    P = self.params

    if active:
      accel = actuators.accel
      gas, brake = compute_gas_brake(actuators.accel, CS.out.vEgo, CS.CP.carFingerprint)
    else:
      accel = 0.0
      gas, brake = 0.0, 0.0

    # Send CAN commands.
    can_sends = []

    # wind brake from air resistance decel at high speed
    wind_brake = interp(CS.out.vEgo, [0.0, 2.3, 35.0], [0.001, 0.002, 0.15])
    # all of this is only relevant for HONDA NIDEC
    max_accel = interp(CS.out.vEgo, P.NIDEC_MAX_ACCEL_BP, P.NIDEC_MAX_ACCEL_V)
    # TODO this 1.44 is just to maintain previous behavior
    pcm_speed_BP = [-wind_brake,
                    -wind_brake*(3/4),
                      0.0,
                      0.5]
    # The Honda ODYSSEY seems to have different PCM_ACCEL
    # msgs, is it other cars too?
    pcm_speed = 0.0
    pcm_accel = int(0.0)
    #
    #
    # if not CS.CP.openpilotLongitudinalControl:
    #   if (frame % 2) == 0:
    #     idx = frame // 2
    #     can_sends.append(hondacan.create_bosch_supplemental_1(self.packer, CS.CP.carFingerprint, idx))
    #   # If using stock ACC, spam cancel command to kill gas when OP disengages.
    #   if pcm_cancel_cmd:
    #     can_sends.append(hondacan.spam_buttons_command(self.packer, CruiseButtons.CANCEL, idx, CS.CP.carFingerprint))
    #   elif CS.out.cruiseState.standstill:
    #     can_sends.append(hondacan.spam_buttons_command(self.packer, CruiseButtons.RES_ACCEL, idx, CS.CP.carFingerprint))

    # else:
    # Send gas and brake commands.
    if (frame % 2) == 0:
      idx = frame // 2
      ts = frame * DT_CTRL

      # way too aggressive at low speed without this
      gas_mult = interp(CS.out.vEgo, [0., 10.], [0.4, 1.0])
      # send exactly zero if apply_gas is zero. Interceptor will send the max between read value and apply_gas.
      # This prevents unexpected pedal range rescaling
      # Sending non-zero gas when OP is not enabled will cause the PCM not to respond to throttle as expected
      # when you do enable.
      if active:
        self.gas = clip(gas_mult * (gas - brake + wind_brake*3/4), 0., 1.)
      else:
        self.gas = 0.0
      can_sends.append(create_gas_interceptor_command(self.packer, self.gas, idx))

    new_actuators = actuators.copy()
    new_actuators.speed = self.speed
    new_actuators.accel = self.accel
    new_actuators.gas = self.gas
    new_actuators.brake = self.brake

    return new_actuators, can_sends
