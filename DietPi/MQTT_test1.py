#!/usr/bin/python3
# 9/1/23 Dennis Holt 
# test MQTT to S31B  command power on and off
#
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

import time
import paho.mqtt.client as mqtt
import json
# from queue import Queue
from threading import Thread
from dataclasses import dataclass

# define data classes for storing global data
@dataclass
class g_stuff:
#    sensors: list[sens]
    broker_address: str = "localhost"  # try "DietPi" or "Holtpi0" or "localhost" or "192.168.86.29"
                                    # broker_address = "192.168.0.111"  # Holt-Pi0b on Rosie
    heat_on_setpoint: float = 15.5     # 15.5
    heat_off_setpoint: float = 17.5    # 17.5
    loop_interval: float = 60
    closet_temp: float = None
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
                                    # plug commands topic="cmnd/S31B/POWER"
    plug_topic = "+/S31B/#"         # plug telemetry topic="tele/S31B/SENSOR"
                                    # plug status topic="tele/S31B/STATE"
                                    # plug Last will & Testiment topic="tele/S31B/LWT"
    client = mqtt.Client("Test")  # name associated with messages sent
    # set activity callback routines
    client.on_connect = on_connect # attach function to
    client.on_message = on_message
    client.on_log = on_log
    client.on_publish = on_publish
    client.connect(broker_address)  # look up dietPi on Jolt 
    client.loop_start() 
    time.sleep(0.6)
    client.subscribe(plug_topic, 0)
    return client

def on_message(client, userdata, message):
    '''Put info of interest in global stuff data class'''
    print('Topic= ', message.topic)
    decoded_message = str(message.payload.decode("utf-8"))     
    if message.topic == "tele/S31B/SENSOR":
        msDict=json.loads(decoded_message)
        print("SENSOR msDict= ", msDict)

    if message.topic == "tele/S31B/STATE":
        msDict=json.loads(decoded_message)
        print("STATE msDict= ", msDict)

    if message.topic == "stat/S31B/RESULT":
        msDict=json.loads(decoded_message)
        print("RESULT msDict= ", msDict)
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
    time.sleep(1) # let stuff settle down
    ret=g_stuff.mqtt_client.publish("cmnd/S31B/POWER", "ON",1)
    time.sleep(10)  # a little time for reaction and update of heater_state
    ret=g_stuff.mqtt_client.publish("cmnd/S31B/POWER", "OFF",1)
    time.sleep(3)  # a little time for reaction and update of heater_state

    g_stuff.mqtt_client.loop_stop()
    g_stuff.mqtt_client.disconnect()
    exit()

if __name__ == "__main__":
    main()
