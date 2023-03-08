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
    snd = []
    for frame in CAN_MSGS[idx]:
      if frame[0] not in IGNORED_MSGS:
        if frame[3] == 1: 
          # f can b (1be)
          snd.append((frame[0], frame[1], frame[2], 0))
        # elif frame[3] == 2:
          # f can d/e (1d5)
          snd.append((frame[0], frame[1], frame[2], 2))
    snd = list(filter(lambda x: x[-1] <= 4, snd))
    pm.send('sendcan', can_list_to_can_capnp(snd, msgtype='sendcan', valid=True))
    idx = (idx + 1) % len(CAN_MSGS)

    rk.keep_time()


if __name__ == "__main__":

  # odyssey
  print("Loading odyssey21 log...")
  ROUTE = "c443ca9eee127f66|2021-02-15--16-05-36"
  REPLAY_SEGS = list(range(0, 2))
  CAN_MSGS = []
  logs = [f"/run/user/1000/gvfs/nfs:host=192.168.50.11,prefix=%2Fmnt%2Fraid0/storage/Chris/OP/odyssey21/stateful/c443ca9eee127f66/stock/2022-08-22--19-10-22--{i}/c443ca9eee127f66_2022-08-22--19-10-22--{i}--rlog.bz2" for i in REPLAY_SEGS]
 

  # # 2020 accord body
  # print("Loading Accord log...")
  # ROUTE = "0521a23eaf280813|2021-02-15--16-05-36"
  # REPLAY_SEGS = [0]#list(range(0, 2))
  # CAN_MSGS = []
  # logs = [f"/run/user/1000/gvfs/nfs:host=192.168.50.11,prefix=%2Fmnt%2Fraid0/storage/Chris/OP/accord2.0_body/0521a23eaf280813/2021-02-15--16-05-36--0/rlog.bz2"]
 
  # rdx
  # print("Loading Rdx log...")
  # ROUTE = "c699fc417b4d6e94|2022-08-21--20-29-14"
  # REPLAY_SEGS = list(range(0, 2))
  # CAN_MSGS = []
  # logs = [f"/run/user/1000/gvfs/nfs:host=192.168.50.11,prefix=%2Fmnt%2Fraid0/storage/Chris/OP/rdx/dejavu/c699fc417b4d6e94/stock/2022-08-21--20-29-14--{i}/c699fc417b4d6e94_2022-08-21--20-29-14--{i}--rlog.bz2" for i in REPLAY_SEGS]


  # civic hatch
  # print("Loading civic hatch log...")
  # ROUTE = "7f6cd31ea33923bd|2023-03-07--13-11-14"
  # REPLAY_SEGS = list(range(0, 2))
  # CAN_MSGS = []
  # logs = [f"/home/pi/Downloads/2023-03-07--13-11-14--{i}/rlog" for i in REPLAY_SEGS]

  with multiprocessing.Pool(24) as pool:
    for lr in tqdm(pool.map(load_segment, logs)):
      CAN_MSGS += [can_capnp_to_can_list(m.can) for m in lr if m.which() == 'can']

  print('sending')
  send_thread()