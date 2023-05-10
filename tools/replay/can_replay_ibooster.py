#!/usr/bin/env python3
import os
import multiprocessing
from tqdm import tqdm

os.environ['FILEREADER_CACHE'] = '1'

import cereal.messaging as messaging
from selfdrive.boardd.boardd import can_list_to_can_capnp
from common.realtime import Ratekeeper, DT_CTRL
from selfdrive.boardd.boardd import can_capnp_to_can_list
from selfdrive.car.honda.ibooster.minimal_no_dtcs import FakeHonda
from tools.plotjuggler.juggle import load_segment


def send_thread():
  idx = 0
  rk = Ratekeeper(1 / DT_CTRL, print_delay_threshold=None)
  pm = messaging.PubMaster(['sendcan'])
  while True:
    snd = []
    for frame in CAN_MSGS[idx]:
      # VSA_IBOOSTER_COMMAND
      if frame[0] == 232: 
        snd.append((frame[0], frame[1], frame[2], 0))

    snd = list(filter(lambda x: x[-1] <= 4, snd))

    # GENERATE STATIC FRAMES
    can_sends = fake_car.send(command=False)
    fake_car.frame += 1
    snd.extend(can_sends)

    pm.send('sendcan', can_list_to_can_capnp(snd, msgtype='sendcan', valid=True))

    idx += 1
    rk.keep_time()


if __name__ == "__main__":
  # 2017 CRV IBOOSTER COMMAND DRIVE
  print("Loading crv 17 joe1 log...")
  ROUTE = "2661e2cc2e445b48|2021-03-03--17-08-12"
  REPLAY_SEGS = list(range(0, 20))
  CAN_MSGS = []
  logs = [f"/run/user/1000/gvfs/nfs:host=192.168.50.11,prefix=%2Fmnt%2Fraid0/storage/Chris/OP/crv2017/joe1/2661e2cc2e445b48/stock_acc_3mile/2021-03-03--17-08-12--{i}/2661e2cc2e445b48_2021-03-03--17-08-12--{i}--rlog.bz2" for i in REPLAY_SEGS]

  with multiprocessing.Pool(24) as pool:
    for lr in tqdm(pool.map(load_segment, logs)):
      CAN_MSGS += [can_capnp_to_can_list(m.can) for m in lr if m.which() == 'can']

  fake_car = FakeHonda()
  print('sending')
  send_thread()
