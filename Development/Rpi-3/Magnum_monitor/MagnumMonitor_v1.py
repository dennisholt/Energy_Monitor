#!/usr/bin/python3   # RPi
# #!/usr/local/bin/ python3  # MacBook
# revised by Dennis Holt July 30, 2023
# Ben, need help with exception handling  

# start of reading from Magnum inverter controler and wrighting to influx database
# based on tutorials:
#   http://www.roman10.net/serial-port-communications-in-python/
#   http://www.brettdangerfield.com/post/raspberrypi_temperature_monitor_project/
#   pyserial.sourceforge.net/pyserial.html
#   pyserial.sourceforge.net

import os, serial, time, struct
from array import *
from datetime import date

def open_next_file(filename, mode):
    ''' args filename with path; mode ['wb', ]'''
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

# open_serial(ser)

def main():
#    time.sleep(1)   #  let things get settled down
# setup serial connection to Magnum inverter RS485
    SERIALPORT = "/dev/ttyUSB0"
    BAUDRATE = 19200
    ser = serial.Serial(SERIALPORT, BAUDRATE) # ser is open on creation
    ser.bytesize = serial.EIGHTBITS #number of bits per byte
    ser.parity = serial.PARITY_NONE #set parity check: no parity
    ser.stopbits = serial.STOPBITS_ONE #number of stop bits
    ser.timeout = 0.04 # try to syncronize with inverter #None = block read
    ser.xonxoff = False # disable software flow control
    ser.rtscts = False # disable hardware (RTS/CTS) flow control
    ser.dsrdtr = False # disable hardware (DSR/DTR) flow control
#    ser.inter_byte_timeout (float) # default is None
    ser.write_timeout = 0.001 # timeout for write, keep write (not used) from blocking

    # print 'Starting-up Serial Monitor'
    # inverter sends 21 bytes; remote sends 21 bytes; AGS sends 5; BMK sends 17; 59 max
    # Try reading packets with timeout set and packing them into a .bin file.
    ser.reset_input_buffer()
    ser.reset_output_buffer()
# open log file
# os.getcwd()      # Return the current working directory
    os.chdir('/home/pi/Programs')   # Change current working directory
    print('current working directory =', os.getcwd())
    log = open_next_file('MagnumMonitorLog.txt', 'at')
    dt = time.strftime("%Y-%m-%dT%H:%M:%S",time.localtime(time.time()))
    log.write(dt + ' Monitor program started \n')
    print(dt, ' Monitor program started')
    t1 = time.time()
    for i in range(5000):
#    while True:
        if ser.isOpen():
            try:
    #            for j in range(1,40):
                while ser.in_waiting < 40:
                    continue
                out = ser.read(size=64)
    #            fb.write (out)
     #           print(len(out), "  ", out.hex(' ', 1))
     #           ser.reset_input_buffer()
            except IOError as e:
                print("error communicating...: " + str(e))
                ser.open()
            ag = out[41:len(out)]
            if len(ag) > 1:
                if ag[1] == 0xa2:
                    t2 = time.time()
                    interval = t2 - t1
                    print(len(out), ' ',interval, 'sec ', ag.hex(' ', 1))
                    t1 = t2

  #      if not fb is None: 
   #         fb.close()
    ser.close()
    log.close()
    # end #
   
if __name__ == "__main__":
    main()