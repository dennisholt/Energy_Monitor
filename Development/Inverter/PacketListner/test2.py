#!/usr/bin python3
'''
May 7, 2023 by: Dennis Holt
Test percistance of local variables in functions
'''
import socket
import struct
import time
from dataclasses import dataclass

def local_variables(x=2):
    print("x= ",x)

def main():
    local_variables(3)
    local_variables()
    local_variables(4)
    local_variables()

if __name__ == "__main__":
    main()
