#!/usr/bin/env python3

def carcontrollerCANBuilder():
    dbc = '/home/pi/openpilot/opendbc/HONDA_MASTER.dbc'
    blank_values = '{}'
    sig_name = None
    id = [1424,1600,1601,1618]
    with open(dbc, 'r') as fp:
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

# def carStateCANBuilder():



def dec_to_name(address=[], dbc=None):
    ### Searches the DBC file for the frame in decimal and returns a frame name.
    ### If no name is found, then the decimal value is returned instead.

    assert address
    assert dbc is not None

    with open(dbc, 'r') as fp:
        lines = fp.readlines()
        for line in lines:
            name = None
            for idx, frame in enumerate(address):
                if line.find(f"BO_ {frame}") != -1:
                    raw = line.split()
                    name = raw[2].replace(":","")
                    address[idx] = name
    
    return address

if __name__ == '__main__':
  name = dec_to_name([228], '/home/pi/openpilot/opendbc/HONDA_MASTER.dbc')
  print(name)