#!/usr/bin/env python3
import argparse
import binascii
import cereal.messaging as messaging
import time


def can_printer(bus, addr, msgs):
  logcan = messaging.sub_sock('can', addr=addr)
  start = time.monotonic_ns()
  while 1:
    can_recv = messaging.drain_sock(logcan, wait_for_one=True)
    for x in can_recv:
      for y in x.can:
        if y.src == bus:
          if y.address in msgs:
            # a = y.dat.decode('ascii', 'backslashreplace')
            x = binascii.hexlify(y.dat).decode('ascii')
            dd = "%f %04X(%4d)(%6d) %s \n" % (((time.monotonic_ns() - start) * 0.000000001), int(y.address), int(y.address), len(y.dat), x)
            print(dd, end='')


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="simple CAN data viewer",
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  parser.add_argument("--bus", type=int, help="CAN bus to print out", default=0)
  parser.add_argument("msgs", nargs='+', help="List of CAN IDs (eg. 0xe4 0x1df 0x1b9) ")
  parser.add_argument("--addr", default="127.0.0.1")

  args = parser.parse_args()
  messages = []
  for i in args.msgs:
    messages.append(int(i, 16))
  can_printer(args.bus, args.addr, messages)
