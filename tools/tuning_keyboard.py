#!/usr/bin/python3

from common.params import Params

## This tool requires these params created and set as persistent in common/params.cc and then set as "floats" in the params dir
# TUNE_P
# TUNE_I
# TUNE_F
# TUNE_ACCEL


values_idx = 0
values = ["P", "I", "F", "ACCEL"]


### based on https://stackoverflow.com/questions/510357/how-to-read-a-single-character-from-the-user
def getChar():
  # for POSIX-based systems (with termios & tty support)
  import tty, sys, termios  # raises ImportError if unsupported

  fd = sys.stdin.fileno()
  oldSettings = termios.tcgetattr(fd)

  try:
    tty.setcbreak(fd)
    answer = sys.stdin.read(1)
  finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, oldSettings)

  return answer
###

while 1:
  val = float(Params().get(f"TUNE_{values[values_idx]}"))
  print(f'{values[values_idx]} now at {val}') 
  i = getChar()

  iteration_val = 0.25 if values[values_idx] == "ACCEL" else 0.01

  if i == 'w':    
    val = float(Params().get(f"TUNE_{values[values_idx]}")) + iteration_val
    Params().put(f"TUNE_{values[values_idx]}", ascii(round(val, 3)))
  if i == 's': 
    val = float(Params().get(f"TUNE_{values[values_idx]}")) - iteration_val
    Params().put(f"TUNE_{values[values_idx]}", ascii(round(val, 3)))
  if i == '0':
    Params().put(f"TUNE_{values[values_idx]}", ascii(float(0.0)))
  if i == 'a':
    values_idx += -1
    values_idx %= len(values)
    val = float(Params().get(f"TUNE_{values[values_idx]}"))
  if i == 'd':
    values_idx += 1
    values_idx %= len(values)
    val = float(Params().get(f"TUNE_{values[values_idx]}"))

  else:
    pass
    


