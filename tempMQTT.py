#!/usr/bin/python3
# 9/28/22 Dennis Holt  
# Plan is to read closet temp; Get power readings from S31 via MQTT; 
# turn on or off heating lamps via MQTT based on closet temp; 
# Store temperatures, lamp control changes and power in influxdb.
# Hope the Pi-0 can handle this. 

# getting influxdb installed and running on Rpi
# sudo apt update
# sudo apt upgrade
# sudo apt install influxdb
# sudo apt install influxdb-client
# later set it up to start on boot sudo systemctl enable influxdb

# sudo apt-get update
# sudo apt install mosquitto mosquitto-cliants
# sudo apt-get install -y i2c-tools
# sudo apt-get install python3-smbus
# sudo pip3 install adafruit-circuitpython-mcp9808
# sudo pip install paho-mqtt
# sudo pip install influxdb
# run client $ influx
# > show databases
# > create database "bat-closet"

import time
import datetime
from influxdb import InfluxDBClient
import board
import busio
import adafruit_mcp9808
import paho.mqtt.client as mqtt
import json
from queue import Queue

### Initialization ###
###    Globals     ###
turn_on_temp = 15.5  # on when below x in degrees celsius
turn_off_temp = 17.5 # off when above x in degrees celsius
broker_address = "localhost"
# broker_address = "192.168.0.111"  # Holt-Pi0b on Rosie
# smart plug hostname:  S31B-4913
plug_topic = "+/S31B/#"
old_plug_topic = "+/BatTempPlug/#"
# turn on/off topic="cmnd/S31B/POWER", ["ON","OFF","TOGGLE"]
# plug telemetry topic="tele/S31B/SENSOR"
# plug status topic="tele/S31B/STATE"
# plug Last will & Testiment topic="tele/S31B/LWT"
temp_interval = 60  # measure temperature every x seconds
# power measurement interval set tasmota console TelePeriod x (sec) (default=300)

def log_plug_state(state):
    localTime = time.localtime(time.time())
    readTime = time.strftime("%Y-%m-%dT%H:%M:%S",localTime)+local_offset
#    print("readTime[1:19]=",readTime[0:19])
    json_body=[{'measurement': 'power','time':readTime,
        'fields':{'local_dt':readTime[0:19],'heat':state}}]
    ret = influx_client.write_points(json_body)
 
def log_old_plug_state(state):
    localTime = time.localtime(time.time())
    readTime = time.strftime("%Y-%m-%dT%H:%M:%S",localTime)+local_offset
#    print("readTime[1:19]=",readTime[0:19])
    json_body=[{'measurement': 'power','time':readTime,
        'fields':{'local_dt':readTime[0:19],'old_plug':state}}]
    ret = influx_client.write_points(json_body)    
    
def log_old_plug_sensor(temp):
    localTime = time.localtime(time.time())
#    print('in old plug sensor temp= ',temp)
    readTime = time.strftime("%Y-%m-%dT%H:%M:%S",localTime)+local_offset
#    print("readTime[1:19]=",readTime[0:19])
    json_body=[{'measurement': 'temp','time':readTime,
        'fields':{'local_dt':readTime[0:19],'OPTemp':temp}}]
    ret = influx_client.write_points(json_body)    
    
# define MQTT on_message handling call back
# imedeatly set plug_state 
def on_message(client, userdata, message):
    global plug_state, old_plug_state
    q.put(message)
    decoded_message = str(message.payload.decode("utf-8"))     
#    print("Message received, topic= ",message.topic)
#    print("msg= ",decoded_message)
#    msDict=json.loads(decoded_message) # fails if payload='Online' from topic .../LWT
    if message.topic == "stat/S31B/STATUS11":
        msDict=json.loads(decoded_message)
        plug_state=msDict.get('StatusSTS').get('POWER')
        log_plug_state(plug_state)
#        print("plug state=",plug_state)
    if message.topic == "stat/S31B/RESULT":
        msDict=json.loads(decoded_message)
        plug_state=msDict.get('POWER')
#        print("plug state=",plug_state)
        log_plug_state(plug_state)
    if message.topic == "tele/S31B/STATE":
        msDict=json.loads(decoded_message)
        plug_state=msDict.get('POWER')
#        print("plug state=",plug_state)
        log_plug_state(plug_state)
####  Log old plug
    if message.topic == "stat/BatTempPlug/STATUS11":
        msDict=json.loads(decoded_message)
        old_plug_state=msDict.get('StatusSTS').get('POWER')
        log_old_plug_state(old_plug_state)
#        print("plug state=",plug_state)
    if message.topic == "stat/BatTempPlug/RESULT":
        msDict=json.loads(decoded_message)
        was_state = old_plug_state
        old_plug_state=msDict.get('POWER')
#        print("plug state=",plug_state)
        if old_plug_state != was_state:
            log_old_plug_state(old_plug_state)
    if message.topic == "tele/BatTempPlug/STATE":
        msDict=json.loads(decoded_message)
        old_plug_state=msDict.get('POWER')
#        print("plug state=",plug_state)
        log_old_plug_state(old_plug_state)
    if message.topic == "tele/BatTempPlug/SENSOR":
        msDict=json.loads(decoded_message)
        old_plug_state= 'NA'
        temp = msDict.get('MCP9808').get('Temperature')
#        print("SENSOR=", temp)
        log_old_plug_sensor(temp)
        
def on_publish(client, userdata, mid):
    pass
    #    print("Message Published")
    
def on_log(client, userdata, level, buf):
    print("log: ", +buf)
    
def on_connect(client, userdata, flags, rc):
#    if rc==0:
#        print("connected OK")
#    else:
#        print("Bad connection Returned code= ", rc)
    pass
 
def log_power_sensor(): # filter MQTT messages received for .../SENSOR
    msDict = None
#    print("getting power sensor message")
    while not q.empty():
        message = q.get()
        if message is None:
            continue
#        print("topic=",message.topic," msg=",str(message.payload.decode("utf-8")))
        if message.topic == "tele/S31B/SENSOR":
            decoded_message = str(message.payload.decode("utf-8")) 
            msDict = json.loads(decoded_message)
            readTime = msDict.get('Time')+local_offset
            energy = msDict.get('ENERGY')
            watts = energy.get('Power')
            kwh = energy.get('Total')
            # build json and output to influx
            json_body=[
                {"measurement": "power", 
                "tags":{"parm":"lamp_pwr"}, 
                "time":readTime,
                "fields":{"local_dt":readTime[0:19],"watts":watts,"kWhr":kwh}
                }]
#            print("JSON= ", json_body)
#            fmt = "%Y-%m-%dT%H:%M:%S"+local_offset
#            str_time = time.strptime(readTime, fmt)
#            sec_time = time.mktime(str_time)
#            print("time in sec = ", sec_time)
            ret = influx_client.write_points(json_body)
#            print("db_write_return= ", ret)
 
def do_temp_log_control(sensors, local_offset):
    localTime = time.localtime(time.time())
    readTime = time.strftime("%Y-%m-%dT%H:%M:%S",localTime)+local_offset
#    fmt = "%Y-%m-%dT%H:%M:%S"+local_offset
#    str_time = time.strptime(readTime, fmt)
#    sec_time = time.mktime(str_time)
#    print("temp reading time in sec = ", sec_time)
#    print("readTime=",readTime)
    flds_Dict={'local_dt':readTime[0:19]}
    for sensor in sensors:
        try:
            temperature = sensor.dev.temperature
        except:
            temperature = -9999.0
        flds_Dict.update({sensor.location : temperature})
    closetTemp=flds_Dict.get('Closet')
    if not closetTemp == -9999.0:
#        print('the temperature is= ', closetTemp,'C')
        if closetTemp < turn_on_temp and plug_state == 'OFF':
            ret=client.publish("cmnd/S31B/POWER", "ON",1)
            time.sleep(0.1)
#            ret=client.publish("cmnd/S31B/Status", "11",0)
    #        print("pub on ret=",ret)

        if closetTemp > turn_off_temp and plug_state == 'ON':
            ret=client.publish("cmnd/S31B/POWER", "OFF",1)
            time.sleep(0.1)
#            ret=client.publish("cmnd/S31B/Status", "11",0)
    #        print("pub off ret=",ret)  
    #    print("flds_Dict=",flds_Dict)
    json_body=[
        {'measurement': 'temp',
        'time':readTime,
        'fields':flds_Dict}
        ]
    ret = influx_client.write_points(json_body)
#    print("db_write_return= ", ret)
    
# define a sensor class to have a device and a location
class sens():
    def __init__(self, i2c_bus, address, sensType, location):
#        print('input ',i2c_bus,'  ',address,'  ',sensType,'  ',location)
        if sensType.upper() == 'MCP9808':
            self.dev = adafruit_mcp9808.MCP9808(i2c_bus, address)
#            print('output ', self.dev)
        else:
            raise ValueError(
                "Sensor type " + str(sensType) + " unknown.")
        self.address = address
        self.location = location

# make i2c bus object 
i2c_bus = busio.I2C(board.SCL, board.SDA)

# make a set of sensor objects
sensors = []
sensors.append(sens(i2c_bus, 0x1C, 'MCP9808', 'test_sens'))
sensors.append(sens(i2c_bus, 0x1A, 'MCP9808', 'Closet'))
sensors.append(sens(i2c_bus, 0x1C, 'MCP9808', 'Indoor'))
sensors.append(sens(i2c_bus, 0x19, 'MCP9808', 'Outdoor'))
#for sensor in sensors:
#    print(sensor.address,'  ',sensor.location, '  ',sensor.dev)
# connect to influx database
influx_client = InfluxDBClient(host='solarPi4', port=8086)
influx_client.switch_database('bat_closet')

# Make message que and connect to MQTT broker
q=Queue()
client = mqtt.Client("Pi0b")  # name associated with messages sent
# set activity callback routines
client.on_connect = on_connect # attach function to
client.on_message = on_message   
client.on_log = on_log
client.on_publish = on_publish
client.connect(broker_address)
client.loop_start() 
time.sleep(0.6)
client.subscribe(plug_topic, 0)
client.subscribe(old_plug_topic, 0)
plug_state = '' 
old_plug_state = ''  
# plug_state set by topic [tele/S31B/STATE, stat/S31B/RESULT, stat/S31B/STATUS11]
ret=client.publish("cmnd/S31B/Status", "11",0) # get initial plug state
ret=client.publish("cmnd/BatTempPlug/Status", "11",0) # get old plug state

def setLocalOffset():        # needs to run periodically (daily)
    global local_offset

    if time.localtime()[8] == 1:  # is local time DST?
        local_offset = "-04:00"   # DST
    else:
        local_offset = "-05:00"   # STD
#    print("local_offset = ", local_offset)

def main():
    setLocalOffset()              # needs to run periodically (daily)
    now = time.time()    
    cycle = 0
    while True:   #time.time() < now + 120:
    # sec in day = 24 * 3600 = 86400 loops in day 86400 / temp_interval    
        if cycle * temp_interval >= 86400:  # daily set local offset
            setLocalOffset()
            cycle = 0
        time.sleep(temp_interval)
        cycle += 1
    # log temps, control plug 
        do_temp_log_control(sensors, local_offset)

    # Process MQTT messages log on/off and power
        log_power_sensor() 


    #    print('.',end='') # dots to mark number of sleep loops
    #print("but now it is: ", time.time()) # The End
    influx_client.close()
    client.loop_stop()
    client.disconnect()
    exit()

main()
    
