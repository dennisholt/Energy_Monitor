#!/usr/bin/python3
# 3/11/23 Dennis Holt 
# 2nd itteration with revised Influx database w/ retention policies & continuous queries 
# Plan is to read shed, outdoor temp via I2C sensors;
# Control heating lamps with BatTempPlug Tasmota w/ I2C sensor, message MQTT status change;
# Read BatTempPlug temp via MQTT
# Read heater wattage and cum kWhr from S31B via MQTT;
# Store temperatures, lamp control changes and power in influxdb;
# Feb 8, 2023 lock S31B plug on and only use it to monitor power, plug BatTempPlug into S31B;

# March 8, 2023
# to do:
#  Find out if time(time) is GMT
#  Monitor MQTT to see what messages are sent by plugs
#  Verify if continuous query works and if time stamp is start of group.
#  Need tag in Influx for Year-Month to group for summary
#  add cum_kWh to influx continuous queries
#  may need set S31B plug set tasmota console TelePeriod 
# OUTLINE:
#   when heater state changes write a record
#   every temp_interval write a record.
#   data collected from Temp sensors; S31B plug; BatTempPlug
# RECORD: 
# json_body=[
#                {"measurement": "temp", 
#                "tags":{"yr_mo":yr_mo},              # for monthly summary from read time
#                "time":readTime,                     # time stamp GMT = Z
#                "fields":{"interval":interval,       # seconds since last record
#                          "local_dt":readTime[0:19], # Readable local time from time stamp
#                          "temp_closet":   ,         # from I2C connected sensors
#                          "temp_shed":     ,
#                          "temp_outdoor":  ,
#                          "heater":        ,         # from MQTT BatTempPlug status change
#                          "heater_watts":watts,      # from S31B MQTT status request
#                          "heater_kWhr":kwh}         # from the above S31B request
#             }]

# aggregate summary records are time stamped by continuous query as time of first record in group
# initial records will mark heater state for condition during interval so must know previous heater state
# initial records are time stamped at end of period
# plug may send status when change or at telperiod

# Both plugs have Tasmota TelePeriod = 300 so every 5 minutes they broadcast status:
# topic= tele/BatTempPlug/STATE  msg= {"Time":"2023-03-12T13:37:03","Uptime":"3T23:43:30","UptimeSec":344610,"Heap":28,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":1,"POWER":"ON","Wifi":{"AP":1,"SSId":"jolt","BSSId":"3C:28:6D:AD:BE:EA","Channel":1,"RSSI":100,"Signal":-42,"LinkCount":1,"Downtime":"0T00:00:15"}}
# topic= tele/BatTempPlug/SENSOR  msg= {"Time":"2023-03-12T13:37:03","MCP9808":{"Temperature":17.6},"TempUnit":"C"}
# topic= tele/S31B/STATE  msg= {"Time":"2023-03-12T13:38:01","Uptime":"3T23:50:19","UptimeSec":345019,"Heap":25,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":1,"POWER":"ON","Wifi":{"AP":2,"SSId":"jolt","BSSId":"3C:28:6D:AD:BE:EA","Channel":1,"Mode":"11n","RSSI":100,"Signal":-31,"LinkCount":1,"Downtime":"0T00:04:32"}}
# topic= tele/S31B/SENSOR  msg= {"Time":"2023-03-12T13:38:01","ENERGY":{"TotalStartTime":"2022-09-24T18:51:27","Total":156.193,"Yesterday":1.181,"Today":0.889,"Period":15,"Power":178,"ApparentPower":178,"ReactivePower": 0,"Factor":1.00,"Voltage":119,"Current":1.501}}
# When BatTempPlug switches its power it broadcasts:
# topic= stat/BatTempPlug/RESULT  msg= {"POWER":"OFF"}
# topic= stat/BatTempPlug/POWER  msg= OFF
# Status request commands: cmnd/[S31B, BatTempPlug]/Status  msg= 10; cmnd/[S31B, BatTempPlug]/Status  msg= ; result in responses: 
# topic= stat/S31B/STATUS10  msg= {"StatusSNS":{"Time":"2023-03-12T14:01:04","ENERGY":{"TotalStartTime":"2022-09-24T18:51:27","Total":156.206,"Yesterday":1.181,"Today":0.902,"Power": 0,"ApparentPower": 0,"ReactivePower": 0,"Factor":0.00,"Voltage":121,"Current":0.000}}}
# topic= stat/S31B/STATUS  msg= {"Status":{"Module":0,"DeviceName":"S31B","FriendlyName":["S31B"],"Topic":"S31B","ButtonTopic":"0","Power":1,"PowerOnState":3,"LedState":1,"LedMask":"FFFF","SaveData":1,"SaveState":1,"SwitchTopic":"0","SwitchMode":[0,0,0,0,0,0,0,0],"ButtonRetain":0,"SwitchRetain":0,"SensorRetain":0,"PowerRetain":0,"InfoRetain":0,"StateRetain":0}}
# topic= stat/BatTempPlug/STATUS10  msg= {"StatusSNS":{"Time":"2023-03-12T14:01:05","MCP9808":{"Temperature":17.5},"TempUnit":"C"}}
# topic= stat/BatTempPlug/STATUS  msg= {"Status":{"Module":0,"DeviceName":"BatTempPlug","FriendlyName":["BatTempPlug"],"Topic":"BatTempPlug","ButtonTopic":"0","Power":0,"PowerOnState":3,"LedState":1,"LedMask":"FFFF","SaveData":1,"SaveState":1,"SwitchTopic":"0","SwitchMode":[0,0,0,0,0,0,0,0],"ButtonRetain":0,"SwitchRetain":0,"SensorRetain":0,"PowerRetain":0}}

# BatTempPlug mem1 = 18.0; mem2 = 15.3

# Later will get battery info via packetlistner & write to "battery" measure Influxdb
# Battery: SOC; AHr_to_Empty; Current; Voltage; Watts; cum_kWhr
#   Heater: state; watts; cum_kWhr

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
# import datetime
from influxdb import InfluxDBClient
import board
import busio
import adafruit_mcp9808
import paho.mqtt.client as mqtt
import json
from queue import Queue
from threading import Thread

### Initialization ###
###    Globals     ###
mqtt_client = None 
influx_client = None
sensors = None
temp_interval = 60  # measure temperature every x seconds, and when heater status changes
heater_prior_st = 0  # 0 = "OFF"; 1 = "ON" for cum of heater on time 
prior_tim = time.time_ns()  # for influx time stamp and interval int in nanoseconds
heater_status_msg = ""
closet_temp_msg = ""
heater_power_msg = "" 
q=Queue()                       # Make message que 

def mqtt_init():
    broker_address = "localhost" # try "DietPi" or "Holtpi0" or "localhost" or "192.168.86.29"
                                    # broker_address = "192.168.0.111"  # Holt-Pi0b on Rosie
                                    # smart plug hostname:  S31B-4913
    plug_topic = "+/S31B/#"         # plug telemetry topic="tele/S31B/SENSOR"
                                    # plug status topic="tele/S31B/STATE"
                                    # plug Last will & Testiment topic="tele/S31B/LWT"
    old_plug_topic = "+/BatTempPlug/#"
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
    client.subscribe(old_plug_topic, 0)
    # Send status commands to see if things are working
    ret=client.publish("cmnd/S31B/Status", "10",0) # get initial S31B sensor status
    ret=client.publish("cmnd/BatTempPlug/Status", "10",0) # get old plug sensor status
    ret=client.publish("cmnd/BatTempPlug/Status", "",0) # get old plug state
    return client

def influx_init():
# connect to influx database
    influx_client = InfluxDBClient(host='solarPi4', port=8086)
    influx_client.switch_database('battery_db')
    return influx_client

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

def i2c_init():
    # make i2c bus object 
    i2c_bus = busio.I2C(board.SCL, board.SDA)

    # make a set of sensor objects
    sensors = []
    # sensors.append(sens(i2c_bus, 0x1C, 'MCP9808', 'test_sens')) # installed but not used
    # sensors.append(sens(i2c_bus, 0x1A, 'MCP9808', 'Closet')) # installed but not used
    sensors.append(sens(i2c_bus, 0x1C, 'MCP9808', 'Shed'))
    sensors.append(sens(i2c_bus, 0x19, 'MCP9808', 'Outdoor'))
    return sensors

def write_record(mqtt_client, influx_client, sensors):
    global heater_status_msg, closet_temp_msg, heater_power_msg, heater_prior_st, prior_tim
#    heater_prior_st = [0, 1] 
#    prior_tim (int nanoseconds)  time.time_ns()
    now = time.time_ns()  # get time
    interval = (now - prior_tim) / 1e9
    prior_tim = now
    now_str = time.localtime(now / 1e9)
    readTime = time.strftime("%Y-%m-%dT%H:%M:%S",now_str)
    yr_mo = readTime[2:7]
    heater_status_msg = ""  # clear mqtt messages
    closet_temp_msg = ""
    heater_power_msg = ""
    # mqtt request status and sensors
    ret = mqtt_client.publish("cmnd/BatTempPlug/Status", "",0) # get old plug state
    ret = mqtt_client.publish("cmnd/BatTempPlug/Status", "10",0) # get closet temp
    ret = mqtt_client.publish("cmnd/S31B/Status", "10",0) # get heater watts & cum kWhr
    # get shed & outdoor temperatures
    for sensor in sensors:
        try:
            temperature = sensor.dev.temperature
        except:
            temperature = -9999.0
        if sensor.location == "Shed":
            temp_shed = temperature
        if sensor.location == "Outdoor":
            temp_outdoor = temperature
    # get mqtt responses
    while heater_status_msg == "":
        print("Waiting for heater_status_msg")
        time.sleep(0.5)
    heater = heater_prior_st
    msDict = json.loads(heater_status_msg)
    heater_prior_st = msDict.get('Status').get('Power')  # [0, 1]

    while closet_temp_msg == "":
        print("Waiting for closet_temp_msg")
        time.sleep(0.5)
    msDict = json.loads(closet_temp_msg)
    temp_closet = msDict.get('StatusSNS').get('MCP9808').get('Temperature')

    while heater_power_msg == "":
        print("Waiting for heater_power_msg")
        time.sleep(0.5)
    msDict = json.loads(heater_power_msg)
    heater_watts = msDict.get('StatusSNS').get('ENERGY').get('Power')
    heater_kWhr = msDict.get('StatusSNS').get('ENERGY').get('Total')

# Put together the influx record
    json_body=[
                    {"measurement": "temp", 
                    "tags":{"yr_mo":yr_mo},                     # for monthly summary from read time
                    "time":now,                                 # time stamp GMT = Z
                    "fields":{"interval":interval,              # seconds since last record
                            "local_dt":readTime,              # Readable local time from time stamp
                            "temp_closet":temp_closet,        # from I2C connected sensors
                            "temp_shed":temp_shed,
                            "temp_outdoor":temp_outdoor,
                            "heater":heater,                  # from MQTT BatTempPlug status change
                            "heat_interval":interval * heater,
                            "heater_watts":heater_watts,      # from S31B MQTT status request
                            "heater_kWhr":heater_kWhr}        # from the above S31B request
                }]
    ret = influx_client.write_points(json_body)

def main():
    global mqtt_client, influx_client, sensors
    # Set up MQTT and subscribe to all messages
    mqtt_client = mqtt_init()
    # connect to Influx database    
    influx_client = influx_init()
    # initialize I2C temp sensor connection
    sensors = i2c_init()

# loop write record
    while True:    #while True:  for it in range(30):
        time.sleep(temp_interval)
        write_record(mqtt_client, influx_client, sensors)

    influx_client.close()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    exit()

# define MQTT on_message handling call back
# 4 messages of interest are: 
# Heater state:
# topic= stat/BatTempPlug/RESULT  msg= {"POWER":"OFF"}
# topic= stat/BatTempPlug/STATUS  msg= {"Status":{"Module":0,
#                                                 "DeviceName":"BatTempPlug",
#                                                 "FriendlyName":["BatTempPlug"],
#                                                 "Topic":"BatTempPlug",
#                                                 "ButtonTopic":"0",
#                                                 "Power":0,
#                                                 "PowerOnState":3,
#                                                 "LedState":1,
#                                                 "LedMask":"FFFF",
#                                                 "SaveData":1,
#                                                 "SaveState":1,
#                                                 "SwitchTopic":"0",
#                                                 "SwitchMode":[0,0,0,0,0,0,0,0],
#                                                 "ButtonRetain":0,
#                                                 "SwitchRetain":0,
#                                                 "SensorRetain":0,
#                                                 "PowerRetain":0} }
# Closet temperature:
# topic= stat/BatTempPlug/STATUS10  msg= {"StatusSNS":{"Time":"2023-03-12T14:01:05",
#                                                      "MCP9808":{"Temperature":17.5},
#                                                      "TempUnit":"C"} }
# Heater power sensor status:
# topic= stat/S31B/STATUS10  msg= {"StatusSNS":{"Time":"2023-03-12T14:01:04",
#                                               "ENERGY":{"TotalStartTime":"2022-09-24T18:51:27",
#                                                         "Total":156.206,
#                                                         "Yesterday":1.181,
#                                                         "Today":0.902,
#                                                         "Power": 0,
#                                                         "ApparentPower": 0,
#                                                         "ReactivePower": 0,
#                                                         "Factor":0.00,
#                                                         "Voltage":121,
#                                                         "Current":0.000} } }
# Put messages of interest in GLOBAL; If heater status changes call write a record
def on_message(client, userdata, message):
    global heater_status_msg, closet_temp_msg, heater_power_msg, heater_prior_st, mqtt_client, influx_client, sensors
#   q.put(message)
#    print("On_message")
    decoded_message = str(message.payload.decode("utf-8"))     
    if message.topic == "stat/S31B/STATUS10":
        heater_power_msg = decoded_message
        
    if message.topic == "stat/BatTempPlug/STATUS10":
        closet_temp_msg = decoded_message

    if message.topic == "stat/BatTempPlug/STATUS":
#        print("Battery temp plug status message received.")
        heater_status_msg = decoded_message

    if message.topic == "stat/BatTempPlug/RESULT":
        msDict=json.loads(decoded_message)
        if msDict.get('POWER') == "OFF":
            pwr = 0
        else:
            pwr = 1
        if pwr != heater_prior_st:
            heater_prior_st = pwr
            switched = Thread(target = write_record, args = (mqtt_client, influx_client, sensors))
            switched.start()
#            write_record(mqtt_client, influx_client, sensors)


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
 
if __name__ == "__main__":
    main()
