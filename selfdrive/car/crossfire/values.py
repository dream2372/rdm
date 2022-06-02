from enum import IntFlag

from cereal import car
from selfdrive.car import dbc_dict

Ecu = car.CarParams.Ecu
VisualAlert = car.CarControl.HUDControl.VisualAlert


# class CarControllerParams():
#   # Allow small margin below -3.5 m/s^2 from ISO 15622:2018 since we
#   # perform the closed loop control, and might need some
#   # to apply some more braking if we're on a downhill slope.
#   # Our controller should still keep the 2 second average above
#   # -3.5 m/s^2 as per planner limits
#   NIDEC_ACCEL_MIN = -4.0  # m/s^2
#   NIDEC_ACCEL_MAX = 1.6  # m/s^2, lower than 2.0 m/s^2 for tuning reasons
#
#   NIDEC_ACCEL_LOOKUP_BP = [-1., 0., .6]
#   NIDEC_ACCEL_LOOKUP_V = [-4.8, 0., 2.0]
#
#   NIDEC_MAX_ACCEL_V = [0.5, 2.4, 1.4, 0.6]
#   NIDEC_MAX_ACCEL_BP = [0.0, 4.0, 10., 20.]
#
#   NIDEC_BRAKE_MAX = 1024 // 4
#
#   BOSCH_ACCEL_MIN = -3.5  # m/s^2
#   BOSCH_ACCEL_MAX = 2.0  # m/s^2
#
#   BOSCH_GAS_LOOKUP_BP = [-0.2, 2.0]  # 2m/s^2
#   BOSCH_GAS_LOOKUP_V = [0, 1600]

  # def __init__(self, CP):
  #   self.STEER_MAX = CP.lateralParams.torqueBP[-1]
  #   # mirror of list (assuming first item is zero) for interp of signed request values
  #   assert(CP.lateralParams.torqueBP[0] == 0)
  #   assert(CP.lateralParams.torqueBP[0] == 0)
  #   self.STEER_LOOKUP_BP = [v * -1 for v in CP.lateralParams.torqueBP][1:][::-1] + list(CP.lateralParams.torqueBP)
    # self.STEER_LOOKUP_V = [v * -1 for v in CP.lateralParams.torqueV][1:][::-1] + list(CP.lateralParams.torqueV)


# Car button codes
class CruiseButtons:
  RES_ACCEL = 4
  DECEL_SET = 3
  CANCEL = 2
  MAIN = 1

class CAR:
  CROSSFIRE = "CROSSFIRE 2005"

FW_VERSIONS = {}

DBC = {
  CAR.CROSSFIRE: dbc_dict('crossfire', None)
}
#
# STEER_THRESHOLD = {
#   # default is 1200, overrides go here
#   CAR.CIVIC_BOSCH: 600,
#   CAR.ACURA_RDX: 400,
#   CAR.CRV_EU: 400,
# }
