2023-01-14  Huddle with Ben
Set-up github: git@github.com:dennisholt/Energy_Monitor.git  (public)
First subproject: Magnum data -> influx -> grafana
-    Get Pi3 setup and connected to Magnum Controler 
-    push current code files to repo
-    Identify which peramaters to put on dashboard
-    Find-out and set-up influx database with retention policies and auto query to down-sample to broader view dashboards.
-   Ben to schedule next Huddle

2023-02-05  Huddle with Ben
*** Keep everything related to Jeff's interface in 'Energy_Monitor' folder ***
Work flow: Modify > Git Add > Git Commit > Sync

VS-Code setup workspace = Dennis'JunkYard  
Package Managers: 
    homebrew: general & versitale; $ brew leves shows tree of packages installed
    pip3: Python package manager; $ pipdeptree shows tree of packages installed
    apt: Package manager for linux; use homebrew if you can
Moved PacketListnerV6.py to folder Energy_Monitor
Fixed time structure in json to Influx

Next: 1. SOC + etc from Batrium > Influx > Grafana
    2. screen shot of grafana for Ben
    3. Set up influx with retention policies and auto down-sampling to long-term measures
    4. Sonoff S31 to solid on > attache old plug for heat control
    5. set-up Pi3 to parallel track Maxum messages

2023-02-10  Influxdb V1.8 Notes
    Influxdb loaded on Pi4 database=bat_closet; Measures [temp, power]

Influx measure to .csv
$ influx -precision 'rfc3339' -database 'bat_closet'
    -execute 'select * from power' -format csv > power1.csv
Then FileZilla sftp to MacBook
Can clear database table with: influx > drop measurement power 

    Want to set auto downsampling and retention policy:
    ref: https://docs.influxdata.com/influxdb/v1.8/guides/downsample_and_retain/
    policy; group by interval;  Retention duration;  Samples retained
     s5       5 sec                5d                  69k
     m5       5 min                3w                  6k
     m30      30 min               12w                 4k
     d1       1 day                104w                0.7k
     d30      1 month              INF
A database can have multiple Retention policys
    CREATE RETENTION POLICY "two_hours" ON "food_data" DURATION 2h REPLICATION 1 DEFAULT
  CREATE RETENTION POLICY "a_year" ON "food_data" DURATION 52w REPLICATION 1
Other commands: ALTER RETENTION POLICY; DROP RETENTION POLICY
What is: SHARD DURATION?? by default it is a fraction of the retention duration eg if duration is 2days to 6 months the shard group retention is 1 day.  
What is a shard group and what does this retention mean? Data is stored in shard groups and when the entire shard group is older than the retention duration it is dropped. Shard group duration should be more than 1000 points per series for efficiency. eg if sample rate is every 5 sec then 1000 sampls is 1.4 hours.  
Continuous query: These run automatically and do the down sampling from one measurement sampling to a wider space sampling.
  CREATE CONTINUOUS QUERY "cq_30m" ON "food_data" BEGIN
    SELECT mean("website") AS "mean_website",mean("phone") AS "mean_phone"
    INTO "a_year"."downsampled_orders"
    FROM "orders"
    GROUP BY time(30m)
  END

March 7, 2023
Current database is bat_closet
has measurements temp and power

Database is stored at /var/lib/influxdb/
show shards gives sense of shard files 

Where are the influxdb log file???

What we want to collect eventually:
interval, local_dt, yr_mo    Note yr_mo is a tag groupby , * groups by all tags
temp: Bat_closet; Outdoor; Shed; House
Battery: SOC; AHr_to_Empty; Current; Voltage; Watts; cum_kWhr
  Heater: state; watts; cum_kWhr

Continuous query: temp; SOC; Current; Voltage; Watts = Max & Min & Mean
        Cum_Heater_on_time; Cum_Heater_kWhr; Cum_Battery_kWhr
        For m5: heaterStatus = last()

Setup new database "battery_db"  (will have measures "temp", "battery")
set retention policies: 
  CREATE RETENTION POLICY "s5" ON "battery_db" DURATION 5d DEFAULT
  CREATE RETENTION POLICY "m5" ON "battery_db" DURATION 3w 
  CREATE RETENTION POLICY "m30" ON "battery_db" DURATION 12w 
  CREATE RETENTION POLICY "d1" ON "battery_db" DURATION 104w 
  CREATE RETENTION POLICY "d30" ON "battery_db" DURATION INF 
--RESAMPLE EVERY 10m FOR 12m

CREATE CONTINUOUS QUERY "cq_temp_m5" ON "battery_db" 
BEGIN
  SELECT sum("interval") AS "interval",
    first("local_dt") AS "local_dt",
    mean("temp_closet") AS "avg_temp_closet",
    max("temp_closet") AS "max_temp_closet",
    min("temp_closet") AS "min_temp_closet",
    mean("temp_shed") AS "avg_temp_shed",
    mean("temp_outdoor") AS "avg_temp_outdoor",
    first("heater") AS "heater",
    sum("heater" * "interval") AS "heater_on",
    first("heater_watts") AS "heater_watts",
    last("heater_kWhr") - first(heater_kWhr)  AS "heater_kWhr"
  INTO "m5"."temp"
  FROM "temp"
  GROUP BY time(5m), *   note: , * groups by all tags preserving tages in output
END
to edit: DROP CONTINUOUS QUERY "cq_temp_m5" ON "battery_db"   then create new version
CREATE CONTINUOUS QUERY "cq_temp_m5" ON "battery_db" BEGIN SELECT sum("interval") AS "interval", first("local_dt") AS "local_dt", mean("temp_closet") AS "avg_temp_closet", max("temp_closet") AS "max_temp_closet", min("temp_closet") AS "min_temp_closet", mean("temp_shed") AS "avg_temp_shed", mean("temp_outdoor") AS "avg_temp_outdoor", first("heater") AS "heater", sum("heat_interval") AS "heater_on", first("heater_watts") AS "heater_watts", last("heater_kWhr") AS "heater_last_kWhr", first(heater_kWhr) AS "heater_first_kWhr" INTO "m5"."temp" FROM "temp" GROUP BY time(5m), * END

"m5"."temp" will have "time" "yr_mo" "interval" "local_dt" "avg_temp_closet" "max_temp_closet" "min_temp_closet"
                      "avg_temp_shed" "avg_temp_outdoor" "heater" "heater_on" "heater_watts" "heater_kWhr"


CREATE CONTINUOUS QUERY "cq_temp_m30" ON "battery_db" 
RESAMPLE EVERY 6h FOR 7h
BEGIN
  SELECT mean("avg_temp_closet") AS "avg_temp_closet",
    max("max_temp_closet") AS "max_temp_closet",
    min("min_temp_closet") AS "min_temp_closet",
    mean("avg_temp_shed") AS "avg_temp_shed",
    mean("avg_temp_outdoor") AS "avg_temp_outdoor",
    last("heater") AS "heater",
    sum("heater_on") AS "heater_on",
    last("heater_watts") AS "heater_watts",
    sum("heater_kWhr") AS "heater_kWhr",
    sum("interval") AS "interval",
    last("local_dt") AS "local_dt",
    last("yr_mo") AS "yr_mo"
  INTO "m30"."temp"
  FROM "m5"."temp"
  GROUP BY time(30m), *   note: , * groups by all tags
END

CREATE CONTINUOUS QUERY "cq_temp_m30" ON "battery_db" RESAMPLE EVERY 6h FOR 7h BEGIN SELECT mean("avg_temp_closet") AS "avg_temp_closet", max("max_temp_closet") AS "max_temp_closet", min("min_temp_closet") AS "min_temp_closet", mean("avg_temp_shed") AS "avg_temp_shed", mean("avg_temp_outdoor") AS "avg_temp_outdoor", last("heater") AS "heater", sum("heater_on") AS "heater_on", last("heater_watts") AS "heater_watts", sum("heater_kWhr") AS "heater_kWhr", sum("interval") AS "interval", last("local_dt") AS "local_dt", last("yr_mo") AS "yr_mo" INTO "m30"."temp" FROM "m5"."temp" GROUP BY time(30m), * END

CREATE CONTINUOUS QUERY "cq_temp_d1" ON "battery_db" 
BEGIN
  SELECT mean("avg_temp_closet") AS "avg_temp_closet",
    max("max_temp_closet") AS "max_temp_closet",
    min("min_temp_closet") AS "min_temp_closet",
    mean("avg_temp_shed") AS "avg_temp_shed",
    mean("avg_temp_outdoor") AS "avg_temp_outdoor",
    sum("heater_on") / 3600 AS "heater_on",
    sum("heater_on") / sum("interval") AS "pct.heater_on",
    sum("interval") / 3600 AS "interval",
    sum("heater_kWhr") AS "heater_kWhr",
    last("local_dt") AS "local_dt",
    last("yr_mo") AS "yr_mo"
  INTO "d1"."temp"
  FROM "m30"."m30_temp"
  GROUP BY time(1d), *   note: , * groups by all tags
END

CREATE CONTINUOUS QUERY "cq_temp_d1" ON "battery_db" BEGIN SELECT mean("avg_temp_closet") AS "avg_temp_closet", max("max_temp_closet") AS "max_temp_closet", min("min_temp_closet") AS "min_temp_closet", mean("avg_temp_shed") AS "avg_temp_shed", mean("avg_temp_outdoor") AS "avg_temp_outdoor", sum("heater_on") / 3600 AS "heater_on", sum("heater_on") / sum("interval") AS "pct.heater_on", sum("interval") / 3600 AS "interval", sum("heater_kWhr") AS "heater_kWhr", last("local_dt") AS "local_dt", last("yr_mo") AS "yr_mo" INTO "d1"."temp" FROM "m30"."temp" GROUP BY time(1d), * END

CREATE CONTINUOUS QUERY "cq_temp_d30" ON "battery_db" BEGIN
  SELECT mean("avg_temp_closet") AS "avg_temp_closet",
    max("max_temp_closet") AS "max_temp_closet",
    min("min_temp_closet") AS "min_temp_closet",
    mean("avg_temp_shed") AS "avg_temp_shed",
    mean("avg_temp_outdoor") AS "avg_temp_outdoor",
    sum("heater_on") AS "heater_on",
    sum("heater_on") / sum("interval") AS "pct.heater_on",
    sum("interval") AS "interval",
    sum("heater_kWhr") AS "heater_kWhr",
    last("local_dt") AS "local_dt",
    last("yr_mo") AS "yr_mo"
  INTO "d30"."temp"
  FROM "d1"."temp"
  GROUP BY "yr_mo"
END

CREATE CONTINUOUS QUERY "cq_temp_d30" ON "battery_db" BEGIN SELECT mean("avg_temp_closet") AS "avg_temp_closet", max("max_temp_closet") AS "max_temp_closet", min("min_temp_closet") AS "min_temp_closet", mean("avg_temp_shed") AS "avg_temp_shed", mean("avg_temp_outdoor") AS "avg_temp_outdoor", sum("heater_on") AS "heater_on", sum("heater_on") / sum("interval") AS "pct.heater_on", sum("interval") AS "interval", sum("heater_kWhr") AS "heater_kWhr", last("local_dt") AS "local_dt", last("yr_mo") AS "yr_mo" INTO "d30"."temp" FROM "d1"."temp" GROUP BY "yr_mo" END

ssh pi@solarPi4
influx
show databases
use bat_closet
show measurements
select * from power limit 3
time Bat_Ahr Bat_Watts_in DC_A DC_V SOC heat interval kWhr local_dt old_plug parm watts
select * from temp limit 1
time Closet Indoor OPTemp Outdoor local_dt test_sens
create database battery_db
create retention policy "s5" on "battery_db" duration 5d replication 1 default
create retention policy "m5" on "battery_db" duration 3w replication 1 
create retention policy "m30" on "battery_db" duration 12w replication 1 
create retention policy "d1" on "battery_db" duration 104w replication 1 
create retention policy "d30" on "battery_db" duration INF replication 1
> show retention policies
name    duration   shardGroupDuration replicaN default
----    --------   ------------------ -------- -------
autogen 0s         168h0m0s           1        false
s5      120h0m0s   24h0m0s            1        true
m5      504h0m0s   24h0m0s            1        false
m30     2016h0m0s  24h0m0s            1        false
d1      17472h0m0s 168h0m0s           1        false
d30     0s         168h0m0s           1        false
 

Entries are made by DietPi, (heater from old_plug)
  measure = temp: fields = local_dt, interval, heater[0,1], heater_watts, cum_kWh, temp_closet, temp_shed, temp_outdoor,
PacketListner
  measure = battery: fields = local_dt, interval, SOC, bat_amps_in, bat_volts, bat_ah_to_empty, bat_cum_kWh_in,

2023 March 14:
Got tempMQTT_V2.py working and Influx measure temp looks ok 
Not sure if CQ is working. CQ m5 didn't appear to run but I may have had the name wrong.
I thought it was just "m5" but it is "cq_temp_m5". 
is Only one in db right now.  Hope to go up tomorrow and check. 

Tomorrow: Check CQ;  
    set V2 to run as background service on DietPi. 
    Collect Ra data;
    Grafana dashboard pulling from battery_db temp
      Grafana tutorial: https://www.youtube.com/watch?v=4qpI4T6_bUw

Problem in Continuous Query:
  sum(heater * interval) AS heater_on    -> make field in s5.temp heat_interval
  last(heater_kWhr) - first(heater_kWhr) AS heater_kWhr  -> make two separate fields in m5

  "heat_interval"

Talk with Ben March 19, 2023
Data classes: https://docs.python.org/3/library/dataclasses.html
turn hex into string: data.hex() - convert bytes to hex string
bytes.fromhex(hex_string) - convert hex string to bytes

March 22, 2023
Influx measure to .csv
$ influx -precision 'rfc3339' -database 'bat_closet'
    -execute 'select * from power' -format csv > power1.csv
Then FileZilla sftp to MacBook
Can clear database table with: influx > drop measurement power 

At Jeff's: Stop tempMQTT_V2 service & Run in terminal sudo python3...
Turn plug off & on and see what errors come up. 
Filezilla new versoin to DietPi and see if that works in terminal. if so start as service

Transfer Batrium mes3F34, 3233, 3E33 to .csv on macBook
Drop other mesage measures

Test data class for aggregating voltage, current, min pack voltage and temp

study influxql functions for better way to do things.  

pi@DietPi:~/Programs/tempMQTT_V2$ sudo python3 tempMQTT_V2.py
Waiting for heater_status_msg
Exception in thread Thread-1:
Traceback (most recent call last):
  File "/usr/lib/python3.9/threading.py", line 954, in _bootstrap_inner
    self.run()
  File "/usr/lib/python3.9/threading.py", line 892, in run
    self._target(*self._args, **self._kwargs)
  File "/usr/local/lib/python3.9/dist-packages/paho/mqtt/client.py", line 3591, in _thread_main
    self.loop_forever(retry_first_connection=True)
  File "/usr/local/lib/python3.9/dist-packages/paho/mqtt/client.py", line 1756, in loop_forever
    rc = self._loop(timeout)
  File "/usr/local/lib/python3.9/dist-packages/paho/mqtt/client.py", line 1164, in _loop
    rc = self.loop_read()
  File "/usr/local/lib/python3.9/dist-packages/paho/mqtt/client.py", line 1556, in loop_read
    rc = self._packet_read()
  File "/usr/local/lib/python3.9/dist-packages/paho/mqtt/client.py", line 2439, in _packet_read
    rc = self._packet_handle()
  File "/usr/local/lib/python3.9/dist-packages/paho/mqtt/client.py", line 3033, in _packet_handle
    return self._handle_publish()
  File "/usr/local/lib/python3.9/dist-packages/paho/mqtt/client.py", line 3327, in _handle_publish
    self._handle_on_message(message)
  File "/usr/local/lib/python3.9/dist-packages/paho/mqtt/client.py", line 3570, in _handle_on_message
    on_message(self, self._userdata, message)
  File "/home/pi/Programs/tempMQTT_V2/tempMQTT_V2.py", line 302, in on_message
    write_record(mqtt_client, influx_client, sensors)
  File "/home/pi/Programs/tempMQTT_V2/tempMQTT_V2.py", line 175, in write_record
    ret = mqtt_client.publish("cmnd/BatTempPlug/Status", "",0) # get old plug state
AttributeError: 'NoneType' object has no attribute 'publish'
^CTraceback (most recent call last):
  File "/home/pi/Programs/tempMQTT_V2/tempMQTT_V2.py", line 320, in <module>
    main()
  File "/home/pi/Programs/tempMQTT_V2/tempMQTT_V2.py", line 236, in main
    time.sleep(temp_interval)

Line continuation
global in main
call routine from callback without holding call back waiting for a return
think about heater status change and the interval evaluation for power integration

influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from mes3233' -format csv > mes3233.csv

Apr 14, 2023
pi@solarPi4:~/Packet_Listner $ influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from s5.temp' -format csv > stemp.csv
pi@solarPi4:~/Packet_Listner $ influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from m5.temp' -format csv > mtemp.csv
> show retention policies
name    duration   shardGroupDuration replicaN default
----    --------   ------------------ -------- -------
autogen 0s         168h0m0s           1        false
s5      120h0m0s   24h0m0s            1        true
m5      504h0m0s   24h0m0s            1        false
m30     2016h0m0s  24h0m0s            1        false
d1      17472h0m0s 168h0m0s           1        false
d30     0s         168h0m0s           1        false

Apr 18, 2023
> use battery_db
Using database battery_db
> CREATE CONTINUOUS QUERY "cq_temp_d30" ON "battery_db" BEGIN SELECT mean("avg_temp_closet") AS "avg_temp_closet", max("max_temp_closet") AS "max_temp_closet", min("min_temp_closet") AS "min_temp_closet", mean("avg_temp_shed") AS "avg_temp_shed", mean("avg_temp_outdoor") AS "avg_temp_outdoor", sum("heater_on") AS "heater_on", sum("heater_on") / sum("interval") AS "pct.heater_on", sum("interval") AS "interval", sum("heater_kWhr") AS "heater_kWhr", last("local_dt") AS "local_dt", last("yr_mo") AS "yr_mo" INTO "d30"."temp" FROM "d1"."temp" GROUP BY "yr_mo" END
ERR: error parsing query: found yr_mo, expected GROUP BY time(...) at line 1, char 551

> show continuous queries
name: battery_db
name        query
----        -----
cq_temp_m5  CREATE CONTINUOUS QUERY cq_temp_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, first(heater) AS heater, sum(heat_interval) AS heater_on, first(heater_watts) AS heater_watts, last(heater_kWhr) AS heater_last_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m5.temp FROM battery_db.s5.temp GROUP BY time(5m), * END
cq_temp_m30 CREATE CONTINUOUS QUERY cq_temp_m30 ON battery_db BEGIN SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, last(heater) AS heater, sum(heater_on) AS heater_on, last(heater_watts) AS heater_watts, sum(heater_kWhr) AS heater_kWhr, sum(interval) AS interval, last(local_dt) AS local_dt, last(yr_mo) AS yr_mo INTO battery_db.m30.temp FROM battery_db.m5.temp GROUP BY time(30m), * END
cq_temp_d1  CREATE CONTINUOUS QUERY cq_temp_d1 ON battery_db BEGIN SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / 3600 AS heater_on, sum(heater_on) / sum(interval) AS "pct.heater_on", sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, last(local_dt) AS local_dt, last(yr_mo) AS yr_mo INTO battery_db.d1.temp FROM battery_db.m30.temp GROUP BY time(1d), * END

> select * from m5.temp limit 10
time                avg_temp_closet    avg_temp_outdoor avg_temp_shed heater heater_first_kWhr heater_last_kWhr heater_on heater_watts interval           local_dt            max_temp_closet min_temp_closet yr_mo

> select * from m30.temp limit 10
name: temp
time                avg_temp_closet    avg_temp_outdoor   avg_temp_shed      heater heater_on heater_watts interval    local_dt            max_temp_closet min_temp_closet yr_mo

> SELECT MEAN("avg_temp_closet") FROM "m5"."temp" GROUP BY "yr_mo"
name: temp
tags: yr_mo=23-03
time mean
---- ----
0    16.452868055555562

name: temp
tags: yr_mo=23-04
time mean
---- ----
0    17.756531811036666

> select * from "d1"."temp"
> 
Perhaps I need something in "d1"."temp" before I can establish continuous query that uses tag in "d1"
> select * from "d1"."temp"
name: temp
time                avg_temp_closet    avg_temp_outdoor   avg_temp_shed      heater_on          interval           local_dt            max_temp_closet min_temp_closet pct.heater_on       yr_mo
----                ---------------    ----------------   -------------      ---------          --------           --------            --------------- --------------- -------------       -----
1681776000000000000 18.627041666666667 14.075442708333332 15.797447916666664 0                  9.998763376944444  2023-04-18T19:55:00 20.4            15.5            0                   23-04
1681862400000000000 16.594525462962963 8.876414207175925  12.375441261574075 2.2427454502777775 24.01514775137694  2023-04-19T19:55:54 18.1            15.1            0.09338878417473767 23-04
1681948800000000000 16.14423611111111  10.820804398148148 13.526493778935189 1.669250011388889  23.983719094127228 2023-04-20T19:55:56 18.1            15.1            0.06959929795865687 23-04
1682035200000000000 17.439068287037035 12.186480034722218 15.273213252314811 1.3490125683333334 23.98431257507917  2023-04-21T19:55:00 19.5            15.1            0.05624562155410787 23-04
> 
CREATE CONTINUOUS QUERY "cq_temp_m5" ON "battery_db" BEGIN SELECT mean("avg_temp_closet") AS "avg_temp_closet", max("max_temp_closet") AS "max_temp_closet", min("min_temp_closet") AS "min_temp_closet", mean("avg_temp_shed") AS "avg_temp_shed", mean("avg_temp_outdoor") AS "avg_temp_outdoor", sum("heater_on") AS "heater_on", sum("heater_on") / sum("interval") AS "pct.heater_on", sum("interval") AS "interval", sum("heater_kWhr") AS "heater_kWhr", last("local_dt") AS "local_dt", last("yr_mo") AS "yr_mo" INTO "d30"."temp" FROM "d1"."temp" GROUP BY "yr_mo" END

ERR: error parsing query: found yr_mo, expected GROUP BY time(...) at line 1, char 551

SELECT MEAN("avg_temp_closet") FROM "d1"."temp" GROUP BY "yr_mo"

May 10, 2023
Grafana need training;
 Grafana tutorial: https://www.youtube.com/watch?v=4qpI4T6_bUw

May 13, 2023
Create continuous queries for batrium data\
CREATE CONTINUOUS QUERY "cq_bat_m5" ON "battery_db" BEGIN SELECT min("soc") AS "min_soc", min("Ahr2empty") AS "min_Ahr2empty", min("avgVoltage") AS "min_m30Voltage", mean("avgWatts") AS "avgWatts", min("minWatts") AS "maxDischargeWatts", max("maxWatts") AS "maxChargeWatts", min("minCurrent") AS "maxDischargeCurrent", max("maxCurrent") AS "maxChargeCurrent", max(kWh_charge) AS "kWh_charge", max(kWh_discharge) AS "kWh_discharge", sum("interval") / 3600 AS "interval", min(pakMinT) AS "pakMinT", min(pakMinV) AS "pakMinV", last("local_dt") AS "local_dt", last("yr_mo") AS "yr_mo" INTO "m5"."battery" FROM "s30"."battery" GROUP BY time(1d), * END

Create continuous queries for batrium data\
CREATE CONTINUOUS QUERY "cq_bat_m5" ON "battery_db" BEGIN SELECT min("min_soc") AS "min_soc", min("min_Ahr2empty") AS "min_Ahr2empty", min("min_m30Voltage") AS "min_m30Voltage", mean("avgWatts") AS "avgWatts", min("maxDischargeWatts") AS "maxDischargeWatts", max("maxChargeWatts") AS "maxChargeWatts", min("maxDischargeCurrent") AS "maxDischargeCurrent", max("maxChargeCurrent") AS "maxChargeCurrent", max(kWh_charge) AS "kWh_charge", max(kWh_discharge) AS "kWh_discharge", sum("interval") AS "interval", min(pakMinT) AS "pakMinT", min(pakMinV) AS "pakMinV", last("local_dt") AS "local_dt", last("yr_mo") AS "yr_mo" INTO "d30"."battery" FROM "d1"."battery" GROUP BY "yr_mo", * END


pi@solarPi4:~/Packet_Listner $ influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from m30.battery' -format csv > m30battery.csv
check temp tables at all retention levels 
pi@solarPi4:~/Packet_Listner $ influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from s5.temp' -format csv > s5temp.csv
pi@solarPi4:~/Packet_Listner $ influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from m5.temp' -format csv > m5temp.csv
pi@solarPi4:~/Packet_Listner $ influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from m30.temp' -format csv > m30temp.csv
pi@solarPi4:~/Packet_Listner $ influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from d1.temp' -format csv > d1temp.csv

May 14, 2023
Need to move everything from m30.battery to s30.battery. then set continuous queries
  create retention policy "s30" on "battery_db" duration 5d replication 1
> select * INTO s30.battery FROM m30.battery
 drop retention policy m30 on battery_db
 create retention policy "m30" on "battery_db" duration 84d replication 1

Fix some stuff
select * FROM m5.battery
show continuous queries  (copy for data dictionary)
drop continuous query cq_bat_m5 on battery_db  bad continuous query wrong group by time and perhaps format of FROM & INTO arguments
 drop retention policy m30 on battery_db Wrong duration
 show retention policies
create retention policy "m30" on "battery_db" duration 84d replication 1 
show retention policies
CREATE CONTINUOUS QUERY cq_bat_m5 ON battery_db BEGIN SELECT min(soc) AS min_soc, min(Ahr2empty) AS min_Ahr2empty, min(avgVoltage) AS min_m30Voltage, mean(avgWatts) AS avgWatts, min(minWatts) AS maxDischargeWatts, max(maxWatts) AS maxChargeWatts, min(minCurrent) AS maxDischargeCurrent, max(maxCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) / 3600 AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, last(local_dt) AS local_dt, last(yr_mo) AS yr_mo INTO "m5"."battery" FROM "s30"."battery" GROUP BY time(5m), * END

CREATE CONTINUOUS QUERY "cq_bat_m30" ON "battery_db" BEGIN SELECT min("min_soc") AS "min_soc", min("min_Ahr2empty") AS "min_Ahr2empty", min("min_m30Voltage") AS "min_m30Voltage", mean("avgWatts") AS "avgWatts", min("maxDischargeWatts") AS "maxDischargeWatts", max("maxChargeWatts") AS "maxChargeWatts", min("maxDischargeCurrent") AS "maxDischargeCurrent", max("maxChargeCurrent") AS "maxChargeCurrent", max(kWh_charge) AS "kWh_charge", max(kWh_discharge) AS "kWh_discharge", sum("interval") AS "interval", min(pakMinT) AS "pakMinT", min(pakMinV) AS "pakMinV", last("local_dt") AS "local_dt", last("yr_mo") AS "yr_mo" INTO "m30"."battery" FROM "m5"."battery" GROUP BY time(30m), * END

CREATE CONTINUOUS QUERY "cq_bat_d1" ON "battery_db" BEGIN SELECT min("min_soc") AS "min_soc", min("min_Ahr2empty") AS "min_Ahr2empty", min("min_m30Voltage") AS "min_m30Voltage", mean("avgWatts") AS "avgWatts", min("maxDischargeWatts") AS "maxDischargeWatts", max("maxChargeWatts") AS "maxChargeWatts", min("maxDischargeCurrent") AS "maxDischargeCurrent", max("maxChargeCurrent") AS "maxChargeCurrent", max(kWh_charge) AS "kWh_charge", max(kWh_discharge) AS "kWh_discharge", sum("interval") AS "interval", min(pakMinT) AS "pakMinT", min(pakMinV) AS "pakMinV", last("local_dt") AS "local_dt", last("yr_mo") AS "yr_mo" INTO "d1"."battery" FROM "m30"."battery" GROUP BY time(1d), * END

May 16, 2023
Checking Continuous queries
cq_temp_m30 CREATE CONTINUOUS QUERY cq_temp_m30 ON battery_db BEGIN SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, last(heater) AS heater, sum(heater_on) AS heater_on, last(heater_watts) AS heater_watts, sum(heater_kWhr) AS heater_kWhr, sum(interval) AS interval, last(local_dt) AS local_dt, last(yr_mo) AS yr_mo INTO battery_db.m30.temp FROM battery_db.m5.temp GROUP BY time(30m), * END
cq_temp_d1  CREATE CONTINUOUS QUERY cq_temp_d1 ON battery_db BEGIN SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / 3600 AS heater_on, sum(heater_on) / sum(interval) AS "pct.heater_on", sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, last(local_dt) AS local_dt, last(yr_mo) AS yr_mo INTO battery_db.d1.temp FROM battery_db.m30.temp GROUP BY time(1d), * END

Checking continuous queries
query grouping is on blocks of time UTC which means day is not local day
Try droping and adding with format from show (no quote marks) To help with future edits to cq
Does cq_temp_m5 have output "yr_mo"?  GROUP BY time(5m), * with the star = all tags
What do we want to do with heater on-time, watts, kWhr ??
  Watts detects if bulb is burned out..
  first and last kWhr can give energy used during period. 
  change first("heater") to max("heater")
  change first("heater_watts") to mean("heater_watts")
m30
  change first("heater") to max("heater")
  change first("heater_watts") to mean("heater_watts")
  change last("local_dt") to first("local_dt")
  first("heater_first_kWhr") AS "heater_first_kWhr"
  last("heater_last_kWhr") AS "heater_last_kWhr"
  drop last("yr_mo")  should be covered by GROUP BY *
d1
  last("heater_last_kWhr") – first(heater_first_kWhr) AS heater_kWhr
show continuous queries  (copy for data dictionary)
  get .csv s30.battery   
  pi@solarPi4:~/Packet_Listner $ influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from s30.battery' -format csv > s30battery.csv
  pi@solarPi4:~/Packet_Listner $ influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from m5.battery' -format csv > m5battery.csv
  pi@solarPi4:~/Packet_Listner $ influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from m30.battery' -format csv > m30battery.csv
  pi@solarPi4:~/Packet_Listner $ influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from d1.battery' -format csv > d1battery.csv

 set Batrium time

  CONTINUOUS QUERY can have:
     sum(heater_on) / sum(interval) AS "pct.heater_on", 
     sum(interval) / 3600 AS interval
     for battery make a h1.battery  because we want to see reset on charge/discharge cum kWhr hour aand day will be broken on UTC and batrium may be resetting on local midnight.  

> show continuous queries
cq_temp_m5  CREATE CONTINUOUS QUERY cq_temp_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, first(heater) AS heater, sum(heat_interval) AS heater_on, first(heater_watts) AS heater_watts, last(heater_kWhr) AS heater_last_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m5.temp FROM battery_db.s5.temp GROUP BY time(5m), * END
cq_temp_m30 CREATE CONTINUOUS QUERY cq_temp_m30 ON battery_db BEGIN SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, last(heater) AS heater, sum(heater_on) AS heater_on, last(heater_watts) AS heater_watts, sum(heater_kWhr) AS heater_kWhr, sum(interval) AS interval, last(local_dt) AS local_dt, last(yr_mo) AS yr_mo INTO battery_db.m30.temp FROM battery_db.m5.temp GROUP BY time(30m), * END
cq_temp_d1  CREATE CONTINUOUS QUERY cq_temp_d1 ON battery_db BEGIN SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / 3600 AS heater_on, sum(heater_on) / sum(interval) AS "pct.heater_on", sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, last(local_dt) AS local_dt, last(yr_mo) AS yr_mo INTO battery_db.d1.temp FROM battery_db.m30.temp GROUP BY time(1d), * END
cq_bat_m5   CREATE CONTINUOUS QUERY cq_bat_m5 ON battery_db BEGIN SELECT min(soc) AS min_soc, min(Ahr2empty) AS min_Ahr2empty, min(avgVoltage) AS min_m30Voltage, mean(avgWatts) AS avgWatts, min(minWatts) AS maxDischargeWatts, max(maxWatts) AS maxChargeWatts, min(minCurrent) AS maxDischargeCurrent, max(maxCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) / 3600 AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, last(local_dt) AS local_dt, last(yr_mo) AS yr_mo INTO battery_db.m5.battery FROM battery_db.s30.battery GROUP BY time(5m), * END
cq_bat_m30  CREATE CONTINUOUS QUERY cq_bat_m30 ON battery_db BEGIN SELECT min(min_soc) AS min_soc, min(min_Ahr2empty) AS min_Ahr2empty, min(min_m30Voltage) AS min_m30Voltage, mean(avgWatts) AS avgWatts, min(maxDischargeWatts) AS maxDischargeWatts, max(maxChargeWatts) AS maxChargeWatts, min(maxDischargeCurrent) AS maxDischargeCurrent, max(maxChargeCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, last(local_dt) AS local_dt, last(yr_mo) AS yr_mo INTO battery_db.m30.battery FROM battery_db.m5.battery GROUP BY time(30m), * END
cq_bat_d1   CREATE CONTINUOUS QUERY cq_bat_d1 ON battery_db BEGIN SELECT min(min_soc) AS min_soc, min(min_Ahr2empty) AS min_Ahr2empty, min(min_m30Voltage) AS min_m30Voltage, mean(avgWatts) AS avgWatts, min(maxDischargeWatts) AS maxDischargeWatts, max(maxChargeWatts) AS maxChargeWatts, min(maxDischargeCurrent) AS maxDischargeCurrent, max(maxChargeCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, last(local_dt) AS local_dt, last(yr_mo) AS yr_mo INTO battery_db.d1.battery FROM battery_db.m30.battery GROUP BY time(1d), * END


show retention policies
name    duration   shardGroupDuration replicaN default
----    --------   ------------------ -------- -------
autogen 0s         168h0m0s           1        false
s5      120h0m0s   24h0m0s            1        true
m5      504h0m0s   24h0m0s            1        false
d1      17472h0m0s 168h0m0s           1        false
d30     0s         168h0m0s           1        false
s30     120h0m0s   24h0m0s            1        false
m30     2016h0m0s  24h0m0s            1        false

 $ influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from m5.battery' -format csv > m5battery.csv
 
 tomorrow 5/19 fix temp CQs
Try CQ without quoting variables:
DROP CONTINUOUS QUERY cq_temp_m5 ON battery_db
CREATE CONTINUOUS QUERY cq_temp_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heat_interval) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_kWhr) AS heater_last_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m5.temp FROM battery_db.s5.temp GROUP BY time(5m), * END
SHOW CONTINUOUS QUERIES

DROP CONTINUOUS QUERY cq_temp_m30 ON battery_db
CREATE CONTINUOUS QUERY cq_temp_m30 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heat_interval) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_last_kWhr) - first(heater_first_kWhr) AS heater_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m30.temp FROM battery_db.m5.temp GROUP BY time(5m), * END

DROP CONTINUOUS QUERY cq_temp_d1 ON battery_db
CREATE CONTINUOUS QUERY cq_temp_d1 ON battery_db BEGIN SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / 3600 AS heater_on, sum(heater_on) / sum(interval) AS "pct.heater_on", sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, first(local_dt) AS local_dt INTO battery_db.d1.temp FROM battery_db.m30.temp GROUP BY time(1d), * END

What about measurements from Batrium 
DROP CONTINUOUS QUERY cq_bat_m5 ON battery_db
CREATE CONTINUOUS QUERY cq_bat_m5 ON battery_db BEGIN SELECT min(soc) AS min_soc, min(Ahr2empty) AS min_Ahr2empty, min(avgVoltage) AS min_Voltage, mean(avgWatts) AS avgWatts, min(minWatts) AS maxDischargeWatts, max(maxWatts) AS maxChargeWatts, min(minCurrent) AS maxDischargeCurrent, max(maxCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, first(local_dt) AS local_dt INTO battery_db.m5.battery FROM battery_db.s30.battery GROUP BY time(5m), * END

DROP CONTINUOUS QUERY cq_bat_m30 ON battery_db
CREATE CONTINUOUS QUERY cq_bat_m30 ON battery_db BEGIN SELECT min(min_soc) AS min_soc, min(min_Ahr2empty) AS min_Ahr2empty, min(min_Voltage) AS min_Voltage, mean(avgWatts) AS avgWatts, min(maxDischargeWatts) AS maxDischargeWatts, max(maxChargeWatts) AS maxChargeWatts, min(maxDischargeCurrent) AS maxDischargeCurrent, max(maxChargeCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) / 3600 AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, first(local_dt) AS local_dt INTO battery_db.m30.battery FROM battery_db.m5.battery GROUP BY time(30m), * END

DROP CONTINUOUS QUERY cq_bat_d1 ON battery_db
CREATE CONTINUOUS QUERY cq_bat_d1 ON battery_db BEGIN SELECT min(min_soc) AS min_soc, min(min_Ahr2empty) AS min_Ahr2empty, min(min_Voltage) AS min_Voltage, mean(avgWatts) AS avgWatts, min(maxDischargeWatts) AS maxDischargeWatts, max(maxChargeWatts) AS maxChargeWatts, min(maxDischargeCurrent) AS maxDischargeCurrent, max(maxChargeCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, first(local_dt) AS local_dt INTO battery_db.d1.battery FROM battery_db.m30.battery GROUP BY time(1d), * END

05/19/23
cq_temp_m5  CREATE CONTINUOUS QUERY cq_temp_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heat_interval) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_kWhr) AS heater_last_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m5.temp FROM battery_db.s5.temp GROUP BY time(5m), * END
cq_temp_m30 CREATE CONTINUOUS QUERY cq_temp_m30 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heat_interval) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_last_kWhr) - first(heater_first_kWhr) AS heater_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m30.temp FROM battery_db.m5.temp GROUP BY time(5m), * END
cq_temp_d1  CREATE CONTINUOUS QUERY cq_temp_d1 ON battery_db BEGIN SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / 3600 AS heater_on, sum(heater_on) / sum(interval) AS "pct.heater_on", sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, first(local_dt) AS local_dt INTO battery_db.d1.temp FROM battery_db.m30.temp GROUP BY time(1d), * END
cq_bat_m5   CREATE CONTINUOUS QUERY cq_bat_m5 ON battery_db BEGIN SELECT min(soc) AS min_soc, min(Ahr2empty) AS min_Ahr2empty, min(avgVoltage) AS min_Voltage, mean(avgWatts) AS avgWatts, min(minWatts) AS maxDischargeWatts, max(maxWatts) AS maxChargeWatts, min(minCurrent) AS maxDischargeCurrent, max(maxCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, first(local_dt) AS local_dt INTO battery_db.m5.battery FROM battery_db.s30.battery GROUP BY time(5m), * END
cq_bat_m30  CREATE CONTINUOUS QUERY cq_bat_m30 ON battery_db BEGIN SELECT min(min_soc) AS min_soc, min(min_Ahr2empty) AS min_Ahr2empty, min(min_Voltage) AS min_Voltage, mean(avgWatts) AS avgWatts, min(maxDischargeWatts) AS maxDischargeWatts, max(maxChargeWatts) AS maxChargeWatts, min(maxDischargeCurrent) AS maxDischargeCurrent, max(maxChargeCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) / 3600 AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, first(local_dt) AS local_dt INTO battery_db.m30.battery FROM battery_db.m5.battery GROUP BY time(30m), * END
cq_bat_d1   CREATE CONTINUOUS QUERY cq_bat_d1 ON battery_db BEGIN SELECT min(min_soc) AS min_soc, min(min_Ahr2empty) AS min_Ahr2empty, min(min_Voltage) AS min_Voltage, mean(avgWatts) AS avgWatts, min(maxDischargeWatts) AS maxDischargeWatts, max(maxChargeWatts) AS maxChargeWatts, min(maxDischargeCurrent) AS maxDischargeCurrent, max(maxChargeCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, first(local_dt) AS local_dt INTO battery_db.d1.battery FROM battery_db.m30.battery GROUP BY time(1d), * END

> use _internal
Using database _internal
> select * from cq order by desc limit 10
name: cq
time                hostname queryFail queryOk
----                -------- --------- -------
1684524160000000000 solarPi4 12        7000
1684524150000000000 solarPi4 12        7000
1684524140000000000 solarPi4 12        7000
1684524130000000000 solarPi4 12        7000
1684524120000000000 solarPi4 12        7000
1684524110000000000 solarPi4 12        7000
1684524100000000000 solarPi4 12        7000
1684524090000000000 solarPi4 12        7000
1684524080000000000 solarPi4 12        7000
1684524070000000000 solarPi4 12        7000

old= CREATE CONTINUOUS QUERY cq_temp_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, first(heater) AS heater, sum(heat_interval) AS heater_on, first(heater_watts) AS heater_watts, last(heater_kWhr) AS heater_last_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m5.temp FROM battery_db.s5.temp GROUP BY time(5m), * END
new= CREATE CONTINUOUS QUERY cq_temp_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, last(heater) AS heater, sum(heat_interval) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_kWhr) AS heater_last_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m5.temp FROM battery_db.s5.temp GROUP BY time(5m), * END

select first(local_dt), last(heater) AS heater, sum(heat_interval) AS heater_on, mean(heater_watts) AS heater_watts from m5.temp where time > now()-2h  group by time(5m)

difference  first(heater) AS heater vs  last(heater) AS heater
            first(heater_watts) AS heater_watts  vs  mean(heater_watts) AS heater_watts
cq_temp_m30 also not running

try: copy of new changed to old: CREATE CONTINUOUS QUERY cq_temp_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, first(heater) AS heater, sum(heat_interval) AS heater_on, first(heater_watts) AS heater_watts, last(heater_kWhr) AS heater_last_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m5.temp FROM battery_db.s5.temp GROUP BY time(5m), * END
Works try just changing to mean(heater_watts) AS heater_watts perhaps the field is int and can't take a float
CREATE CONTINUOUS QUERY cq_temp_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, first(heater) AS heater, sum(heat_interval) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_kWhr) AS heater_last_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m5.temp FROM battery_db.s5.temp GROUP BY time(5m), * END
doesn't work try just switching first(heater) to max(heater)
CREATE CONTINUOUS QUERY cq_temp_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heat_interval) AS heater_on, first(heater_watts) AS heater_watts, last(heater_kWhr) AS heater_last_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m5.temp FROM battery_db.s5.temp GROUP BY time(5m), * END 
try same fix on m30.temp and d1.temp
cq_temp_m30 CREATE CONTINUOUS QUERY cq_temp_m30 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heat_interval) AS heater_on, first(heater_watts) AS heater_watts, last(heater_last_kWhr) - first(heater_first_kWhr) AS heater_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m30.temp FROM battery_db.m5.temp GROUP BY time(5m), * END
CREATE CONTINUOUS QUERY cq_temp_d1 ON battery_db BEGIN SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / 3600 AS heater_on, sum(heater_on) / sum(interval) AS "pct.heater_on", sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, first(local_dt) AS local_dt INTO battery_db.d1.temp FROM battery_db.m30.temp GROUP BY time(1d), * END
I don't think d1 has the problem need to check tomorrow.