#!/usr/bin python3
'''
May 2, 2023 by: Dennis Holt
'''
import socket
import struct
import time
from dataclasses import dataclass

def main():
    start = time.time()

    
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
