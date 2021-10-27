#!/usr/bin/env python3
import cereal.messaging as messaging
from common.params import Params

# Check openpilot for radar faults before performing an alignment. Except alignment errors, no faults are desired.
# This script does NOT account for vertical alignment!!!
# Set your own radarOffset before doing this! Left of the driver's seat is positive.
# For example, this fork assumes the offset for the Civic Hatchback. The radar is mounted ~0.57m to the left, so the proper command would be `echo -n 0.57 > /data/params/d/TeslaRadarOffset`
# After adjusting the radar mount's alignment, your factory radar must be realigned using professional methods/tooling or by recording and rolling back the adjustments made at alignment-time.

      #   Adjustment Screw Diagram   #

       #  H ---------------------
       #    |                   |
       #    |                   |
       #    |                   |
       #    |                   |
       #    |                   |
       #    |                   |
       #    |                   |
       #    -------------------- V


# H = Horiztonal
# V = Vertical

MINX = 2.5
MAXX = 10
MINY = -2.0
MAXY = 2.0

def main():
  sm = messaging.SubMaster(['liveTracks'])
  radarOffset = float(Params().get("TeslaRadarOffset"))

  while 1:
    sm.update()
    if sm.updated['liveTracks']:
      d = sm['liveTracks']
      for i, track in enumerate(d):
        del i
        # We apply an offset, based on the mounting position, when the tracks are read into RadarInterface. Undo that here to properly align on the radar's centerline.
        dRel = round(track.dRel - radarOffset, 2)
        yRel = round(track.yRel, 2)
        if (MAXX >= dRel >= MINX) and (MAXY >= yRel >= MINY):
          # TODO: print multiple possiblities before clearing the screen. This code assumes only one good point
          # print(chr(27) + "[2J")
          print("ID ", end=' '), print(track.trackId, end=' '), print(", Distance", end=' '), print(f'{dRel:.2f}', end=' '), print(", Horizontal", end=' '), print(f'{yRel:.2f}', end=' '), print("")
if __name__ == '__main__':
  main()
