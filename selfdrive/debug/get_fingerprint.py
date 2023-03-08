#!/usr/bin/env python3

# simple script to get a vehicle fingerprint.

# Instructions:
# - connect to a Panda
# - run selfdrive/boardd/boardd
# - launching this script
#   Note: it's very important that the car is in stock mode, in order to collect a complete fingerprint
# - since some messages are published at low frequency, keep this script running for at least 30s,
#   until all messages are received at least once

import cereal.messaging as messaging

logcan = messaging.sub_sock('can')
msgs_1 = {}
msgs_4 = {}
while True:
  lc = messaging.recv_sock(logcan, True)
  if lc is None:
    continue

  for c in lc.can:
    # read also msgs sent by EON on CAN bus 0x80 and filter out the
    # addr with more than 11 bits
    if c.src == 1 and c.address < 0x800 and c.address not in (0x7df, 0x7e0, 0x7e8):
      msgs_1[c.address] = len(c.dat)
    if c.src == 4 and c.address < 0x800 and c.address not in (0x7df, 0x7e0, 0x7e8):
      msgs_4[c.address] = len(c.dat)

  fingerprint_b = ', '.join("%d: %d" % v for v in sorted(msgs_1.items()))
  fingerprint_a = ', '.join("%d: %d" % v for v in sorted(msgs_4.items()))

  print(f"number of fcan b messages {len(msgs_1)}:")
  print(f"fingerprint {fingerprint_a}")

  print(f"number of fcan a messages {len(msgs_4)}:")
  print(f"fingerprint {fingerprint_b}")
