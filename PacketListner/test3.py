#!/usr/bin/env python3
'''
Nov 24, 2023 pack voltages to JSON
'''
from dataclasses import dataclass
from pprint import pprint  ###

@dataclass
class Node:
    state: list[tuple]   #(float,float,int)

def main():
    get_list()
    print("out_node_list= ", Node.state)

def get_list():
    Node.state = [(3.3, 10.1,1), (3.32, 10.2, 2), (3.33, 10.3, 3), (3.34, 10.4, 4), (3.35, 10.5,5),]
    return 

if __name__ == '__main__': 
    main()