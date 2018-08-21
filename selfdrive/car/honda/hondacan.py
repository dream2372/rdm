import struct

import common.numpy_fast as np
from selfdrive.config import Conversions as CV
from selfdrive.car.honda.values import CAR, HONDA_BOSCH

# *** Honda specific ***
def can_cksum(mm):
  s = 0
  for c in mm:
    c = ord(c)
    s += (c>>4)
    s += c & 0xF
  s = 8-s
  s %= 0x10
  return s


def fix(msg, addr):
  msg2 = msg[0:-1] + chr(ord(msg[-1]) | can_cksum(struct.pack("I", addr)+msg))
  return msg2


def make_can_msg(addr, dat, idx, alt):
  if idx is not None:
    dat += chr(idx << 4)
    dat = fix(dat, addr)
  return [addr, 0, dat, alt]

def create_long_command(packer, enabled, longenabled, accel, idx):
  control_on = 5 if enabled else 0

  ## TODO: VERIFY THESE
  HI_ACCEL_THRESHOLD = [1.52]
  MID_ACCEL_THRESHOLD = [0.632]
  LO_ACCEL_THRESHOLD = [-0.11]

  #THESE MAY BE UNNECESSARY
  LO_BRAKE_THRESHOLD = 0
  MID_BRAKE_THRESHOLD = 0
  HI_BRAKE_THRESHOLD = 0

  #set the state flag. This has at least 4 values, depending on what's going on.
  if longenabled and enabled:
    #going to idle/coast
    if (accel <= 0 and accel >= -0.11):
      state_flag = 0
      braking_flag = 0
      gas_command = 0.208
      print "idle/coast ",
    #going to low accel
    if (accel < 0.632 and accel > 0):
      state_flag = 0
      braking_flag = 0
      gas_command = accel
      print "low accel ",
    #going to mid accel
    elif (accel > 0.632 and accel < 1.52):
      state_flag = 1
      braking_flag = 0
      #zero out when almost to 9 high bits (max for gas_command). 9bits high would be 0.511
      gas_command = (accel - 0.506)
      print "mid accel ",
    #going to high accel
    elif (accel >= 1.52):
      state_flag = 2
      braking_flag = 0
      gas_command = (accel - (0.506 * 2))
      print "hi accel ",
    #going to brake
    elif (accel < -0.11):
      state_flag = 69 #69 in decimal
      braking_flag = 1
      gas_command = 0.208
      print "brake ",
    else:
      state_flag = 69 #69 in decimal
      braking_flag = 0
      gas_command = 0.208
      print "why? ",
  else:
    state_flag = 69 #69 in decimal
    braking_flag = 0
    gas_command = 0.208
    accel = 0
    print "disabled ",

  print "accel ", accel, "gas_command ", gas_command, "state_flag", state_flag

  #we dont set set_to_1 on CIVIC_HATCH.
  values = {
    "GAS_COMMAND": gas_command,
    "STATE_FLAG": state_flag,
    "BRAKING_1": braking_flag,
    "BRAKING_2": braking_flag,
    "CONTROL_ON": control_on,
    "GAS_BRAKE": accel,
  }
  return packer.make_can_msg("ACC_CONTROL", 0, values, idx)

def create_acc_control_on(packer, enabled, idx):
  values = {
  "SET_TO_3": 0x03,
  "CONTROL_ON": enabled,
  "SET_TO_FF": 0xff,
  "SET_TO_75": 0x75,
  "SET_TO_30": 0x30,
  }

  return packer.make_can_msg("ACC_CONTROL_ON", 0, values, idx)

#create blank 0x1fa on CIVIC_HATCH with no bosch radar
def create_1fa(packer, idx):
  values = {}
  return packer.make_can_msg("BLANK_1FA", 0, values, idx)

def create_brake_command(packer, apply_brake, pcm_override, pcm_cancel_cmd, chime, fcw, idx):
  """Creates a CAN message for the Honda DBC BRAKE_COMMAND."""
  pump_on = apply_brake > 0
  brakelights = apply_brake > 0
  brake_rq = apply_brake > 0
  pcm_fault_cmd = False

  values = {
    "COMPUTER_BRAKE": apply_brake,
    "BRAKE_PUMP_REQUEST": pump_on,
    "CRUISE_OVERRIDE": pcm_override,
    "CRUISE_FAULT_CMD": pcm_fault_cmd,
    "CRUISE_CANCEL_CMD": pcm_cancel_cmd,
    "COMPUTER_BRAKE_REQUEST": brake_rq,
    "SET_ME_0X80": 0x80,
    "BRAKE_LIGHTS": brakelights,
    "CHIME": chime,
    "FCW": fcw << 1,  # TODO: Why are there two bits for fcw? According to dbc file the first bit should also work
  }
  return packer.make_can_msg("BRAKE_COMMAND", 0, values, idx)

def create_gas_command(packer, gas_amount, idx):
  """Creates a CAN message for the Honda DBC GAS_COMMAND."""
  enable = gas_amount > 0.001

  values = {"ENABLE": enable}

  if enable:
    values["GAS_COMMAND"] = gas_amount * 255.
    values["GAS_COMMAND2"] = gas_amount * 255.

  return packer.make_can_msg("GAS_COMMAND", 0, values, idx)


def create_steering_control(packer, apply_steer, lkas_active, car_fingerprint, visionradar, radaroffcan, idx):
  """Creates a CAN message for the Honda DBC STEERING_CONTROL."""
  values = {
    "STEER_TORQUE": apply_steer if lkas_active else 0,
    "STEER_TORQUE_REQUEST": lkas_active,
  }
  # Set bus 2 for accord and new crv.
  bus = 2 if car_fingerprint in HONDA_BOSCH and not visionradar else 0
  return packer.make_can_msg("STEERING_CONTROL", bus, values, idx)


def create_ui_commands(packer, pcm_speed, hud, car_fingerprint, longenabled, visionradar, radaroffcan, idx):
  """Creates an iterable of CAN messages for the UIs."""
  commands = []
  bus = 0

  # Bosch sends commands to bus 2.
  if car_fingerprint in HONDA_BOSCH and not visionradar:
    bus = 2
  else:
    if car_fingerprint in HONDA_BOSCH:
      acc_hud_values = {
        'CRUISE_SPEED': hud.v_cruise,
        'ENABLE_MINI_CAR': hud.mini_car,
        'SET_TO_1': 0x01,
        'HUD_LEAD': hud.car,
        'HUD_DISTANCE': 0x02,
        'ACC_ON': longenabled,
        'SET_TO_X3': 0x03,
      }
    else:
      acc_hud_values = {
        'PCM_SPEED': pcm_speed * CV.MS_TO_KPH,
        'PCM_GAS': hud.pcm_accel,
        'CRUISE_SPEED': hud.v_cruise,
        'ENABLE_MINI_CAR': hud.mini_car,
        'HUD_LEAD': hud.car,
        'SET_ME_X03': 0x03,
        'SET_ME_X03_2': 0x03,
        'SET_ME_X01': 0x01,
      }
  commands.append(packer.make_can_msg('ACC_HUD', 0, acc_hud_values, idx))

  lkas_hud_values = {
    'SET_ME_X41': 0x41,
    'SET_ME_X48': 0x48,
    'STEERING_REQUIRED': hud.steer_required,
    'SOLID_LANES': hud.lanes,
    'BEEP': hud.beep,
  }
  commands.append(packer.make_can_msg('LKAS_HUD', bus, lkas_hud_values, idx))

  if car_fingerprint in (CAR.CIVIC, CAR.ODYSSEY):
    commands.append(packer.make_can_msg('HIGHBEAM_CONTROL', 0, {'HIGHBEAMS_ON': False}, idx))
  if not visionradar:
    radar_hud_values = {
      'ACC_ALERTS': hud.acc_alert,
      'LEAD_SPEED': 0x1fe,  # What are these magic values
      'LEAD_STATE': 0x7,
      'LEAD_DISTANCE': 0x1e,
    }

  elif visionradar:
    radar_hud_values = {
    'SET_TO_1' : 0x01,
    }

  commands.append(packer.make_can_msg('RADAR_HUD', 0, radar_hud_values, idx))

  # if True:
  #   commands.append(packer.make_can_msg('HIGHBEAM_CONTROL', 0, {'HIGHBEAMS_ON': False}, idx))
  #   radar_hud_values = {
  #     'ACC_ALERTS': hud.acc_alert,
  #     'SET_TO_1': 0x01,
  #   }
  #   commands.append(packer.make_can_msg('RADAR_HUD', 0, radar_hud_values, idx))
  return commands


def create_radar_commands(v_ego, car_fingerprint, new_radar_config, idx):
  """Creates an iterable of CAN messages for the radar system."""
  commands = []
  v_ego_kph = np.clip(int(round(v_ego * CV.MS_TO_KPH)), 0, 255)
  speed = struct.pack('!B', v_ego_kph)

  msg_0x300 = ("\xf9" + speed + "\x8a\xd0" +
               ("\x20" if idx == 0 or idx == 3 else "\x00") +
               "\x00\x00")

  if car_fingerprint == CAR.CIVIC:
    msg_0x301 = "\x02\x38\x44\x32\x4f\x00\x00"
    idx_offset = 0xc if new_radar_config else 0x8   # radar in civic 2018 requires 0xc
    commands.append(make_can_msg(0x300, msg_0x300, idx + idx_offset, 1))
  else:
    if car_fingerprint == CAR.CRV:
      msg_0x301 = "\x00\x00\x50\x02\x51\x00\x00"
    elif car_fingerprint == CAR.ACURA_RDX:
      msg_0x301 = "\x0f\x57\x4f\x02\x5a\x00\x00"
    elif car_fingerprint == CAR.ODYSSEY:
      msg_0x301 = "\x00\x00\x56\x02\x55\x00\x00"
    elif car_fingerprint == CAR.ACURA_ILX:
      msg_0x301 = "\x0f\x18\x51\x02\x5a\x00\x00"
    elif car_fingerprint == CAR.PILOT:
      msg_0x301 = "\x00\x00\x56\x02\x58\x00\x00"
    elif car_fingerprint == CAR.RIDGELINE:
      msg_0x301 = "\x00\x00\x56\x02\x57\x00\x00"
    commands.append(make_can_msg(0x300, msg_0x300, idx, 1))

  commands.append(make_can_msg(0x301, msg_0x301, idx, 1))
  return commands

def spam_buttons_command(packer, button_val, idx):
  values = {
    'CRUISE_BUTTONS': button_val,
    'CRUISE_SETTING': 0,
  }
  return packer.make_can_msg("SCM_BUTTONS", 0, values, idx)
