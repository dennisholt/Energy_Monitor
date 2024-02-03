# Energy_Monitor
Off grid monitoring system for output to Grafana dashboards.
This is a work in process
We have a Magnum inverter system

To Do
=====
- [ ] Magnum to Influx
- [ ] Batrium to Influx
- [x] Battery temperature to Influx
- [i] Graphana dashboard from Influx
- [i] New Influx DB with retention policies and continuous queries
- [ ]      may need to add cum_kWh into continuous querys


Ben Help
- VSCode run icon not working in python script
    can run in terminal window with:  % python3 read_translate_V4.0.py
- Remote access to Jeff's network. VPN?
- Slides to scan
- family bank 
- time stamp z
- python extension loading....
-tempMQTT_V2.py
    - Scope of classes like influx_client
    - are there precompile constants def MQTT_host = "DietPi" without being a global
    - How to handle onMessage call back function: global closet_temp_msg = ""
            while closet_temp_msg == "":
    
