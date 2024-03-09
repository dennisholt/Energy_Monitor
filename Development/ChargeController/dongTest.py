#!/usr/bin/python3
# revised by Dennis Holt July 25, 2023
# start of reading from Magnum inverter controler and wrighting to influx database
# based on tutorials:
#   http://www.roman10.net/serial-port-communications-in-python/
#   http://www.brettdangerfield.com/post/raspberrypi_temperature_monitor_project/
#   pyserial.sourceforge.net/pyserial.html
#   pyserial.sourceforge.net

import serial, time, struct
from array import *
from datetime import date
time.sleep(1)   #  let things get settled down
SERIALPORT = "/dev/ttyUSB0"
BAUDRATE = 19200

ser = serial.Serial(SERIALPORT, BAUDRATE)
ser.bytesize = serial.EIGHTBITS #number of bits per byte
ser.parity = serial.PARITY_NONE #set parity check: no parity
ser.stopbits = serial.STOPBITS_ONE #number of stop bits
ser.timeout = 0.04 # try to syncronize with inverter #None = block read
ser.xonxoff = False # disable software flow control
ser.rtscts = False # disable hardware (RTS/CTS) flow control
ser.dsrdtr = False # disable hardware (DSR/DTR) flow control
ser.writeTimeout = 0 # timeout for write
print(ser)

def open_serial(ser):
    try:
        ser.open()
    except Exception :
        print ("error open serial port: " + str(e))
        exit()

# open_serial(ser)
while True:
    today = date.today()
    fb = open_next_file("/home/pi/Programs/outfile" + str(today) + ".bin")
    day_start = time.time()
    day_end = day_start + 60*60*24
    print ('%s %20.5f %20.5f' % (today, day_start, day_end))
    if ser.isOpen():
        try:
            ser.flushInput() # discard input buffer contents
            ser.flushOutput() # abort current output
            a = time.time()
            print("time", a)
            while a < day_end:
    #            for j in range(1,40):
                while ser.in_waiting < 40:
                    continue
                response = ser.read(size=64)
                tb = struct.pack('d',a) # pack time into 8 bytes
                out = array('B')
                out.frombytes(tb)
          #      out.frombytes((response))
                out.extend(response)
                out.frombytes(bytes([0xff, 0xff]))
                fb.write (out)
          #      outStr = " ".join(out[x].encode('hex') for x in range(0,len(out))) + '\n'
                print(len(response), "  ",bytes(out).hex())
                ser.flushInput()
                a = time.time()
       
        except IOError as e:
            print("error communicating...: " + str(e))

    else:
        print("can't open serial port ")

    if not fb is None: 
        fb.close()

ser.close()
# end #

            





