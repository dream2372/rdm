#!/usr/bin/env python3

blank_values = '{}'
sig_name = None
id = [1424,1600,1601,1618]
with open(r'/home/pi/Desktop/HONDA_MASTER.dbc', 'r') as fp:
    lines = fp.readlines()
    for frame in id:
        for line in lines:
        # read all lines in a list
            if line.find(f"BO_ {frame}") != -1:
                x = line.split()
                sig_name = x[2].replace(":","")
                print(f"""can_sends.append(packer.make_can_msg("{sig_name}", bus, {blank_values})) # {frame}""")
        if sig_name is None:
            print(f"{frame} not found")