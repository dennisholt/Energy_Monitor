#!/usr/bin/python3   # RPi
# #!/usr/local/bin/ python3  # MacBook
# revised by Dennis Holt July 30, 2023
# Ben, need help with exception handling  
# set-up needed: sudo pip install influxdb
# start of reading from Magnum inverter controler and wrighting to influx database
# based on tutorials:
#   http://www.roman10.net/serial-port-communications-in-python/
#   http://www.brettdangerfield.com/post/raspberrypi_temperature_monitor_project/
#   pyserial.sourceforge.net/pyserial.html
#   pyserial.sourceforge.net

import os, serial, time, struct
from array import *
from datetime import date
from influxdb import InfluxDBClient
from dataclasses import dataclass

# define data classes for shunt and pack
@dataclass
class Magnum:
    count: int = 0
    time: float = 0
    sumWattsOut: float = 0
    sumGenWattsIn: float = 0
    maxWattsOut: float = -999.
    genRunTime: float = 0
    genStatus: int = -1
    genStartMode: int = -1
    inverterStatus: int = -1
    inverterFault: int = -1

def influx_init():
    '''connect to influx database'''
    influx_client = InfluxDBClient(host='localhost', port=8086) # 'solarPi4'
    influx_client.switch_database('battery_db')
    # influx_client.drop_measurement(measurement="battery_db.m30.battery")
    # print('measurements= ', influx_client.get_list_measurements())
    # drop_measurement(measurement='')
    return influx_client

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
    influx_client = influx_init()  # connect to influx database
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
    inv = Magnum()   # instance of data class
    t1 = time.time()
    for i in range(50): # test for xx Magnum messages
#    while True:  # collect data for 5 sec
        if ser.isOpen():
            try: # get magnum record
    #            for j in range(1,40):
                while ser.in_waiting < 40:  # is this covered by read(64)?
                    continue
                out = ser.read(size=64)
    #            fb.write (out)
     #           print(len(out), "  ", out.hex(' ', 1))
     #           ser.reset_input_buffer()
            except IOError as e:
                print("error communicating...: " + str(e))
                ser.open()
            # process inverter and remote portions of record
            # is inverter portion valid
            if out[10] == 0x3d and out[14] == 0x73:
                print('valid inverter portion')
                inv.count += 1
                genWatts = float(out[7] * out[16])
                inv.sumGenWattsIn += genWatts
                wattsOut = float(out[6] * out[17])
                inv.sumWattsOut += wattsOut
                inv.maxWattsOut = max(inv.maxWattsOut, wattsOut)
                inv.inverterStatus = out[0]
                inv.inverterFault = out[1]
                print('count: ', inv.count, ' Gen V: ', out[7], ' A: ', out[16], ' watts: ', genWatts)
                print('AC out V: ', out[6], ' A: ', out[17], ' watts: ', wattsOut)
                print('sumWatts: ', inv.sumWattsOut, ' maxWatts: ', inv.maxWattsOut, ' status: ',
                      inv.inverterStatus, ' fault: ', inv.inverterFault)
            # is remote portion valid
            if out[21+6] == 0x20:
                inv.genStartMode = out[21+8]
            # is AGS present and valid
            if len(out) > 47 and out[21 + 21] == 0xa1 and out[21+21+2] == 0x34:
                inv.genStatus = out[21+21+1]
                print('AGS header: ', out[21+21], ' generator status: ', inv.genStatus, ' gen start mode: ', inv.genStartMode)

        else: 
            ser.open()

  #      if not fb is None: 
   #         fb.close()
    ser.close()
    log.close()
    # end #
   
if __name__ == "__main__":
    main()