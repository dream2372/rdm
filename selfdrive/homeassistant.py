#!/usr/bin/env python
import zmq
from copy import copy
from selfdrive import messaging
from selfdrive.services import service_list
from cereal import log
from time import sleep
from common.transformations.coordinates import geodetic2ecef
import requests
import os
import subprocess

def main(gctx=None):
  context = zmq.Context()
  poller = zmq.Poller()
  sock = messaging.sub_sock(context, service_list['liveLocation'].port, poller)

  #initialize the values
  latitude = -1
  longitude = -1
  altitude = -1
  speed = -1

  #the password to get into your homeassistant UI
  API_PASSWORD = '***REMOVED***'
  #the url and what you want to call your EON entity. ie, 'https://myhomeassistanturl.com/api/states/eon.chris'
  API_URL = 'https://***REMOVED***/api/states/eon_chris'


  while 1:
    ping = subprocess.call(["ping", "-W", "4", "-c", "1", "***REMOVED***"])
    if ping:
      sleep(15)
      continue
    print "Transmitting to Home Assistant..."
    for sock, event in poller.poll(500):
      msg = sock.recv()
      evt = log.Event.from_bytes(msg)

      latitude = evt.liveLocation.lat
      longitude = evt.liveLocation.lon
      altitude = evt.liveLocation.alt
      speed = evt.liveLocation.speed

      headers = {
      'x-ha-access': API_PASSWORD
      }

      stats = {'latitude': latitude,
      'longitude': longitude,
      'altitude': altitude,
      'speed': speed,
      }
      data = {'state': 'connected',
      'attributes': stats,
      }
      r = requests.post(API_URL, headers=headers, json=data)
      if r.status_code == requests.codes.ok:
        print "Received by Home Assistant"
<<<<<<< HEAD
      sleep(60) #sleep until next time to send
=======
      sleep(3) #sleep until next time to send
    else:
      continue
>>>>>>> parent of b4f6cda... move things around

if __name__ == '__main__':
  main()
