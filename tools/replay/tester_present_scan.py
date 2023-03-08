#!/usr/bin/env python3
import os
import time
import threading
import multiprocessing
from tqdm import tqdm

os.environ['FILEREADER_CACHE'] = '1'

import cereal.messaging as messaging

from selfdrive.boardd.boardd import can_list_to_can_capnp

from common.basedir import BASEDIR
from common.realtime import config_realtime_process, Ratekeeper, DT_CTRL
from selfdrive.boardd.boardd import can_capnp_to_can_list
from tools.plotjuggler.juggle import load_segment
from panda import Panda

# Honda Accord iBooster 
IGNORED_MSGS = [0xe7, 0x1be, 0x1d5, 0x686]

def send_thread():

  idx = 0
  rk = Ratekeeper(1 / DT_CTRL, print_delay_threshold=None)
  pm = messaging.PubMaster(['sendcan'])
  while True:
    # for idx in tqdm(range (0x0, 0x20000000)):
    for idx in tqdm(range (0x18DA0000, 0x20000000)):
      # print(f"sending to addr {hex(idx)}")
      snd = []

      snd.append((idx, 0, b'\x02\x3e\x00\x00\x00\x00\x00\x00', 2))
      snd = list(filter(lambda x: x[-1] <= 4, snd))
      pm.send('sendcan', can_list_to_can_capnp(snd, msgtype='sendcan', valid=True))
      time.sleep(0.01)

      
    # for frame in CAN_MSGS[idx]:
    #   if frame[0] not in IGNORED_MSGS:
    #     if frame[3] == 1: 
    #       # f can b (1be)
    #       snd.append((frame[0], frame[1], frame[2], 0))
    #     # elif frame[3] == 2:
    #       # f can d/e (1d5)
    #       snd.append((frame[0], frame[1], frame[2], 2))
    # snd = list(filter(lambda x: x[-1] <= 4, snd))
    # pm.send('sendcan', can_list_to_can_capnp(snd, msgtype='sendcan', valid=True))
    # idx = (idx + 1) % len(CAN_MSGS)

    rk.keep_time()


if __name__ == "__main__":

  # # civic hatch
  # print("Loading civic hatch log...")
  # ROUTE = "7f6cd31ea33923bd|2023-03-07--13-11-14"
  # REPLAY_SEGS = list(range(0, 2))
  # CAN_MSGS = []
  # logs = [f"/home/pi/Downloads/2023-03-07--13-11-14--{i}/rlog" for i in REPLAY_SEGS]

  # with multiprocessing.Pool(24) as pool:
  #   for lr in tqdm(pool.map(load_segment, logs)):
  #     CAN_MSGS += [can_capnp_to_can_list(m.can) for m in lr if m.which() == 'can']

  print('sending')
  send_thread()
