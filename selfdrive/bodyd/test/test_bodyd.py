#!/usr/bin/env python3
from selfdrive.bodyd.bodyd import BodyD
from selfdrive.car.honda.values import BODY_SUPPORTED
from selfdrive.car.honda.values import CAR as HONDA


# test that we can init with every supported car


CARS = set([HONDA.ACCORD, HONDA.ACCORDH, HONDA.CIVIC, HONDA.CIVIC_BOSCH, HONDA.CIVIC_BOSCH_DIESEL, HONDA.ACURA_ILX,
            HONDA.CRV, HONDA.CRV_5G, HONDA.CRV_EU, HONDA.CRV_HYBRID, HONDA.FIT, HONDA.FREED, HONDA.HRV, HONDA.ODYSSEY,
            HONDA.ODYSSEY_CHN, HONDA.ACURA_RDX, HONDA.ACURA_RDX_3G, HONDA.PILOT, HONDA.RIDGELINE,
            HONDA.INSIGHT, HONDA.HONDA_E])

class TestCP():
  def __init__(self, car):
    self.carFingerprint = car

def main():
  for car in CARS:
    CP = TestCP(car)
    b = BodyD(CP)
    if car in BODY_SUPPORTED:
      assert b.BD is not None, ("bodyd not loaded for", car)
    if car not in BODY_SUPPORTED:
      print(car, 'not supported')
      assert b.BD is None, ("bodyd loaded erroneously for", car)


if __name__ == '__main__':
  main()
