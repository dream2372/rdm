from collections import namedtuple
from common.realtime import DT_CTRL
from selfdrive.controls.lib.drive_helpers import rate_limit
from common.numpy_fast import clip
from selfdrive.car import create_gas_command
from selfdrive.car.honda import hondacan
from selfdrive.car.honda.values import AH, CruiseButtons, CAR, HONDA_BOSCH
from selfdrive.can.packer import CANPacker

# Accel limits
ACCEL_HYST_GAP = 5  # don't change accel command for small oscilalitons within this value
# # TODO:  find this. braking stops responding at a certain point. car won't hold. Need to go to max brake faster?
ACCEL_RATE_LIMIT_UP = 0.02
ACCEL_RATE_LIMIT_DOWN = 0.02
ACCEL_MAX = 1600
ACCEL_MIN = -1599
# # TODO: Find this in a m/s2 equivalent
# ACCEL_STOPPED = -1599
ACCEL_SCALE = max(ACCEL_MAX, -ACCEL_MIN)
# ACCEL_SCALE_STOPPED = max(ACCEL_MAX, -ACCEL_STOPPED)


def accel_hysteresis_and_rate_limit(accel, accel_steady, enabled, diff):
  # for small accel oscillations within ACCEL_HYST_GAP, don't change the accel command
  if not enabled:
    # send 0 when disabled, otherwise acc faults
    accel_steady = 0.
    diff = 0
  else:
    diff = accel - accel_steady
    # rate limit first
    if (accel - accel_steady) > ACCEL_RATE_LIMIT_UP:
      accel_steady = accel_steady + ACCEL_RATE_LIMIT_UP
      print "Limit UP: ",
      print accel_steady
    elif (accel_steady - accel) > ACCEL_RATE_LIMIT_DOWN:
      accel_steady = accel_steady - ACCEL_RATE_LIMIT_DOWN
      print "Limit DN: ",
      print accel_steady
    else:
      accel_steady = accel
    # # now apply hysteresis if it still applies
    # if accel > accel_steady + ACCEL_HYST_GAP:
    #   accel = accel - ACCEL_HYST_GAP
    #   print "Hyst: ",
    #   print accel
    # elif accel < accel_steady - ACCEL_HYST_GAP:
    #   accel = accel + ACCEL_HYST_GAP
    #   print "Hyst: ",
    #   print accel
  accel = accel_steady
  return accel, accel_steady, diff


def actuator_hystereses(brake, braking, brake_steady, v_ego, car_fingerprint):
  # hyst params
  brake_hyst_on = 0.02     # to activate brakes exceed this value
  brake_hyst_off = 0.005                     # to deactivate brakes below this value
  brake_hyst_gap = 0.01                      # don't change brake command for small oscillations within this value

  #*** hysteresis logic to avoid brake blinking. go above 0.1 to trigger
  if (brake < brake_hyst_on and not braking) or brake < brake_hyst_off:
    brake = 0.
  braking = brake > 0.

  # for small brake oscillations within brake_hyst_gap, don't change the brake command
  if brake == 0.:
    brake_steady = 0.
  elif brake > brake_steady + brake_hyst_gap:
    brake_steady = brake - brake_hyst_gap
  elif brake < brake_steady - brake_hyst_gap:
    brake_steady = brake + brake_hyst_gap
  brake = brake_steady

  if (car_fingerprint in (CAR.ACURA_ILX, CAR.CRV)) and brake > 0.0:
    brake += 0.15

  return brake, braking, brake_steady


def brake_pump_hysteresis(apply_brake, apply_brake_last, last_pump_ts, ts):
  pump_on = False

  # reset pump timer if:
  # - there is an increment in brake request
  # - we are applying steady state brakes and we haven't been running the pump
  #   for more than 20s (to prevent pressure bleeding)
  if apply_brake > apply_brake_last or (ts - last_pump_ts > 20. and apply_brake > 0):
    last_pump_ts = ts

  # once the pump is on, run it for at least 0.2s
  if ts - last_pump_ts < 0.2 and apply_brake > 0:
    pump_on = True

  return pump_on, last_pump_ts


def process_hud_alert(hud_alert):
  # initialize to no alert
  fcw_display = 0
  steer_required = 0
  acc_alert = 0
  if hud_alert == AH.NONE:          # no alert
    pass
  elif hud_alert == AH.FCW:         # FCW
    fcw_display = hud_alert[1]
  elif hud_alert == AH.STEER:       # STEER
    steer_required = hud_alert[1]
  else:                             # any other ACC alert
    acc_alert = hud_alert[1]

  return fcw_display, steer_required, acc_alert


HUDData = namedtuple("HUDData",
                     ["pcm_accel", "v_cruise", "mini_car", "car", "X4",
                      "lanes", "fcw", "acc_alert", "steer_required"])


class CarController(object):
  def __init__(self, dbc_name):
    self.braking = False
    self.accel_steady = 0.
    self.accel_diff = 0.
    self.brake_steady = 0.
    self.brake_last = 0.
    self.apply_brake_last = 0
    self.last_pump_ts = 0.
    self.packer = CANPacker(dbc_name)
    self.radarVin_idx = 0

  def update(self, enabled, CS, frame, actuators, \
             pcm_speed, pcm_override, pcm_cancel_cmd, pcm_accel, \
             hud_v_cruise, hud_show_lanes, hud_show_car, hud_alert):

    # *** apply brake hysteresis ***
    brake, self.braking, self.brake_steady = actuator_hystereses(actuators.brake, self.braking, self.brake_steady, CS.v_ego, CS.CP.carFingerprint)

    # *** no output if not enabled ***
    if not enabled and CS.pcm_acc_status:
      # send pcm acc cancel cmd if drive is disabled but pcm is still on, or if the system can't be activated
      pcm_cancel_cmd = True

    # *** rate limit after the enable check ***
    self.brake_last = rate_limit(brake, self.brake_last, -2., 1./100)


    # vehicle hud display, wait for one update from 10Hz 0x304 msg
    if hud_show_lanes:
      hud_lanes = 1
    else:
      hud_lanes = 0

    if enabled:
      if hud_show_car:
        hud_car = 2
      else:
        hud_car = 1
    else:
      hud_car = 0

    fcw_display, steer_required, acc_alert = process_hud_alert(hud_alert)

    hud = HUDData(int(pcm_accel), int(round(hud_v_cruise)), 1, hud_car,
                  0xc1, hud_lanes, fcw_display, acc_alert, steer_required)

    # **** process the car messages ****

    # *** compute control surfaces ***
    BRAKE_MAX = 1024//4
    if CS.CP.carFingerprint in (CAR.ACURA_ILX):
      STEER_MAX = 0xF00
    elif CS.CP.carFingerprint in (CAR.CRV, CAR.ACURA_RDX):
      STEER_MAX = 0x3e8  # CR-V only uses 12-bits and requires a lower value (max value from energee)
    elif CS.CP.carFingerprint in (CAR.ODYSSEY_CHN):
      STEER_MAX = 0x7FFF
    else:
      STEER_MAX = 0x1000

    # gas and brake
    apply_accel = actuators.gas - actuators.brake
    raw_accel = actuators.gas - actuators.brake
    apply_accel, self.accel_steady, self.accel_diff = accel_hysteresis_and_rate_limit(apply_accel, self.accel_steady, enabled, self.accel_diff)

    # if CS.v_ego_raw > 2.3:
    #   apply_accel = clip(apply_accel * ACCEL_SCALE, ACCEL_MIN, ACCEL_MAX)
    # else:
    #   apply_accel = clip(apply_accel * ACCEL_SCALE_STOPPED, ACCEL_STOPPED, ACCEL_MAX)
    apply_accel = clip(apply_accel * ACCEL_SCALE, ACCEL_MIN, ACCEL_MAX)


    # steer torque is converted back to CAN reference (positive when steering right)
    apply_gas = clip(actuators.gas, 0., 1.)
    apply_brake = int(clip(self.brake_last * BRAKE_MAX, 0, BRAKE_MAX - 1))
    apply_steer = int(clip(-actuators.steer * STEER_MAX, -STEER_MAX, STEER_MAX))

    lkas_active = enabled and not CS.steer_not_allowed

    # Send CAN commands.
    can_sends = []

    # if using tesla radar, we need to send the VIN
    if CS.useTeslaRadar and ((frame % 100) == 0):
      can_sends.append(hondacan.create_radar_VIN_msg(self.radarVin_idx, CS.radarVIN, 2, 0x17c, 1, CS.radarPosition, CS.radarEpasType))
      self.radarVin_idx += 1
      self.radarVin_idx = self.radarVin_idx % 3

    # Send steering command.
    idx = frame % 4
    can_sends.append(hondacan.create_steering_control(self.packer, apply_steer,
     lkas_active, CS.CP.carFingerprint, CS.CP.radarOffCan, idx, CS.CP.isPandaBlack))

    # debug prints every 1/4"
    if (frame % 25) == 0:
      print "aEgo: ",
      print round(CS.a_ego,4),
      print " actuators: ",
      print round (raw_accel,4),
      print " Diff: ",
      print round(self.accel_diff, 4),
      print " Accel: ",
      print round(apply_accel, 4)


    # Send dashboard UI commands.
    if (frame % 10) == 0:
      idx = (frame/10) % 4
      can_sends.extend(hondacan.create_ui_commands(self.packer, pcm_speed, hud, CS.CP.carFingerprint, CS.CP.openpilotLongitudinalControl, CS.is_metric, idx, CS.CP.isPandaBlack))

    if not CS.CP.openpilotLongitudinalControl:
      # If using stock ACC, spam cancel command to kill gas when OP disengages.
      if pcm_cancel_cmd:
        can_sends.append(hondacan.spam_buttons_command(self.packer, CruiseButtons.CANCEL, idx, CS.CP.carFingerprint, CS.CP.isPandaBlack))
      elif CS.stopped:
        can_sends.append(hondacan.spam_buttons_command(self.packer, CruiseButtons.RES_ACCEL, idx, CS.CP.carFingerprint, CS.CP.isPandaBlack))

    else:
      # Send gas, brake, and acc commands.
      if (frame % 2) == 0:
        if CS.CP.carFingerprint in HONDA_BOSCH:
          idx = frame // 2
          can_sends.extend(hondacan.create_acc_commands(self.packer, enabled, apply_accel, actuators.brake, CS.CP.carFingerprint, idx, CS.CP.isPandaBlack))
        else:
          idx = frame // 2
          ts = frame * DT_CTRL
          pump_on, self.last_pump_ts = brake_pump_hysteresis(apply_brake, self.apply_brake_last, self.last_pump_ts, ts)
          can_sends.append(hondacan.create_brake_command(self.packer, apply_brake, pump_on,
           pcm_override, pcm_cancel_cmd, hud.fcw, idx, CS.CP.carFingerprint, CS.CP.isPandaBlack))
          self.apply_brake_last = apply_brake

        if CS.CP.enableGasInterceptor:
          # send exactly zero if apply_gas is zero. Interceptor will send the max between read value and apply_gas.
          # This prevents unexpected pedal range rescaling
          can_sends.append(create_gas_command(self.packer, apply_gas, idx))

      # TODO: this only applies to people adding a nidec radar to vehicles that didn't come with one
      # so this cannot be upstreamed and needs to be refactored out better somehow
      # if (frame % 5) == 0:
      #   idx = (frame / 5) % 4
      #   can_sends.extend(hondacan.create_radar_commands(CS.v_ego, idx))

    return can_sends
