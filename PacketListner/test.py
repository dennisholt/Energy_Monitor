#!/usr/bin python3
'''
May 2, 2023 by: Dennis Holt
UDP listener and parser for datalogging battery condition
test decyphering msg0X415A # lowest 2 pack voltage and temp with pack ID
test decyphering msg0X3F34 # shunt volts current watts capacity to empty
test decyphering msg0X3233 # SOC, kWh Charge, kWh Discharge
'''
import socket
import struct
import textwrap
from dataclasses import dataclass

### Initialization ###
###    Globals     ###
# influx_client = None

# define data classes for shunt and pack
@dataclass
class Shunt:
    count: int = 0
    time: time = 0
    sumVoltage: float = 0
    sumCurrent: float = 0
    minCurrent: float = 0
    maxCurrent: float = 0
    sumWatts: float = 0
    minWatts: float = 0
    maxWatts: float = 0
    Ahr2empty: float = 0

@dataclass
class Pack:
    VoltageMin: float = 0
    Voltage2ndMin: float = 0
    PakMinV: int = 0
    Pak2ndMinV: int = 0
    TempMin: float = 0
    Temp2ndMin: float = 0
    PakMinT: int = 0
    Pak2ndMinT: int = 0
    need_1_16: bool = True
    need_17_28: bool = True

def sortSecond(elem):
    return elem[1]

def sortThird(elem):
    return elem[2]

def main():
    list_tuple = []
    print(list_tuple)
    node = 0
    volt = 3.44
    temp = 15.2
    for i in range (0,16):
        node += 1
        volt -= 0.01
        temp += 0.1
        list_tuple.append((node,round(volt,3),round(temp,3)))
    print(list_tuple)
    print("sort by voltage")
    list_tuple.sort(key=sortSecond)
    print(list_tuple)
    print("sort by temp")
    list_tuple.sort(key=sortThird)
    print(list_tuple)
if __name__ == "__main__":
    main()
