Setup: on RPi-4
$ sudo systemctl status PacketListner
$ sudo systemctl stop PacketListner
ls -al /home/pi/Packet_Listner/
archive PacketListner_V5b.py as PacketListner_V5b.old-dateXX
copy in modified PacketListner_V6.py 
modify PacketListner.service to run PacketListner_V6.py 
  load dependencies
  getting influxdb installed and running I think this is already there
    sudo apt update
    sudo apt upgrade
    sudo apt install influxdb
    sudo apt install influxdb-client
    sudo pip install influxdb
  later set it up to start on boot sudo systemctl enable influxdb
Test run V6

from influxdb import InfluxDBClient

influx_client = InfluxDBClient(host='localhost', port=8086)  # 'solarPi4'
influx_client.switch_database('bat_closet')

def setLocalOffset():        # needs to run periodically (daily)
    global local_offset
    if time.localtime()[8] == 1:  # is local time DST?
        local_offset = "-04:00"   # DST
    else:
        local_offset = "-05:00"   # STD
    print("local_offset = ", local_offset)

localTime = time.localtime(time.time())
    readTime = time.strftime("%Y-%m-%dT%H:%M:%S",localTime)+local_offset
    print("readTime[1:19]=",readTime[0:19])
    json_body=[{'measurement': 'power','time':readTime,
        'fields':{'local_dt':readTime[0:19],'heat':state}}]
    ret = influx_client.write_points(json_body)

           json_body=[
                {"measurement": "power", 
                "tags":{"parm":"lamp_pwr"}, 
                "time":readTime,
                "fields":{"local_dt":readTime[0:19],"watts":watts,"kWhr":kwh}
                }]
            print("JSON= ", json_body)
            fmt = "%Y-%m-%dT%H:%M:%S"+local_offset
            str_time = time.strptime(readTime, fmt)
            sec_time = time.mktime(str_time)
            print("time in sec = ", sec_time)
            ret = influx_client.write_points(json_body)
            print("db_write_return= ", ret)
test run 
Jan 17, 2023
Issue heater gets stuck on: Second time this happened. Found battery heater had been on since 4 a.m. on 1/16 temp near 40C. 
Turned heater off. Reboot DietPi-0b. Seems to be working.
Found Tasmota parameter PulseTime which automaticaly turns power off after set time. Set PulseTime to 1hr, normal heat on period is 20 minutes.

Jan 18, 2023
Issue heater not coming on:
Found battery temp low and heater not comming on. Appears control program crashes when it can't communicate with Pi4 that is running influx database. Some how that machine got powered off. Need to handle this situation in software on DietPi0 which is doing the control. (need Ben's help)

Issue collect SOC, battery power flow, and voltage from Batrium to Influx and Grafana dashboard. I thought this would be easy. Modify the PacketListner that collected battery pack voltage to send it to Influx. Not working yet. Learning. It will be a great step forward when it works. 

Feb 5, 2023

