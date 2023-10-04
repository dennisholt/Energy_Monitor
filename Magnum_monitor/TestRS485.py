#!/usr/bin/python3   # RPi
# by Dennis Holt Aug 7, 2023

import os, serial, time
from array import *

def serial_init():
    '''connect to Magnum RS485 via USB'''
    SERIALPORT = "/dev/ttyACM0"    # ttyUSB0"
    BAUDRATE = 115200 # 19200
    ser = serial.Serial(SERIALPORT, BAUDRATE) # ser is open on creation
    ser.bytesize = serial.EIGHTBITS #number of bits per byte
    ser.parity = serial.PARITY_NONE #set parity check: no parity
    ser.stopbits = serial.STOPBITS_ONE #number of stop bits
    ser.timeout = 2 # try to syncronize with inverter #None = block read
    ser.xonxoff = False # disable software flow control
    ser.rtscts = False # disable hardware (RTS/CTS) flow control
    ser.dsrdtr = False # disable hardware (DSR/DTR) flow control
#    ser.inter_byte_timeout (float) # default is None
    ser.write_timeout = 0.001 # timeout for write, keep write (not used) from blocking
    # print 'Starting-up Serial Monitor'
    # inverter sends 21 bytes; remote sends 21 bytes; AGS sends 6; BMK sends 17; 60 max
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    return ser

def open_next_file(filename, mode):
    ''' args filename with path; mode ['wb', 'at']'''
    try:
        fb = open(filename, mode)
    except IOError as e:
        print ("error opening file: " + str(e))
        exit()
    return fb

def open_serial(ser):
    try:
        ser.open()
    except Exception :
        print ("error open serial port: " + str(e))
        exit()

def main():
    os.chdir('/home/pi/Programs')   # Change current working directory
#    print('current working directory =', os.getcwd())
 #   log = open_next_file('MagnumMonitorLog.txt', 'at') # open log file
 #   dt = time.strftime("%Y-%m-%dT%H:%M:%S",time.localtime(time.time()))
 #   log.write(dt + ' Monitor program started \n')
 #   time.sleep(1)   #  let things get settled down
 #   influx_client = influx_init()  # connect to influx database
    ser = serial_init() # connect to Magnum RS485 bus

 #   inv = Magnum()   # instance of dataclass
    t1 = time.time() # init for timing 5 sec accuisition 
    for i in range(20): # test for xx writes of Magnum data to influx db # while True: 
            try: # get magnum record
                while ser.in_waiting < 1:  # is this covered by read(64)?
                    continue
                time.sleep(2)
                out = ser.read(size=512)
#               fb.write (out)
                print(len(out), "  ", out.hex(' ', 1))
            except IOError as e:
                dt = time.strftime("%Y-%m-%dT%H:%M:%S",time.localtime(time.time()))
 #               log.write(dt + ' error communicating...: ' + str(e) + '\n')
                print("error communicating...: " + str(e))
                open_serial(ser)

 #   if not log is None: 
  #      log.close()
    ser.close()
    # end #
   
if __name__ == "__main__":
    main()