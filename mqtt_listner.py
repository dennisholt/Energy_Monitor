#!/usr/bin/python3
# 3/11/23 Dennis Holt 
# Let's find out what messages are being sent by the smart plugs

import time
import datetime
# from influxdb import InfluxDBClient
# import board
# import busio
# import adafruit_mcp9808
import paho.mqtt.client as mqtt
import json
from queue import Queue

q=Queue() 

def mqtt_init():
    broker_address = "DietPi"    # try "DietPi" or "Holtpi0" or "localhost" or "192.168.86.29"
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
    # plug_state set by topic [tele/S31B/STATE, stat/S31B/RESULT, stat/S31B/STATUS11]
    print("request status 11")
    ret=client.publish("cmnd/S31B/Status", "10",0) # get initial plug state
    ret=client.publish("cmnd/S31B/Status", "",0) # get initial plug state
    ret=client.publish("cmnd/BatTempPlug/Status", "10",0) # get old plug state
    ret=client.publish("cmnd/BatTempPlug/Status", "",0) # get old plug state
    return client

def main():
    # Set up MQTT and subscribe to all messages
    client = mqtt_init()
    for it in range(30):    #while True:
        time.sleep(5)
        print_messages()
    client.loop_stop()
    client.disconnect()
    exit()

def print_messages(): # filter MQTT messages received for .../SENSOR
    msDict = None
#    print("getting power sensor message")
    while not q.empty():
        message = q.get()
        if message is None:
            continue
        print("topic=",message.topic," msg=",str(message.payload.decode("utf-8")))

# define MQTT on_message handling call backs
def on_message(client, userdata, message):
    q.put(message)
#    decoded_message = str(message.payload.decode("utf-8"))     
#    print("Message received, topic= ",message.topic)
#    print("msg= ",decoded_message)
        
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