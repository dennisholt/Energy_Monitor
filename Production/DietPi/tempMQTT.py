#!/usr/bin/python3
# 02/01/24 add exponentially weighted closet temp average
# 9/12/23 change output from m1.temp to m1.m1_temp 
#           program location and name to   Production/tempMQTT
# 8/17/23 Dennis Holt 
# 3rd revision (BatTempPlug died) now read closet temp via I2C; contorl via MQTT to S31B
# on S31B set TelePeriod = 60; clear rules: rule0; set pulsetime1 1900 (=30 minutes value sec + 100)
#    Pulse time will automatically turn plug off after 30 minutes
# we will depend on the TelePeriod MQTT broadcast from the S31B for status and power reading
# we won't request status; however we will send on / off commands
# in the past there was problems with loss of control; sometimes the relay would not be turned off; or on.

#  FUTURE:  write continuous query from m1 to m5;
#           monitor influx if record not written in warning time period raise alarm

# RECORD: 
# json_body=[
#                {"measurement": "temp", 
#                "tags":{"yr_mo":yr_mo},              # for monthly summary from read time
#                "time":readTime,                     # time stamp GMT = Z
#                "fields":{"interval":interval,       # seconds since last record
#                          "local_dt":readTime[0:19], # Readable local time from time stamp
#                          "temp_closet":   ,         # temperatures from Pi0 I2C connected sensors
#                          "temp_closet_expWt": ,
#                          "temp_shed":     ,
#                          "temp_outdoor":  ,
#                          "heater":        ,         # on/off from S31B MQTT status request
#                          "heater_watts":watts,      # from S31B MQTT
#                          "heater_kWhr":kwh}         # from S31B MQTT
#             }]
# retention policy m1
# aggregate summary records are time stamped by continuous query as time of first record in group
# initial records will mark heater state for condition during interval so must know previous heater state
# initial records are time stamped at end of period
# plug may send status when change or at telperiod

# S31B has Tasmota TelePeriod = 300 so every 5 minutes it broadcast status:

# MQTT messages of interest:
# CMD: power on  OR  CMD: power off
# MQT: stat/S31B/RESULT = {"POWER":"ON"}
# MQT: tele/S31B/STATE = {"Time":"2023-08-21T15:05:31","Uptime":"9T04:03:29","UptimeSec":792209,
#                       "Heap":25,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":1,
#                       "POWER":"OFF",
#                       "Wifi":{"AP":2,"SSId":"jolt","BSSId":"3C:28:6D:AD:BE:EA",
#                           "Channel":1,"Mode":"11n","RSSI":100,"Signal":-39,"LinkCount":1,
#                           "Downtime":"0T00:00:05"}}
# MQT: tele/S31B/SENSOR = {"Time":"2023-08-21T15:05:31",
#                       "ENERGY":{"TotalStartTime":"2022-09-24T18:51:27",
#                           "Total":196.708,"Yesterday":0.000,"Today":0.000,"Period": 0,
#                           "Power": 0,"ApparentPower": 0,"ReactivePower": 0,"Factor":0.00,
#                           "Voltage": 0,"Current":0.000}}

# Not used at this time:
# Status request commands: cmnd/[S31B, BatTempPlug]/Status  msg= 10; cmnd/[S31B, BatTempPlug]/Status  msg= ; result in responses: 
# topic= stat/S31B/STATUS10  msg= {"StatusSNS":{"Time":"2023-03-12T14:01:04","ENERGY":{"TotalStartTime":"2022-09-24T18:51:27","Total":156.206,"Yesterday":1.181,"Today":0.902,"Power": 0,"ApparentPower": 0,"ReactivePower": 0,"Factor":0.00,"Voltage":121,"Current":0.000}}}
# topic= stat/S31B/STATUS  msg= {"Status":{"Module":0,"DeviceName":"S31B","FriendlyName":["S31B"],"Topic":"S31B","ButtonTopic":"0","Power":1,"PowerOnState":3,"LedState":1,"LedMask":"FFFF","SaveData":1,"SaveState":1,"SwitchTopic":"0","SwitchMode":[0,0,0,0,0,0,0,0],"ButtonRetain":0,"SwitchRetain":0,"SensorRetain":0,"PowerRetain":0,"InfoRetain":0,"StateRetain":0}}

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
from influxdb import InfluxDBClient
import board
import busio
import adafruit_mcp9808
import paho.mqtt.client as mqtt
import json
# from queue import Queue
from threading import Thread
from dataclasses import dataclass

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

# define data classes for storing global data
@dataclass
class g_stuff:
    sensors: list[sens]
    broker_address: str = "localhost"  # try "DietPi" or "Holtpi0" or "localhost" or "192.168.86.29"
                                    # broker_address = "192.168.0.111"  # Holt-Pi0b on Rosie
    heat_on_setpoint: float = 17.5     # 15.5
    heat_off_setpoint: float = 19.5    # 17.5
    loop_interval: float = 60
    closet_temp: float = None
    alpha: float = 0.01
    temp_closet_expWt: float = None
    shed_temp: float = None
    outdoor_temp: float = None
    prior_time: int = None   # for influx time stamp and interval int in nanoseconds
    heater_watts: float = None
    heater_kWhr: float = None
    heater_state: int = None   # 1 = ON; 0 = OFF
    prior_heater_state: int = 0  # off
    mqtt_client = None 
    influx_client = None

def mqtt_init():
    broker_address = g_stuff.broker_address
#                                   # smart plug hostname:  S31B-4913
    plug_topic = "+/S31B/#"         # plug telemetry topic="tele/S31B/SENSOR"
                                    # plug status topic="tele/S31B/STATE"
                                    # plug Last will & Testiment topic="tele/S31B/LWT"
#   old_plug_topic = "+/BatTempPlug/#"
                          # Make message que 
    client = mqtt.Client("MacBook")  # name associated with messages sent
    # set activity callback routines
    client.on_connect = on_connect # attach function to
    client.on_message = on_message
    client.on_log = on_log
    client.on_publish = on_publish
    client.connect(broker_address)  # look up dietPi on Jolt 
    client.loop_start() 
    time.sleep(0.6)
    client.subscribe(plug_topic, 0)
#   client.subscribe(old_plug_topic, 0)
    # Send status commands to see if things are working
#   ret=client.publish("cmnd/S31B/Status", "10",0) # get initial S31B sensor status
#   ret=client.publish("cmnd/BatTempPlug/Status", "10",0) # get old plug sensor status
#   ret=client.publish("cmnd/BatTempPlug/Status", "",0) # get old plug state
#   print("mqtt_client type = ", type(client))
    return client

def influx_init():
# connect to influx database
    influx_client = InfluxDBClient(host='solarPi4', port=8086)
    influx_client.switch_database('battery_db')
#   print("influx_client type = ", type(influx_client))
    return influx_client

def i2c_init():
    # make i2c bus object 
    i2c_bus = busio.I2C(board.SCL, board.SDA)
    # make a set of sensor objects
    sensors = []
    sensors.append(sens(i2c_bus, 0x1A, 'MCP9808', 'Closet')) 
    sensors.append(sens(i2c_bus, 0x1C, 'MCP9808', 'Shed'))
    sensors.append(sens(i2c_bus, 0x19, 'MCP9808', 'Outdoor'))
    return sensors

def get_temperatures():
    for sensor in g_stuff.sensors:
        try:
            temperature = sensor.dev.temperature
        except:
            temperature = None
        if sensor.location == "Shed":
            g_stuff.shed_temp = temperature
        if sensor.location == "Outdoor":
            g_stuff.outdoor_temp = temperature
        if sensor.location == "Closet":
            g_stuff.closet_temp = temperature

def control_closet_temp():
    '''check for valid temp; compare closet temp to setpoints; send MQTT command to plug; 
    wait change to take effect'''
    if g_stuff.closet_temp is None:
        print("Closet temp not available in control routine")
        return
    if g_stuff.closet_temp < g_stuff.heat_on_setpoint and g_stuff.heater_state == 0:
        ret=g_stuff.mqtt_client.publish("cmnd/S31B/POWER", "ON",1)
        time.sleep(0.5)  # a little time for reaction and update of heater_state
#       print("turn heater on")
    if g_stuff.closet_temp > g_stuff.heat_off_setpoint and g_stuff.heater_state == 1:
        ret=g_stuff.mqtt_client.publish("cmnd/S31B/POWER", "OFF",1)
        time.sleep(0.5)  # a little time for reaction and update of heater_state
#       print("turn heater off")

def write_record():
    '''Write status to Influx battery_db temp'''
#    print('prior_heater_state= ', g_stuff.prior_heater_state, ' heater_state= ', g_stuff.heater_state,
#          ' closet_temp= ', g_stuff.closet_temp)
# if we don't have the info print error message and return
    if g_stuff.closet_temp == None:
#        print("Closet temperature not detected.")
        return
    if g_stuff.heater_state == None:
#        print("Heater status not detected.")
        return
    if g_stuff.heater_watts == None:
#        print("Heater wattage not detected.")
        return
#    prior_tim (int nanoseconds)  time.time_ns()
    now = time.time_ns()  # get time
    if g_stuff.prior_time is None:
        g_stuff.prior_time = now
    if g_stuff.temp_closet_expWt is None:
        g_stuff.temp_closet_expWt = g_stuff.closet_temp
    interval = (now - g_stuff.prior_time) / 1e9
    g_stuff.temp_closet_expWt = g_stuff.temp_closet_expWt * (1 - g_stuff.alpha) + g_stuff.closet_temp * g_stuff.alpha
    now_str = time.localtime(now / 1e9)
    readTime = time.strftime("%Y-%m-%dT%H:%M:%S",now_str)
    yr_mo = readTime[2:7]

# Put together the influx record
    json_body=[
                    {"measurement": "m1_temp", 
                    "tags":{"yr_mo":yr_mo},                     # for monthly summary from read time
                    "time":now,                                 # time stamp GMT = Z
                    "fields":{"interval":interval,              # seconds since last record
                            "local_dt":readTime,              # Readable local time from time stamp
                            "temp_closet":g_stuff.closet_temp,        # from I2C connected sensors
                            "temp_closet_expWt":g_stuff.temp_closet_expWt,
                            "temp_shed":g_stuff.shed_temp,
                            "temp_outdoor":g_stuff.outdoor_temp,
                            "heater":g_stuff.heater_state,                  # from MQTT S31B sensor message
                            "heat_interval":interval * g_stuff.prior_heater_state,
                            "heater_watts":g_stuff.heater_watts,      # from S31B MQTT sensor message
                            "heater_kWhr":g_stuff.heater_kWhr}        # from the above S31B sensor message
                }]
    ret = g_stuff.influx_client.write_points(json_body, retention_policy='m1')
#    print("write record= ", json_body)

#   initialize global variables so we can detect if message didn't arrive
    g_stuff.prior_time = now
    g_stuff.prior_heater_state = g_stuff.heater_state
    g_stuff.closet_temp = None
    g_stuff.heater_state = None
    g_stuff.heater_watts = None
    g_stuff.heater_kWhr = None

def on_message(client, userdata, message):
    '''Put info of interest in global stuff data class'''
# messages of interest: 
#    print("On_message")
#    print("Topic= ",message.topic)
    decoded_message = str(message.payload.decode("utf-8"))     
    if message.topic == "tele/S31B/SENSOR":
        msDict=json.loads(decoded_message)
#        print("SENSOR msDict= ", msDict)
        g_stuff.heater_watts = msDict.get('ENERGY').get('Power')
        g_stuff.heater_kWhr = msDict.get('ENERGY').get('Total')

    if message.topic == "tele/S31B/STATE":
        msDict=json.loads(decoded_message)
#        print("STATE msDict= ", msDict)
        power = msDict.get('POWER')
        if power == "OFF":
            g_stuff.heater_state = 0
        elif power == "ON":
            g_stuff.heater_state = 1
        else:
            print("Problem with POWER not ON or OFF")

    if message.topic == "stat/S31B/RESULT":
        msDict=json.loads(decoded_message)
#        print("RESULT msDict= ", msDict)
        power = msDict.get('POWER')
        if power == "OFF":
            g_stuff.heater_state = 0
        elif power == "ON":
            g_stuff.heater_state = 1
        else:
            print("Problem with POWER not ON or OFF")
    return

def on_publish(client, userdata, mid):
    pass
    #    print("Message Published")
    
def on_log(client, userdata, level, buf):
    print("log: ", +buf)
    
def on_connect(client, userdata, flags, rc):
#    print("on_connect MQTT")
#    if rc==0:
#        print("connected OK")
#    else:
#        print("Bad connection Returned code= ", rc)
    pass

def main():
    '''Initialize stuff; loop {get temperatures; control heater; write record}'''
    # Set up MQTT and subscribe to all messages
    g_stuff.mqtt_client = mqtt_init()
    # connect to Influx database    
    g_stuff.influx_client = influx_init()
    # initialize I2C temp sensor connection
    g_stuff.sensors = i2c_init()

# loop write record
    while True:    #while True:  for it in range(30):
        get_temperatures()
        #  MQTT messages should get processed automatically by on_message() into g_stuff
        control_closet_temp()
        write_record()
        time.sleep(g_stuff.loop_interval)

    influx_client.close()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    exit()

if __name__ == "__main__":
    main()
