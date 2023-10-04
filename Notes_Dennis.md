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

Weather data: https://www.ncei.noaa.gov/access/search/data-search/global-hourly?bbox=43.500,-72.000,43.000,-71.000&pageNum=1&startDate=2023-06-01T00:00:00&endDate=2023-06-15T23:59:59

https://www.ncdc.noaa.gov/cdo-web/webservices/v2#gettingStarted 

Weather stations: https://www.ncei.noaa.gov/access/homr/
Station NAME: CONCORD MUNI AP; NCDCID: 20018627; WBAN: 14745; COOPID: 271683; CALL: CON;
LAT: 43.20488; LON: -71.50257; ELEV: 338; ELEV_P: 343; ELEV_A: 26;  UTC: -5; BEGDT: 19960301; 
GHCND: USW00014745; STNTYPE: ASOS,COOP,PLCD

Station type  ASOS = Automated Surface Observing System
              COOP = NWS Cooperative Network
              PLCD = (Primary) Local Climatological Data (First Order)
Elevation is in feet: "The airport is 346 feet above Mean Sea Level"
ELEV_P: 343; is pressure elevation  
ELEV_A: 26 is annimometer above station which is 338 + 26
FM-12 = SYNOP Report of surface observation form a fixed land station
FM-15 = METAR Aviation routine weather report
FM-16 = SPECI Aviation selected special weather report
SOD = Summary of day report from U.S. ASOS or AWOS station
Download station data about 5 days behind

Abbreviation SLP = Sea Level Pressure: download data from CDO looks like "10126,1" @ 2023-06-11T10:51:00 
Weather Underground Histor shows pressure 29.53 at this time
P0 = P1 (1 - (0.0065h/ (T + 0.0065h + 273.15))-5.257
P0 is the calculated mean sea level value in hPa, P1 is the actual measured pressure (station Pressure) in hectopascal (hPa), T is the temperature in degree Celcius (°C), and h is the elevation in meters (m).

API looks promising https://www.weather.gov/documentation/services-web-api
curl -X GET "https://api.weather.gov/stations/KCON/observations" -H "accept: application/geo+json"
https://api.weather.gov/stations/KCON/observations
Observations delayed by about 30 minutes
for forecast this might be the thing: https://github.com/weather-gov/api
We want the LCD data set: for observed data
https://www.weather.gov/documentation/services-web-api#/default/station_observation_list  list of endpoints
pressure in Pascals  to get "Hg divide by 3386.39

2023 Aug, 05
MagnumMonitor_v3.py  worked 
wrote to influxdb on solarpi4
  > show measurements
  name: measurements
  name
  ----
  battery
  inverter
  temp
  > select * FROM s5.inverter
  name: inverter
  time                avgGenWattsIn avgWattsOut        genRunTime genStartMode genStatus interval          inverterFault inverterStatus local_dt            maxWattsOut yr_mo
  ----                ------------- -----------        ---------- ------------ --------- --------          ------------- -------------- --------            ----------- -----
  1691269074191672970 0             1906.3111111111111 0          1            2         5.085854530334473 0             64             2023-08-05T16:57:54 1952        23-08
  1691269079338621832 0             1898.6136363636363 0          1            2         5.08984112739563  0             64             2023-08-05T16:57:59 1936        23-08
  > 

Aug 07, 2023
Need to document Jeff's system
  Hardware: Producer; Model; Revision; Settings; URL references; Instalation Date
    Magnum wiring pannel:
      Magnum inverter: Two
      AGS:
      BMK:
      Monitor / Controler:
    Computers; interfaces; smart plugs; etc

  Software, databases, programs we wrote, etc



  Software: Producer; Version; Instalation Instructions (including dependencies)

Change retention policy:

influx
use battery_db

drop retention policy s30 on battery_db
create retention policy "s30" on "battery_db" duration 2w replication 1 

> show retention policies

create CQs for inverter

CREATE CONTINUOUS QUERY cq_inv_s30 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.s30.inverter FROM battery_db.s5.inverter GROUP BY time(30s), * END

CREATE CONTINUOUS QUERY cq_inv_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.m5.inverter FROM battery_db.s30.inverter GROUP BY time(5m), * END

CREATE CONTINUOUS QUERY cq_inv_m30 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.m30.inverter FROM battery_db.m5.inverter GROUP BY time(30m), * END

CREATE CONTINUOUS QUERY cq_inv_d1 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.d1.inverter FROM battery_db.m30.inverter GROUP BY time(1d), * END

SHOW CONTINUOUS QUERIES
cq_temp_d1  CREATE CONTINUOUS QUERY cq_temp_d1 ON battery_db BEGIN SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / 3600 AS heater_on, sum(heater_on) / sum(interval) AS "pct.heater_on", sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, first(local_dt) AS local_dt INTO battery_db.d1.temp FROM battery_db.m30.temp GROUP BY time(1d), * END
cq_bat_m5   CREATE CONTINUOUS QUERY cq_bat_m5 ON battery_db BEGIN SELECT min(soc) AS min_soc, min(Ahr2empty) AS min_Ahr2empty, min(avgVoltage) AS min_Voltage, mean(avgWatts) AS avgWatts, min(minWatts) AS maxDischargeWatts, max(maxWatts) AS maxChargeWatts, min(minCurrent) AS maxDischargeCurrent, max(maxCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, first(local_dt) AS local_dt INTO battery_db.m5.battery FROM battery_db.s30.battery GROUP BY time(5m), * END
cq_bat_m30  CREATE CONTINUOUS QUERY cq_bat_m30 ON battery_db BEGIN SELECT min(min_soc) AS min_soc, min(min_Ahr2empty) AS min_Ahr2empty, min(min_Voltage) AS min_Voltage, mean(avgWatts) AS avgWatts, min(maxDischargeWatts) AS maxDischargeWatts, max(maxChargeWatts) AS maxChargeWatts, min(maxDischargeCurrent) AS maxDischargeCurrent, max(maxChargeCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) / 3600 AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, first(local_dt) AS local_dt INTO battery_db.m30.battery FROM battery_db.m5.battery GROUP BY time(30m), * END
cq_bat_d1   CREATE CONTINUOUS QUERY cq_bat_d1 ON battery_db BEGIN SELECT min(min_soc) AS min_soc, min(min_Ahr2empty) AS min_Ahr2empty, min(min_Voltage) AS min_Voltage, mean(avgWatts) AS avgWatts, min(maxDischargeWatts) AS maxDischargeWatts, max(maxChargeWatts) AS maxChargeWatts, min(maxDischargeCurrent) AS maxDischargeCurrent, max(maxChargeCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, first(local_dt) AS local_dt INTO battery_db.d1.battery FROM battery_db.m30.battery GROUP BY time(1d), * END
cq_temp_m5  CREATE CONTINUOUS QUERY cq_temp_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heat_interval) AS heater_on, first(heater_watts) AS heater_watts, last(heater_kWhr) AS heater_last_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m5.temp FROM battery_db.s5.temp GROUP BY time(5m), * END
cq_temp_m30 CREATE CONTINUOUS QUERY cq_temp_m30 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heat_interval) AS heater_on, first(heater_watts) AS heater_watts, last(heater_last_kWhr) - first(heater_first_kWhr) AS heater_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m30.temp FROM battery_db.m5.temp GROUP BY time(5m), * END
cq_inv_s30  CREATE CONTINUOUS QUERY cq_inv_s30 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.s30.inverter FROM battery_db.s5.inverter GROUP BY time(30s), * END
cq_inv_m5   CREATE CONTINUOUS QUERY cq_inv_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.m5.inverter FROM battery_db.s30.inverter GROUP BY time(5m), * END
cq_inv_m30  CREATE CONTINUOUS QUERY cq_inv_m30 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.m30.inverter FROM battery_db.m5.inverter GROUP BY time(30m), * END
cq_inv_d1   CREATE CONTINUOUS QUERY cq_inv_d1 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.d1.inverter FROM battery_db.m30.inverter GROUP BY time(1d), * END


Make .csv from measurement table
pi@solarPi4:~/Packet_Listner $ influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from m5.temp' -format csv > mtemp.csv

Aug 11, 2023
Notes on interfacing with charge controller.
Frustrated, posted for help at MakeIt Slack. 
1. right after plugging in device run dmesg
2. on RPi run lsusb 
3. using PySerial   python -m serial.tools.list_ports -v
4. using PySerial  terminal  python -m serial.tools.miniterm --encoding hexlify /dev/ttyACM0 115200
5. install and run Wireshark 

Setting up RPi zero 2w:
1. using Raspberry Pi Imager.app loaded latest 64bit Raspberry Pi OS w/ desktop bulseye released 2023-05-03 
      to 32GB sim card
2. setup on RPi set user: pi   PW: SunShine
set host name: Holt-Pi02w    auto login   enable SSH, SPI, I2C,
Set Boot to Desktop      command startx to get GUI
lsb_release -a
cat /etc/os-release  "version=11 (bullseye)"
df -h    space on flash drive  
  uname -a       Linux raspberrypi 6.1.21-v8+ #1642 SMP PREEMPT Mon apr 3 17:24:16 BST 2023 aarch64 GNU/Linux
	cat /proc/cpuinfo  BCM2835    Raspberry Pi Zero 2 W Rev 1.0
	cat /etc/debian_version  "11.7"
  hostname -I    192.168.0.200   on Rosie
Python v3.9.2
sudo apt install wireshark
sudo usermod -a -G wireshark pi
Running Wireshark crashes the system freezes up 
sudo python -m pip install pyserial   (version 3.5b0)

Pi02sw on jolt
sudo dmesg   # shows recent log activity USB device connected with PID/VID
    VID:04E2 PID:14411  driver cdc_acm   exar corp.  XR21B1411
 followed by lsusb  to get the usb device number
    Bus:1  device:5
 groups pi
 sudo modprobe usbmon  #  must run after each boot
 sudo wireshark
use the device number to monitor the USB with wireshark
capture saved in /usr/sbin/usermod


Check compatibility with cdc_acm
  https://docs.kernel.org/usb/acm.html
  Universal Serial Bus Communication Device Class Abstract Control Model 
  blog issues with cdc_acm: https://michael.stapelberg.ch/posts/2021-04-27-linux-usb-virtual-serial-cdc-acm/
  Exar XR21b1411  https://www.maxlinear.com/product/interface/uarts/usb-uarts/xr21b1411
  downloaded driver source code to: /Users/dennis/Documents/Family/JeffsHouse/Interface/Ben_Discussion/Energy_Monitor/ChargeController/xr_usb_serial_common_lnx-3.6-and-newer-pak

Aug 18, 2023 @ 13:42  
S31B-4913
13:17:20.442 MQT: tele/S31B/STATE = {"Time":"2023-08-18T13:17:20","Uptime":"6T02:15:18","UptimeSec":526518,"Heap":25,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":1,"POWER":"ON","Wifi":{"AP":2,"SSId":"jolt","BSSId":"3C:28:6D:AD:BE:EA","Channel":1,"Mode":"11n","RSSI":100,"Signal":-36,"LinkCount":1,"Downtime":"0T00:00:05"}}
13:17:20.452 MQT: tele/S31B/SENSOR = {"Time":"2023-08-18T13:17:20","ENERGY":{"TotalStartTime":"2022-09-24T18:51:27","Total":196.708,"Yesterday":0.000,"Today":0.000,"Period": 0,"Power": 0,"ApparentPower": 0,"ReactivePower": 0,"Factor":0.00,"Voltage":122,"Current":0.000}}
13:22:20.428 MQT: tele/S31B/STATE = {"Time":"2023-08-18T13:22:20","Uptime":"6T02:20:18","UptimeSec":526818,"Heap":25,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":1,"POWER":"ON","Wifi":{"AP":2,"SSId":"jolt","BSSId":"3C:28:6D:AD:BE:EA","Channel":1,"Mode":"11n","RSSI":100,"Signal":-35,"LinkCount":1,"Downtime":"0T00:00:05"}}
13:22:20.438 MQT: tele/S31B/SENSOR = {"Time":"2023-08-18T13:22:20","ENERGY":{"TotalStartTime":"2022-09-24T18:51:27","Total":196.708,"Yesterday":0.000,"Today":0.000,"Period": 0,"Power": 0,"ApparentPower": 0,"ReactivePower": 0,"Factor":0.00,"Voltage":123,"Current":0.000}}
13:27:20.428 MQT: tele/S31B/STATE = {"Time":"2023-08-18T13:27:20","Uptime":"6T02:25:18","UptimeSec":527118,"Heap":25,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":1,"POWER":"ON","Wifi":{"AP":2,"SSId":"jolt","BSSId":"3C:28:6D:AD:BE:EA","Channel":1,"Mode":"11n","RSSI":100,"Signal":-35,"LinkCount":1,"Downtime":"0T00:00:05"}}
13:27:20.438 MQT: tele/S31B/SENSOR = {"Time":"2023-08-18T13:27:20","ENERGY":{"TotalStartTime":"2022-09-24T18:51:27","Total":196.708,"Yesterday":0.000,"Today":0.000,"Period": 0,"Power": 0,"ApparentPower": 0,"ReactivePower": 0,"Factor":0.00,"Voltage":123,"Current":0.000}}
13:32:20.471 MQT: tele/S31B/STATE = {"Time":"2023-08-18T13:32:20","Uptime":"6T02:30:18","UptimeSec":527418,"Heap":25,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":1,"POWER":"ON","Wifi":{"AP":2,"SSId":"jolt","BSSId":"3C:28:6D:AD:BE:EA","Channel":1,"Mode":"11n","RSSI":100,"Signal":-35,"LinkCount":1,"Downtime":"0T00:00:05"}}
13:32:20.481 MQT: tele/S31B/SENSOR = {"Time":"2023-08-18T13:32:20","ENERGY":{"TotalStartTime":"2022-09-24T18:51:27","Total":196.708,"Yesterday":0.000,"Today":0.000,"Period": 0,"Power": 0,"ApparentPower": 0,"ReactivePower": 0,"Factor":0.00,"Voltage":123,"Current":0.000}}

14:08:12.966 CMD: rule
14:08:12.973 MQT: stat/S31B/RESULT = {"Rule1":{"State":"ON","Once":"OFF","StopOnError":"OFF","Length":54,"Free":457,"Rules":"ON Power1#state=0 DO Backlog Delay 10; Power1 ON ENDON"}}

14:18:17.730 CMD: status
14:18:17.737 MQT: stat/S31B/STATUS = {"Status":{"Module":0,"DeviceName":"S31B","FriendlyName":["S31B"],"Topic":"S31B","ButtonTopic":"0","Power":1,"PowerOnState":3,"LedState":1,"LedMask":"FFFF","SaveData":1,"SaveState":1,"SwitchTopic":"0","SwitchMode":[0,0,0,0,0,0,0,0],"ButtonRetain":0,"SwitchRetain":0,"SensorRetain":0,"PowerRetain":0,"InfoRetain":0,"StateRetain":0}}
14:20:02.615 CMD: status 1
14:20:02.622 MQT: stat/S31B/STATUS1 = {"StatusPRM":{"Baudrate":4800,"SerialConfig":"8E1","GroupTopic":"tasmotas","OtaUrl":"http://ota.tasmota.com/tasmota/release/tasmota.bin.gz","RestartReason":"Power On","Uptime":"6T03:18:00","StartupUTC":"2023-08-12T15:02:02","Sleep":50,"CfgHolder":4617,"BootCount":66,"BCResetTime":"2022-09-24T18:51:27","SaveCount":4803,"SaveAddress":"F9000"}}
14:20:15.508 CMD: status 2
14:20:15.514 MQT: stat/S31B/STATUS2 = {"StatusFWR":{"Version":"12.1.1(tasmota)","BuildDateTime":"2022-08-25T11:33:55","Boot":31,"Core":"2_7_4_9","SDK":"2.2.2-dev(38a443e)","CpuFrequency":80,"Hardware":"ESP8266EX","CR":"331/699"}}
14:20:20.778 CMD: status 3
14:20:20.785 MQT: stat/S31B/STATUS3 = {"StatusLOG":{"SerialLog":0,"WebLog":2,"MqttLog":0,"SysLog":0,"LogHost":"","LogPort":514,"SSId":["Rosie","jolt"],"TelePeriod":300,"Resolution":"558180C0","SetOption":["00008009","2805C80001000680003C5A0A192800000000","00000080","00006000","00004000","00000000"]}}
14:20:24.933 CMD: status 4
14:20:24.945 MQT: stat/S31B/STATUS4 = {"StatusMEM":{"ProgramSize":624,"Free":376,"Heap":25,"ProgramFlashSize":1024,"FlashSize":4096,"FlashChipId":"16405E","FlashFrequency":40,"FlashMode":3,"Features":["00000809","8F9AC787","04368001","000000CF","010013C0","C000F981","00004004","00001000","54000020","00000000"],"Drivers":"1,2,3,4,5,6,7,8,9,10,12,16,18,19,20,21,22,24,26,27,29,30,35,37,45,62","Sensors":"1,2,3,4,5,6"}}
14:20:27.428 MQT: tele/S31B/STATE = {"Time":"2023-08-18T14:20:27","Uptime":"6T03:18:25","UptimeSec":530305,"Heap":25,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":1,"POWER":"ON","Wifi":{"AP":2,"SSId":"jolt","BSSId":"3C:28:6D:AD:BE:EA","Channel":1,"Mode":"11n","RSSI":100,"Signal":-37,"LinkCount":1,"Downtime":"0T00:00:05"}}
14:20:27.440 MQT: tele/S31B/SENSOR = {"Time":"2023-08-18T14:20:27","ENERGY":{"TotalStartTime":"2022-09-24T18:51:27","Total":196.708,"Yesterday":0.000,"Today":0.000,"Period": 0,"Power": 0,"ApparentPower": 0,"ReactivePower": 0,"Factor":0.00,"Voltage":123,"Current":0.000}}
14:20:38.234 CMD: status 5
14:20:38.241 MQT: stat/S31B/STATUS5 = {"StatusNET":{"Hostname":"S31B-4913","IPAddress":"192.168.86.153","Gateway":"192.168.86.1","Subnetmask":"255.255.255.0","DNSServer1":"192.168.86.1","DNSServer2":"0.0.0.0","Mac":"48:3F:DA:28:D3:31","Webserver":2,"HTTP_API":1,"WifiConfig":4,"WifiPower":17.0}}
14:20:43.727 CMD: status 6
14:20:43.734 MQT: stat/S31B/STATUS6 = {"StatusMQT":{"MqttHost":"DietPi","MqttPort":1883,"MqttClientMask":"DVES_%06X","MqttClient":"DVES_28D331","MqttUser":"","MqttCount":1,"MAX_PACKET_SIZE":1200,"KEEPALIVE":30,"SOCKET_TIMEOUT":4}}
14:20:50.047 CMD: status 7
14:20:50.055 MQT: stat/S31B/STATUS7 = {"StatusTIM":{"UTC":"2023-08-18T18:20:50","Local":"2023-08-18T14:20:50","StartDST":"2023-03-12T02:00:00","EndDST":"2023-11-05T02:00:00","Timezone":99,"Sunrise":"05:54","Sunset":"19:43"}}
14:20:55.279 CMD: status 8
14:20:55.289 MQT: stat/S31B/STATUS8 = {"StatusSNS":{"Time":"2023-08-18T14:20:55","ENERGY":{"TotalStartTime":"2022-09-24T18:51:27","Total":196.708,"Yesterday":0.000,"Today":0.000,"Power": 0,"ApparentPower": 0,"ReactivePower": 0,"Factor":0.00,"Voltage":123,"Current":0.000}}}
14:22:34.504 CMD: status 9
14:22:34.510 MQT: stat/S31B/STATUS9 = {"StatusPTH":{"PowerDelta":[0,0,0],"PowerLow":0,"PowerHigh":0,"VoltageLow":0,"VoltageHigh":0,"CurrentLow":0,"CurrentHigh":0}}
14:22:39.231 CMD: status 10
14:22:39.242 MQT: stat/S31B/STATUS10 = {"StatusSNS":{"Time":"2023-08-18T14:22:39","ENERGY":{"TotalStartTime":"2022-09-24T18:51:27","Total":196.708,"Yesterday":0.000,"Today":0.000,"Power": 0,"ApparentPower": 0,"ReactivePower": 0,"Factor":0.00,"Voltage":122,"Current":0.000}}}
14:22:43.278 CMD: status 11
14:22:43.286 MQT: stat/S31B/STATUS11 = {"StatusSTS":{"Time":"2023-08-18T14:22:43","Uptime":"6T03:20:41","UptimeSec":530441,"Heap":25,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":1,"POWER":"ON","Wifi":{"AP":2,"SSId":"jolt","BSSId":"3C:28:6D:AD:BE:EA","Channel":1,"Mode":"11n","RSSI":100,"Signal":-36,"LinkCount":1,"Downtime":"0T00:00:05"}}}
14:22:47.144 CMD: status 12
14:22:47.149 MQT: stat/S31B/RESULT = {"Command":"Error"}

15:00:31.465 MQT: tele/S31B/STATE = {"Time":"2023-08-21T15:00:31","Uptime":"9T03:58:29","UptimeSec":791909,"Heap":25,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":1,"POWER":"OFF","Wifi":{"AP":2,"SSId":"jolt","BSSId":"3C:28:6D:AD:BE:EA","Channel":1,"Mode":"11n","RSSI":100,"Signal":-39,"LinkCount":1,"Downtime":"0T00:00:05"}}
15:00:31.475 MQT: tele/S31B/SENSOR = {"Time":"2023-08-21T15:00:31","ENERGY":{"TotalStartTime":"2022-09-24T18:51:27","Total":196.708,"Yesterday":0.000,"Today":0.000,"Period": 0,"Power": 0,"ApparentPower": 0,"ReactivePower": 0,"Factor":0.00,"Voltage": 0,"Current":0.000}}
15:05:31.427 MQT: tele/S31B/STATE = {"Time":"2023-08-21T15:05:31","Uptime":"9T04:03:29","UptimeSec":792209,"Heap":25,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":1,"POWER":"OFF","Wifi":{"AP":2,"SSId":"jolt","BSSId":"3C:28:6D:AD:BE:EA","Channel":1,"Mode":"11n","RSSI":100,"Signal":-39,"LinkCount":1,"Downtime":"0T00:00:05"}}
15:05:31.437 MQT: tele/S31B/SENSOR = {"Time":"2023-08-21T15:05:31","ENERGY":{"TotalStartTime":"2022-09-24T18:51:27","Total":196.708,"Yesterday":0.000,"Today":0.000,"Period": 0,"Power": 0,"ApparentPower": 0,"ReactivePower": 0,"Factor":0.00,"Voltage": 0,"Current":0.000}}
15:06:50.336 CMD: pulsetime1 0
15:06:50.341 MQT: stat/S31B/RESULT = {"PulseTime1":{"Set":0,"Remaining":0}}
15:06:58.097 CMD: pulsetime
15:06:58.107 MQT: stat/S31B/RESULT = {"PulseTime":{"Set":[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],"Remaining":[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]}}
15:09:10.037 CMD: power on
15:09:10.043 MQT: stat/S31B/RESULT = {"POWER":"ON"}
15:09:10.046 MQT: stat/S31B/POWER = ON
15:09:30.457 CMD: power off
15:09:30.465 MQT: stat/S31B/RESULT = {"POWER":"OFF"}
15:09:30.468 MQT: stat/S31B/POWER = OFF


> create retention policy "m1" on "battery_db" duration 3w replication 1
> show retention policies
name    duration   shardGroupDuration replicaN default
----    --------   ------------------ -------- -------
autogen 0s         168h0m0s           1        false
s5      120h0m0s   24h0m0s            1        true
m5      504h0m0s   24h0m0s            1        false
d1      17472h0m0s 168h0m0s           1        false
d30     0s         168h0m0s           1        false
m30     2016h0m0s  24h0m0s            1        false
s30     336h0m0s   24h0m0s            1        false
m1      504h0m0s   24h0m0s            1        false


pi@DietPi:~/Programs/tempMQTT_V2$ sudo python3 tempMQTT_V2.py
Traceback (most recent call last):
  File "/home/pi/Programs/tempMQTT_V2/tempMQTT_V2.py", line 86, in <module>
    class g_stuff:
  File "/usr/lib/python3.9/dataclasses.py", line 1021, in dataclass
    return wrap(cls)
  File "/usr/lib/python3.9/dataclasses.py", line 1013, in wrap
    return _process_class(cls, init, repr, eq, order, unsafe_hash, frozen)
  File "/usr/lib/python3.9/dataclasses.py", line 863, in _process_class
    cls_fields = [_get_field(cls, name, type)
  File "/usr/lib/python3.9/dataclasses.py", line 863, in <listcomp>
    cls_fields = [_get_field(cls, name, type)
  File "/usr/lib/python3.9/dataclasses.py", line 747, in _get_field
    raise ValueError(f'mutable default {type(f.default)} for field '
ValueError: mutable default <class 'list'> for field sensors is not allowed: use default_factory
pi@DietPi:~/Programs/tempMQTT_V2$ 

Aug 28, 2023
$ influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from m1.temp' -format csv > m1temp2.csv
Sep 05, 2023
Explore Influx query for getting break point at midnight for day
mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, 
mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, last(heater) AS heater, 
sum(heater_on) AS heater_on, last(heater_watts) AS heater_watts, sum(heater_kWhr) AS heater_kWhr, sum(interval) AS interval, 
last(local_dt) AS local_dt, last(yr_mo) AS yr_mo INTO battery_db.m30.temp FROM battery_db.m5.temp GROUP BY time(30m), * END
Try:
select mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, sum(heater_on) AS heater_on, last(heater_watts) AS heater_watts, sum(heater_kWhr) AS heater_kWhr, sum(interval) AS interval, first(local_dt) AS local_dt, last(yr_mo) AS yr_mo FROM battery_db.m5.temp where time > now() - 2h GROUP BY time(30m) 
Result:
time                avg_temp_closet    max_temp_closet min_temp_closet heater_on heater_watts heater_kWhr interval           local_dt            yr_mo
----                ---------------    --------------- --------------- --------- ------------ ----------- --------           --------            -----
1693922400000000000 25.735000000000003 26.375          25.0625         0         0                        1505.1899560000002 2023-09-05T10:05:32 
1693924200000000000 27.131249999999998 27.875          26.375          0         0                        1806.171136        2023-09-05T10:30:37 
1693926000000000000 28.564583333333335 29.125          27.9375         0         0                        1804.7090230000001 2023-09-05T11:00:43 
1693927800000000000 29.489583333333332 29.75           29              0         0                        1806.032221        2023-09-05T11:30:48 
fix cq_temp_m5
drop CONTINUOUS QUERY cq_temp_m5 ON battery_db
CREATE CONTINUOUS QUERY cq_temp_m5 ON battery_db BEGIN select sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heat_interval) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_kWhr) AS heater_last_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m5.temp FROM battery_db.m1.temp GROUP BY time(5m), * END

> select * from m5.temp
name: temp
time                avg_temp_closet avg_temp_outdoor avg_temp_shed heater heater_first_kWhr heater_last_kWhr heater_on heater_watts interval           local_dt            max_temp_closet min_temp_closet yr_mo
----                --------------- ---------------- ------------- ------ ----------------- ---------------- --------- ------------ --------           --------            --------------- --------------- -----
1693937700000000000 31.3125         37.9375          34.9375       0      196.708           196.708          0         0            60.13198           2023-09-05T14:19:17 31.3125         31.3125         23-09
1693938000000000000 31.15           36.625           34.8875       0      196.708           196.708          0         0            300.72813199999996 2023-09-05T14:20:17 31.25           31.0625         23-09
1693938300000000000 30.8875         36.675           34.725        0      196.708           196.708          0         0            300.801738         2023-09-05T14:25:18 30.9375         30.875          23-09
1693938600000000000 31.0125         40.1125          34.6125       0      196.708           196.708          0         0            300.917931         2023-09-05T14:30:18 31.125          30.9375         23-09
1693938900000000000 31.2            39.05            34.725        0      196.708           196.708          0         0            300.85567599999996 2023-09-05T14:35:19 31.25           31.125          23-09
1693939200000000000 31.2375         37.8             34.875        0      196.708           196.708          0         0            300.87778499999996 2023-09-05T14:40:20 31.25           31.1875         23-09
1693939500000000000 31.2625         37.05            35.025        0      196.708           196.708          0         0            301.026586         2023-09-05T14:45:21 31.3125         31.25           23-09
> select sum(interval) AS interval, first(local_dt) AS local_dt, mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heat_on) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_last_kWhr) - first(heater_first_kWhr) AS heater_kWhr FROM battery_db.m5.temp GROUP BY time(30m)
name: temp
time                interval    local_dt            avg_temp_closet    max_temp_closet min_temp_closet avg_temp_shed     avg_temp_outdoor   heater heater_on heater_watts heater_kWhr
----                --------    --------            ---------------    --------------- --------------- -------------     ----------------   ------ --------- ------------ -----------
1693936800000000000 661.66185   2023-09-05T14:19:17 31.116666666666664 31.3125         30.875          34.85             37.079166666666666 0                0            0
1693938600000000000 1805.417995 2023-09-05T14:30:18 31.220833333333335 31.375          30.9375         34.89166666666667 38.34166666666667  0                0            0
1693940400000000000              

mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, 
mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, last(heater) AS heater, 
sum(heater_on) AS heater_on, last(heater_watts) AS heater_watts, sum(heater_kWhr) AS heater_kWhr, sum(interval) AS interval, 
last(local_dt) AS local_dt, last(yr_mo) AS yr_mo INTO battery_db.m30.temp FROM battery_db.m5.temp GROUP BY time(30m), * END

Sept 6, 2023
Check m5.temp; run m30 query test check for yr; run into m30.temp; create cq m30.
I think the tag yr_mo is auto added to CQ but not regular query,
I don't know if you can drop measure in one retention policy eg "drop measurement m30.temp on battery_db"
Otherwise: DROP SHARD <shard_id_number>

select * from m5.temp where time > Now() - 30m

 select sum(interval) AS interval, first(local_dt) AS local_dt, mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heat_on) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_last_kWhr) - first(heater_first_kWhr) AS heater_kWhr, first(yr_mo) AS yr_mo FROM battery_db.m5.temp GROUP BY time(30m)

select sum(interval) AS interval, first(local_dt) AS local_dt, mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heat_on) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_last_kWhr) - first(heater_first_kWhr) AS heater_kWhr, first(yr_mo) AS yr_mo INTO battery_db.m30.temp FROM battery_db.m5.temp GROUP BY time(30m)

select * from m30.temp 

 CREATE CONTINUOUS QUERY cq_temp_m30 ON battery_db BEGIN select sum(interval) AS interval, first(local_dt) AS local_dt, mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heat_on) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_last_kWhr) - first(heater_first_kWhr) AS heater_kWhr INTO battery_db.m30.temp FROM battery_db.m5.temp GROUP BY time(30m), * END

 ** now for d1
select * from d1.temp
SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / sum(interval) AS "pct.heater_on", sum(heater_on) / 3600 AS heater_on, sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, first(local_dt) AS local_dt, first(yr_mo) AS yr_mo FROM battery_db.m30.temp GROUP BY time(1d, -4h)

SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / sum(interval) AS "pct.heater_on", sum(heater_on) / 3600 AS heater_on, sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, first(local_dt) AS local_dt, first(yr_mo) AS yr_mo INTO battery_db.d1.temp FROM battery_db.m30.temp GROUP BY time(1d, -4h)
 
select * from d1.temp

 CREATE CONTINUOUS QUERY cq_temp_d1 ON battery_db BEGIN SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / sum(interval) AS "pct.heater_on", sum(heater_on) / 3600 AS heater_on, sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, first(local_dt) AS local_dt INTO battery_db.d1.temp FROM battery_db.m30.temp GROUP BY time(1d, -4h), * END

DROP MEASUREMENT "d1.temp"
precision rfc3339
influx_inspect report [ options ] <path>    # shard level report also command export
influx_inspect export -database mydb -retention autogen
<path>   data directory  ~/.influxdb/data/
find .influxdb
ls -al 

check if m5.temp has tag yr_mo
select * from "battery_db"."m5"."temp" where time > now() - 30m group by "yr_mo"
SELECT * FROM ketag.a_year.downsampled_value should work. If not try running SELECT mean(*) INTO ketag.a_year.downsampled_value FROM ketag.autogen.single_measurements GROUP BY time(15s), *

*** DELETE FROM <measurement_name> WHERE [<tag_key>='<tag_value>'] | [<time interval>]
*** each retention policy should use different measurement names because some management commands don't support specifying retention policy  eg. delete from m30.temp where "yr_mo" = ''
  result: ERR: error parsing query: retention policy not supported at line 1, char 1

NEED TO RENAMING measurement in each retention policy:

name    duration   shardGroupDuration replicaN default
----    --------   ------------------ -------- -------
autogen 0s         168h0m0s           1        false
s5      120h0m0s   24h0m0s            1        true
m5      504h0m0s   24h0m0s            1        false
d1      17472h0m0s 168h0m0s           1        false
d30     0s         168h0m0s           1        false
m30     2016h0m0s  24h0m0s            1        false
s30     336h0m0s   24h0m0s            1        false
m1      504h0m0s   24h0m0s            1        false

show field keys & show tag keys  only works on default retention policy 
  work around copy rp.measurement to default rp then show field keys
  > select * into s5.m30_temp from m30.temp
  > show field keys
name: inverter
fieldKey       fieldType
--------       ---------
avgGenWattsIn  float
avgWattsOut    float
genRunTime     float
genStartMode   integer
genStatus      integer
interval       float
inverterFault  integer
inverterStatus integer
local_dt       string
maxWattsOut    float

name: m30_temp
fieldKey         fieldType
--------         ---------
avg_temp_closet  float
avg_temp_outdoor float
avg_temp_shed    float
heater           integer
heater_kWhr      float
heater_watts     float
interval         float
local_dt         string
max_temp_closet  float
min_temp_closet  float
yr_mo            string

 ** now for d1
select * from d1.temp
SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / sum(interval) AS "pct.heater_on", sum(heater_on) / 3600 AS heater_on, sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, first(local_dt) AS local_dt, first(yr_mo) AS yr_mo FROM battery_db.m30.temp GROUP BY time(1d, -4h)

SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / sum(interval) AS "pct.heater_on", sum(heater_on) / 3600 AS heater_on, sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, first(local_dt) AS local_dt, first(yr_mo) AS yr_mo INTO battery_db.d1.temp FROM battery_db.m30.temp GROUP BY time(1d, -4h)
 
select * from d1.temp

 CREATE CONTINUOUS QUERY cq_temp_d1 ON battery_db BEGIN SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / sum(interval) AS "pct.heater_on", sum(heater_on) / 3600 AS heater_on, sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, first(local_dt) AS local_dt INTO battery_db.d1.temp FROM battery_db.m30.temp GROUP BY time(1d, -4h), * END

DROP MEASUREMENT "d1.temp"
precision rfc3339
SELECT mean(avg_temp_closet) AS avg_temp_closet, count(avg_temp_closet) as cnt, sum(heater_kWhr) AS heater_kWhr, first(local_dt) AS local_dt, first(yr_mo) AS yr_mo  FROM battery_db.m30.temp where time > Now() - 3d GROUP BY time(1d, -4h)

PROBLEM  heater_on missing in m30  which should be sum(heater_on) which is usually 0 now
  issue misspelled heater_on as heat_on
deleated and recreated CQ writing to new measurement name

CREATE CONTINUOUS QUERY cq_temp_m30 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heater_on) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_last_kWhr) - first(heater_first_kWhr) AS heater_kWhr INTO battery_db.m30.m30_temp FROM battery_db.m5.temp GROUP BY time(30m), * END

found heater_on field is missing  ?? why ??  deleted measurement and CQ then recreated CQ

fields should be: 13 [time, interval, locaal_dt, avg_temp_closet, max_temp_closet, min_temp_closet, 
    avg_temp_shed, avg_temp_outdoor, heater, heater_on, heater_watts, heater_kWhr, yr_mo]
Fields were there but only one record for latest 30 minute group.

trying to query into measurement and have tag field
SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heater_on) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_last_kWhr) - first(heater_first_kWhr) AS heater_kWhr INTO battery_db.s5.m30_test FROM battery_db.m5.temp GROUP BY time(30m), "yr_mo" 

it worked!!!!
> select * from s5.m30_test limit 10
name: m30_test
time                 avg_temp_closet    avg_temp_outdoor   avg_temp_shed      heater heater_kWhr heater_on heater_watts interval           local_dt            max_temp_closet min_temp_closet yr_mo
----                 ---------------    ----------------   -------------      ------ ----------- --------- ------------ --------           --------            --------------- --------------- -----
2023-09-05T18:00:00Z 31.116666666666664 37.079166666666666 34.85              0      0           0         0            661.66185          2023-09-05T14:19:17 31.3125         30.875          23-09
2023-09-05T18:30:00Z 31.220833333333335 38.34166666666667  34.89166666666667  0      0           0         0            1805.417995        2023-09-05T14:30:18 31.375          30.9375         23-09
2023-09-05T19:00:00Z 31.256250000000005 35.625             35.037499999999994 0      0           0         0            1805.510006        2023-09-05T15:00:24 31.3125         31.125          23-09


SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heater_on) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_last_kWhr) - first(heater_first_kWhr) AS heater_kWhr INTO battery_db.s5.m30_test2 FROM battery_db.m5.temp where time < '2023-09-07T15:30:00Z' GROUP BY time(30m), "yr_mo"

see if m30.m30_temp gets filled with older CQ output
right now looks like it worked
select * from m30.m30_temp where time > now() - 3h

Sep 9, 2023

CREATE CONTINUOUS QUERY cq_temp_d1 ON battery_db BEGIN SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / sum(interval) AS "pct.heater_on", sum(heater_on) / 3600 AS heater_on, sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, first(local_dt) AS local_dt INTO battery_db.d1.d1_temp FROM battery_db.m30.m30_temp GROUP BY time(1d, 4h), * END
> show measurements
name: measurements
name
----
battery
d1_temp
inverter
lowPack
m30_temp
m30_test
m30_test2
temp
> select * from m30.m30_temp limit 2
name: m30_temp
time                 avg_temp_closet    avg_temp_outdoor   avg_temp_shed     heater heater_kWhr heater_on heater_watts interval    local_dt            max_temp_closet min_temp_closet yr_mo
----                 ---------------    ----------------   -------------     ------ ----------- --------- ------------ --------    --------            --------------- --------------- -----
2023-09-05T18:00:00Z 31.116666666666664 37.079166666666666 34.85             0      0           0         0            661.66185   2023-09-05T14:19:17 31.3125         30.875          23-09
2023-09-05T18:30:00Z 31.220833333333335 38.34166666666667  34.89166666666667 0      0           0         0            1805.417995 2023-09-05T14:30:18 31.375          30.9375         23-09

Sept 11, 2023
influx -precision 'rfc3339' -database 'battery_db' 
show retention policies
name    duration   shardGroupDuration replicaN default
----    --------   ------------------ -------- -------
autogen 0s         168h0m0s           1        false
s5      120h0m0s   24h0m0s            1        true
m5      504h0m0s   24h0m0s            1        false
d1      17472h0m0s 168h0m0s           1        false
d30     0s         168h0m0s           1        false
m30     2016h0m0s  24h0m0s            1        false
s30     336h0m0s   24h0m0s            1        false
m1      504h0m0s   24h0m0s            1        false

show measurements [battery, d1_temp, inverter, lowPack, m30_temp, m30_test, m30_test2, temp]
select * from s5.temp limit 2 #empty [s5.temp, s30.temp, d1.temp, d30_temp]
m1.temp [time, heat_interval, heater, heater_kWhr, heater_watts, interval, local_dt, temp_closet, temp_outdoor, temp_shed, yr_mo]
m5.temp [time, avg_temp_closet, avg_temp_outdoor, avg_temp_shed, heater, heater_first_kWhr, heater_last_kWhr, heater_on, heater_watts, interval, local_dt, max_temp_closet, min_temp_closet, yr_mo]
m30.temp [time, avg_temp_closet, avg_temp_outdoor, avg_temp_shed, heater, heater_kWhr, heater_watts, interval, local_dt, max_temp_closet, min_temp_closet, yr_mo]
m30.m30_temp [time, avg_temp_closet, avg_temp_outdoor, avg_temp_shed, heater, heater_kWhr, heater_on, heater_watts, interval, local_dt, max_temp_closet, min_temp_closet, yr_mo]
d1.d1_temp [time, avg_temp_closet, avg_temp_outdoor, avg_temp_shed, heater_kWhr, heater_on, interval, local_dt, max_temp_closet, min_temp_closet, pct.heater_on, yr_mo]
> show continuous queries
name        query
----        -----
cq_bat_m5   CREATE CONTINUOUS QUERY cq_bat_m5 ON battery_db BEGIN SELECT min(soc) AS min_soc, min(Ahr2empty) AS min_Ahr2empty, min(avgVoltage) AS min_Voltage, mean(avgWatts) AS avgWatts, min(minWatts) AS maxDischargeWatts, max(maxWatts) AS maxChargeWatts, min(minCurrent) AS maxDischargeCurrent, max(maxCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, first(local_dt) AS local_dt INTO battery_db.m5.battery FROM battery_db.s30.battery GROUP BY time(5m), * END
cq_bat_m30  CREATE CONTINUOUS QUERY cq_bat_m30 ON battery_db BEGIN SELECT min(min_soc) AS min_soc, min(min_Ahr2empty) AS min_Ahr2empty, min(min_Voltage) AS min_Voltage, mean(avgWatts) AS avgWatts, min(maxDischargeWatts) AS maxDischargeWatts, max(maxChargeWatts) AS maxChargeWatts, min(maxDischargeCurrent) AS maxDischargeCurrent, max(maxChargeCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) / 3600 AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, first(local_dt) AS local_dt INTO battery_db.m30.battery FROM battery_db.m5.battery GROUP BY time(30m), * END
cq_bat_d1   CREATE CONTINUOUS QUERY cq_bat_d1 ON battery_db BEGIN SELECT min(min_soc) AS min_soc, min(min_Ahr2empty) AS min_Ahr2empty, min(min_Voltage) AS min_Voltage, mean(avgWatts) AS avgWatts, min(maxDischargeWatts) AS maxDischargeWatts, max(maxChargeWatts) AS maxChargeWatts, min(maxDischargeCurrent) AS maxDischargeCurrent, max(maxChargeCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, first(local_dt) AS local_dt INTO battery_db.d1.battery FROM battery_db.m30.battery GROUP BY time(1d), * END
cq_inv_s30  CREATE CONTINUOUS QUERY cq_inv_s30 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.s30.inverter FROM battery_db.s5.inverter GROUP BY time(30s), * END
cq_inv_m5   CREATE CONTINUOUS QUERY cq_inv_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.m5.inverter FROM battery_db.s30.inverter GROUP BY time(5m), * END
cq_inv_m30  CREATE CONTINUOUS QUERY cq_inv_m30 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.m30.inverter FROM battery_db.m5.inverter GROUP BY time(30m), * END
cq_inv_d1   CREATE CONTINUOUS QUERY cq_inv_d1 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.d1.inverter FROM battery_db.m30.inverter GROUP BY time(1d), * END
cq_temp_m5  CREATE CONTINUOUS QUERY cq_temp_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heat_interval) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_kWhr) AS heater_last_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m5.temp FROM battery_db.m1.temp GROUP BY time(5m), * END
cq_temp_m30 CREATE CONTINUOUS QUERY cq_temp_m30 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heater_on) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_last_kWhr) - first(heater_first_kWhr) AS heater_kWhr INTO battery_db.m30.m30_temp FROM battery_db.m5.temp GROUP BY time(30m), * END
cq_temp_d1  CREATE CONTINUOUS QUERY cq_temp_d1 ON battery_db BEGIN SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / sum(interval) AS "pct.heater_on", sum(heater_on) / 3600 AS heater_on, sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, first(local_dt) AS local_dt INTO battery_db.d1.d1_temp FROM battery_db.m30.m30_temp GROUP BY time(1d, 4h), * END
exit
influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from m1.temp' -format csv > m1.temp.csv
influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from m5.temp' -format csv > m5.temp.csv
influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from m30.temp' -format csv > m30.temp.csv
influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from m30.m30_temp' -format csv > m30.m30_temp.csv
influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from d1.d1_temp' -format csv > d1.d1_temp.csv
Sep12,2023
Shard = TSM file on disk

Sept12,2023
influx -precision 'rfc3339' -database 'battery_db' 

check records in d1_temp   select * from d1.d1_temp
test Production/tempMQTT  change service to tempMQTT & run
sudo cp ....service /lib/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable tempMQTT.service
  sudo systemctl start tempMQTT.service	

query into m1.m1_temp from m1.temp

drop continuous query "cq_temp_m5" on "battery_db"
CREATE CONTINUOUS QUERY cq_temp_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heat_interval) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_kWhr) AS heater_last_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m5.m5_temp FROM battery_db.m1.m1_temp GROUP BY time(5m), * END

drop continuous query "cq_temp_m30" on "battery_db"
CREATE CONTINUOUS QUERY cq_temp_m30 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heater_on) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_last_kWhr) - first(heater_first_kWhr) AS heater_kWhr INTO battery_db.m30.m30_temp FROM battery_db.m5.m5_temp GROUP BY time(30m), * END

drop continuous query "cq_temp_d1" on "battery_db"
CREATE CONTINUOUS QUERY cq_temp_d1 ON battery_db BEGIN SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / sum(interval) AS "pct_heater_on", sum(heater_on) / 3600 AS heater_on, sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, first(local_dt) AS local_dt INTO battery_db.d1.d1_temp FROM battery_db.m30.m30_temp GROUP BY time(1d, 4h), * END

Check d1.d1_temp does it start 9/5  if not query into

select time as time, heat_interval as heat_interval, heater as heater, heater_kWhr as heater_kWhr, interval as interval, local_dt as local_dt, temp_closet as temp_closet, temp_outdoor as temp_outdoor, temp_shed as temp_shed, yr_mo_1 as yr_mo into m1.test_m1_temp from m1.m1_temp where time > '2023-09-12T18:08:13.769967933Z'
*** heater_watts gets dropped and tag 'yr_mo' gets new data to be 'yr_mo_1'  ??

d1.d1_temp only goes back to 9/9
select time as time, avg_temp_closet as avg_temp_closet, avg_temp_outdoor as avg_temp_outdoor, avg_temp_shed as avg_temp_shed, heater_kWhr as heater_kWhr, heater_on as heater_on, interval as interval, local_dt as local_dt, max_temp_closet as max_temp_closet, min_temp_closet as min_temp_closet, pct.heater_on as pct_heater_on into "test_d1_temp" from d1.d1_temp where yr_mo = "23-09"
show measurements
name: measurements
name
----
battery
d1_temp
inverter
lowPack
m1_temp
m30_temp
m30_test
m30_test2
m5_temp
temp
test_m1_temp
test_m1_temp_2

 SHOW SERIES
key
---
battery,yr_mo=23-05
battery,yr_mo=23-06
battery,yr_mo=23-07
battery,yr_mo=23-08
battery,yr_mo=23-09
d1_temp,yr_mo=23-09
inverter,yr_mo=23-08
inverter,yr_mo=23-09
lowPack
m1_temp
m1_temp,yr_mo=23-09
m30_temp,yr_mo=23-09
m30_test,yr_mo=23-09
m30_test2,yr_mo=23-09
m5_temp,yr_mo=23-09
temp,yr_mo=23-09
test_m1_temp
test_m1_temp_2

 show field keys
name: inverter
fieldKey       fieldType
--------       ---------
avgGenWattsIn  float
avgWattsOut    float
genRunTime     float
genStartMode   integer
genStatus      integer
interval       float
inverterFault  integer
inverterStatus integer
local_dt       string
maxWattsOut    float

name: m30_test
fieldKey         fieldType
--------         ---------
avg_temp_closet  float
avg_temp_outdoor float
avg_temp_shed    float
heater           integer
heater_kWhr      float
heater_on        float
heater_watts     float
interval         float
local_dt         string
max_temp_closet  float
min_temp_closet  float

name: m30_test2
fieldKey         fieldType
--------         ---------
avg_temp_closet  float
avg_temp_outdoor float
avg_temp_shed    float
heater           integer
heater_kWhr      float
heater_on        float
heater_watts     float
interval         float
local_dt         string
max_temp_closet  float
min_temp_closet  float

Sept 13, 2023
influx -precision 'rfc3339' -database 'battery_db' 
measurements [battery, d1_temp, inverter, lowPack, m1_temp, m30_temp, m30_test, m5_temp, 
      temp, test_m1_temp, test_m1_temp_2]
select * into t_m1_temp from m1.m1_temp
> select * from t_m1_temp limit 2  from 9/12 14:17 to 9/13 9:38 top has heater_watts & yr_mo blank
name: t_m1_temp
time                           heat_interval heater heater_kWhr heater_watts interval  local_dt            temp_closet temp_outdoor temp_shed yr_mo
----                           ------------- ------ ----------- ------------ --------  --------            ----------- ------------ --------- -----
2023-09-12T18:17:29.373458975Z 0             0      196.708                  0         2023-09-12T14:17:29 25.25       30.6875      28.875    

select * from m1.test_m1_temp  09-12T14:17 to 09-12T14:40 w/ heater_watts & yr_mo missing
select * from m1.test_m1_temp_2 09-12T14:42 to 09-12T15:08 w/ all fields
select * from m1.temp  09-05T14:19 to 09-12T14:08 w/ all fields
select * into m1.t2_m1_temp from m1.temp 09-05T14:19 to 09-12T14:08 w/ all fields
select * into m1.t2_m1_temp from m1.test_m1_temp_2 09-05T14:19 to 09-12T15:17 w/ all fields
DELETE from m1_temp where time <= '2023-09-12T19:17:39.628524975Z'
select * into m1.m1_temp from m1.t2_m1_temp
Now m1.m1_temp 09-05T14:19 to 09-13T10:37 w/ all fields yea we did it!!!

now work on m5.m5_temp 09-12T14:50 to 09-13T10:35   w/ 14 fields
m5.temp 09-05T14:19 to 09-12T14:05 w/14 fields
select * into m5.m5_temp from m5.temp 09-05T14:19 to 09-13T10:45 w/ all fields 

now work on m30.m30_temp 09-05T14:19 to 09-13T10:00 w/   13 fields great it is all there
m30.temp 09-05T14:30 to 09-07T11:00    missing field heater_on
DROP MEASUREMENT "m30_test" then list measurements and it is still there ??? why

select * from d1.d1_temp 09-09T00:00 to 09-12T00:00   w/ 12 fields

measurements [battery, d1_temp, inverter, lowPack, m1_temp, m30_temp, m30_test, m5_temp, temp]
select * from m1.m1_temp limit 2
time                          heat_interval heater heater_kWhr heater_watts interval  local_dt            temp_closet temp_outdoor temp_shed yr_mo yr_mo_1
2023-09-05T18:19:17.35065984Z 0             0      196.708     0            60.13198  2023-09-05T14:19:17 31.3125     37.9375      34.9375   23-09 
select * from m5.m5_temp limit 2
time                 avg_temp_closet avg_temp_outdoor avg_temp_shed heater heater_first_kWhr heater_last_kWhr heater_on heater_watts interval           local_dt            max_temp_closet min_temp_closet yr_mo yr_mo_1
2023-09-05T18:15:00Z 31.3125         37.9375          34.9375       0      196.708           196.708          0         0            60.13198           2023-09-05T14:19:17 31.3125         31.3125         23-09 
select * from m30.m30_temp limit 2
time                 avg_temp_closet    avg_temp_outdoor   avg_temp_shed     heater heater_kWhr heater_on heater_watts interval    local_dt            max_temp_closet min_temp_closet yr_mo
2023-09-05T18:00:00Z 31.116666666666664 37.079166666666666 34.85             0      0           0         0            661.66185   2023-09-05T14:19:17 31.3125         30.875          23-09
select * from d1.d1_temp limit 2
time                 avg_temp_closet   avg_temp_outdoor  avg_temp_shed      heater_kWhr heater_on interval           local_dt            max_temp_closet min_temp_closet pct.heater_on yr_mo
2023-09-09T04:00:00Z 24.65749782986111 26.00430049189815 27.792393663194446 0           0         23.998204180195835 2023-09-09T00:00:49 29.3125         20.875          0             23-09

select * from s30.battery limit 2
time                           Ahr2empty   avgCurrent          avgVoltage        avgWatts            interval           kWh_charge      kWh_discharge   local_dt            maxCurrent maxWatts minCurrent minWatts pak2ndMinT pak2ndMinT_ID pak2ndMinV pak2ndMinV_ID pakMinT pakMinT_ID pakMinV pakMinV_ID soc   yr_mo
2023-08-30T00:00:18.984813643Z 525.310625  -20.271372549019606 54.26627450980395 -1100.1801960784312 30.335526943206787 18.102048828125 16.565533203125 2023-08-29T20:00:18 -19.76     -999     -20.93     -1136.26 20         23            3.87       20            20      24         3.87    24         87.4  23-08
select * from m5.battery limit 2
time                 avgWatts            interval           kWh_charge     kWh_discharge   local_dt            maxChargeCurrent maxChargeWatts maxDischargeCurrent maxDischargeWatts min_Ahr2empty min_Voltage       min_soc pakMinT pakMinV yr_mo
2023-08-23T00:00:00Z -1596.8266938937968 307.91149497032166 25.28306640625 18.103919921875 2023-08-22T20:00:01 -28.74           -999           -40.9               -2162.03          478.23540625  52.92211538461538 79.57   18      3.775   23-08
select * from m30.battery limit 2
time                 avgWatts           interval           kWh_charge       kWh_discharge   local_dt            maxChargeCurrent maxChargeWatts maxDischargeCurrent maxDischargeWatts min_Ahr2empty min_Voltage       min_soc pakMinT pakMinV yr_mo
2023-06-21T00:00:00Z -596.9790686589818 0.4985120367341571 11.5519091796875 8.779634765625  2023-06-20T20:00:03 -8.58            -482.53        -36.29              -2030.24          585.51225     56.19085714285716 97.42   17      4       23-06
select * from d1.battery limit 2
time                 Ahr2empty avgCurrent avgVoltage avgWatts            interval           
2023-05-14T00:00:00Z                                 -1252.0871477378275 3.4596338913175795 
kWh_charge      kWh_discharge    local_dt            maxChargeCurrent maxChargeWatts maxCurrent 
11.313994140625 9.130220703125   2023-05-14T19:59:47 -4.06            -230.46                   
maxDischargeCurrent maxDischargeWatts maxWatts minCurrent minWatts min_Ahr2empty min_Voltage 
-128.85             -7183.28                                       521.66225                 
min_m30Voltage     min_soc pak2ndMinT pak2ndMinT_ID pak2ndMinV pak2ndMinV_ID pakMinT pakMinT_ID pakMinV 
54.15566666666669  86.79                                                     15                 3.
pakMinV_ID soc yr_mo
86                   23-05

select * from s5.inverter limit 2
time                           avgGenWattsIn avgWattsOut        genRunTime genStartMode genStatus interval          inverterFault inverterStatus local_dt            maxWattsOut yr_mo
2023-09-08T00:00:01.717458429Z 0             1680.5652173913043 0          1            2         5.011566638946533 0             64             2023-09-07T20:00:01 1694        23-09

select * from s30.inverter limit 2
time                 avgGenWattsIn avgWattsOut       genRunTime genStartMode genStatus interval          inverterFault inverterStatus local_dt            maxWattsOut yr_mo
2023-08-30T00:00:00Z 0             959.779973649539  0          1            2         30.23245644569397 0             64             2023-08-29T20:00:28 976         23-08

select * from m5.inverter limit 2
time                 avgGenWattsIn avgWattsOut        genRunTime genStartMode genStatus interval          inverterFault inverterStatus local_dt            maxWattsOut yr_mo
2023-08-23T00:00:00Z 0             1468.3706138586126 0          1            2         288.8119869232178 0             64             2023-08-22T20:04:55 1952        23-08

select * from m30.inverter limit 2
time                 avgGenWattsIn avgWattsOut        genRunTime genStartMode genStatus interval           inverterFault inverterStatus local_dt            maxWattsOut yr_mo
2023-08-09T17:00:00Z 0             1042.8473752693774 0          1            2         121.32385635375977 0             64             2023-08-09T13:20:31 1230        23-08
select * from d1.inverter limit 2
time                 avgGenWattsIn avgWattsOut        genRunTime genStartMode genStatus interval          inverterFault inverterStatus local_dt            maxWattsOut yr_mo
2023-08-09T00:00:00Z 0             1251.4424877590013 0          1            2         22287.3478910923  0             64             2023-08-09T19:59:57 6960        23-08
select * from d1.lowPack limit 2
time                           Ahr2empty  avgVoltage        local_dt            medianV pak2ndMinV pak2ndMinV_ID pakMinV pakMinV_ID soc
2023-08-26T21:17:34.957820213Z 580.882125 55.72611111111112 2023-08-26T17:17:34 3.975   3.975      24            3.975   28         96.65

show continuous queries
name: battery_db
cq_bat_m5   CREATE CONTINUOUS QUERY cq_bat_m5 ON battery_db BEGIN SELECT min(soc) AS min_soc, min(Ahr2empty) AS min_Ahr2empty, min(avgVoltage) AS min_Voltage, mean(avgWatts) AS avgWatts, min(minWatts) AS maxDischargeWatts, max(maxWatts) AS maxChargeWatts, min(minCurrent) AS maxDischargeCurrent, max(maxCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, first(local_dt) AS local_dt INTO battery_db.m5.battery FROM battery_db.s30.battery GROUP BY time(5m), * END

cq_bat_m30  CREATE CONTINUOUS QUERY cq_bat_m30 ON battery_db BEGIN SELECT min(min_soc) AS min_soc, min(min_Ahr2empty) AS min_Ahr2empty, min(min_Voltage) AS min_Voltage, mean(avgWatts) AS avgWatts, min(maxDischargeWatts) AS maxDischargeWatts, max(maxChargeWatts) AS maxChargeWatts, min(maxDischargeCurrent) AS maxDischargeCurrent, max(maxChargeCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) / 3600 AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, first(local_dt) AS local_dt INTO battery_db.m30.battery FROM battery_db.m5.battery GROUP BY time(30m), * END

cq_bat_d1   CREATE CONTINUOUS QUERY cq_bat_d1 ON battery_db BEGIN SELECT min(min_soc) AS min_soc, min(min_Ahr2empty) AS min_Ahr2empty, min(min_Voltage) AS min_Voltage, mean(avgWatts) AS avgWatts, min(maxDischargeWatts) AS maxDischargeWatts, max(maxChargeWatts) AS maxChargeWatts, min(maxDischargeCurrent) AS maxDischargeCurrent, max(maxChargeCurrent) AS maxChargeCurrent, max(kWh_charge) AS kWh_charge, max(kWh_discharge) AS kWh_discharge, sum(interval) AS interval, min(pakMinT) AS pakMinT, min(pakMinV) AS pakMinV, first(local_dt) AS local_dt INTO battery_db.d1.battery FROM battery_db.m30.battery GROUP BY time(1d), * END

cq_inv_s30  CREATE CONTINUOUS QUERY cq_inv_s30 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.s30.inverter FROM battery_db.s5.inverter GROUP BY time(30s), * END

cq_inv_m5   CREATE CONTINUOUS QUERY cq_inv_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.m5.inverter FROM battery_db.s30.inverter GROUP BY time(5m), * END

cq_inv_m30  CREATE CONTINUOUS QUERY cq_inv_m30 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.m30.inverter FROM battery_db.m5.inverter GROUP BY time(30m), * END

cq_inv_d1   CREATE CONTINUOUS QUERY cq_inv_d1 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.d1.inverter FROM battery_db.m30.inverter GROUP BY time(1d), * END

cq_temp_m5  CREATE CONTINUOUS QUERY cq_temp_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(temp_closet) AS avg_temp_closet, max(temp_closet) AS max_temp_closet, min(temp_closet) AS min_temp_closet, mean(temp_shed) AS avg_temp_shed, mean(temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heat_interval) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_kWhr) AS heater_last_kWhr, first(heater_kWhr) AS heater_first_kWhr INTO battery_db.m5.m5_temp FROM battery_db.m1.m1_temp GROUP BY time(5m), * END

cq_temp_m30 CREATE CONTINUOUS QUERY cq_temp_m30 ON battery_db BEGIN SELECT sum(interval) AS interval, first(local_dt) AS local_dt, mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, max(heater) AS heater, sum(heater_on) AS heater_on, mean(heater_watts) AS heater_watts, last(heater_last_kWhr) - first(heater_first_kWhr) AS heater_kWhr INTO battery_db.m30.m30_temp FROM battery_db.m5.m5_temp GROUP BY time(30m), * END

cq_temp_d1  CREATE CONTINUOUS QUERY cq_temp_d1 ON battery_db BEGIN SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / sum(interval) AS "pct_heater_on", sum(heater_on) / 3600 AS heater_on, sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, first(local_dt) AS local_dt INTO battery_db.d1.d1_temp FROM battery_db.m30.m30_temp GROUP BY time(1d, 4h), * END

Issues:
m1.m1_temp  extra field yr_mo_1  also in m5.m5_temp  # seems to have fixed it's self
d1.d1_temp field pct.heater_on should be pct_heater_on # cleaned up 9/15 need to check after d1 runs
s30.battery  maxWatts -999  program issue  
m5.battery maxChargeWatts -999 
d1.battery a bit messed up ***
time                 Ahr2empty avgCurrent avgVoltage avgWatts            interval           
2023-05-14T00:00:00Z                                 -1252.0871477378275 3.4596338913175795 
kWh_charge      kWh_discharge    local_dt            maxChargeCurrent maxChargeWatts maxCurrent 
11.313994140625 9.130220703125   2023-05-14T19:59:47 -4.06            -230.46                   
maxDischargeCurrent maxDischargeWatts maxWatts minCurrent minWatts min_Ahr2empty min_Voltage 
-128.85             -7183.28                                       521.66225                 
min_m30Voltage     min_soc pak2ndMinT pak2ndMinT_ID pak2ndMinV pak2ndMinV_ID pakMinT pakMinT_ID pakMinV 
54.15566666666669  86.79                                                     15                 3.
pakMinV_ID soc yr_mo
86                   23-05

sept 15, 2023
cleaned up cq_temp_d1 9/15 need to check after it runs in a day or so
select * from s30.battery limit 2  from 08-31T20:00 to 09-15T09:52  local time  
max_watts seems to be ok at the beginning -496.46 at the end 2135.52 
however at the end minWatts = 999 3 out of 5 records so can it be sometimes????

check the start and end time of each measure

m1_temp         from 09-12T14:17 
m5_temp         from 09-05T14:19
m30_temp        from 09-05T14:30
d1_temp         from 09-09T00:00     query and add older data from m30
s30.battery     from 08-29T20:00
m5.battery      from 08-22T20:00
m30.battery     from 06-20T20:00
d1.battery      from 05-14T19:59
s5.inverter     from 09-07T20:00
s30.inverter    from 08-30T00:00
m5.inverter     from 08-23T00:00
m30.inverter    from 08-09T17:00
d1.inverter     from 08-09T00:00

SELECT mean(avg_temp_closet) AS avg_temp_closet, max(max_temp_closet) AS max_temp_closet, min(min_temp_closet) AS min_temp_closet, mean(avg_temp_shed) AS avg_temp_shed, mean(avg_temp_outdoor) AS avg_temp_outdoor, sum(heater_on) / sum(interval) AS pct_heater_on, sum(heater_on) / 3600 AS heater_on, sum(interval) / 3600 AS interval, sum(heater_kWhr) AS heater_kWhr, first(local_dt) AS local_dt INTO battery_db.d1.t2_d1_temp FROM battery_db.m30.m30_temp GROUP BY time(1d, 4h), *
select * from d1.d1_temp
select * from d1.t2_d1_temp
select * into d1.d1_temp from d1.t2_d1_temp where time < '2023-09-09T04:00:00Z'
select * from d1.d1_temp

Turn heater lights on for a while 

Work through battery measures
select * from s30.battery where time > now() - 1m
time                           Ahr2empty   avgCurrent          avgVoltage        avgWatts            
2023-08-30T00:00:18.984813643Z 525.310625  -20.271372549019606 54.26627450980395 -1100.1801960784312 
interval           kWh_charge      kWh_discharge   local_dt            maxCurrent maxWatts minCurrent 
30.335526943206787 18.102048828125 16.565533203125 2023-08-29T20:00:18 -19.76     -999     -20.93     
minWatts pak2ndMinT pak2ndMinT_ID pak2ndMinV pak2ndMinV_ID pakMinT pakMinT_ID pakMinV pakMinV_ID soc   
-1136.26 20         23            3.87       20            20      24         3.87    24         87.4  
yr_mo
23-08
Check program maxWatts does it make sense  -999
select * from s30.battery where time > now() - 2m
name: battery
time                           Ahr2empty   avgCurrent         avgVoltage        avgWatts           interval           kWh_charge       kWh_discharge    local_dt            maxCurrent maxWatts minCurrent minWatts pak2ndMinT pak2ndMinT_ID pak2ndMinV pak2ndMinV_ID pakMinT pakMinT_ID pakMinV pakMinV_ID soc   yr_mo
----                           ---------   ----------         ----------        --------           --------           ----------       -------------    --------            ---------- -------- ---------- -------- ---------- ------------- ---------- ------------- ------- ---------- ------- ---------- ---   -----
2023-09-15T18:47:04.261383812Z 593.664     5.777058823529412  56.9050980392157  328.77588235294115 30.201435327529907 12.843392578125  7.03289697265625 2023-09-15T14:47:04 6.2        352.84   5.5        313.18   17         28            4.045      27            17      23         4.04    27         98.77 23-09
2023-09-15T18:47:25.665205813Z 593.696     5.469428571428572  56.90171428571432 311.2671428571428  21.112677097320557 12.8452314453125 7.03289697265625 2023-09-15T14:47:25 5.74       326.52   5.21       296.72   17         28            4.045      27            17      28         4.045   27         98.78 23-09
2023-09-15T18:47:56.102055963Z 593.7490625 6.251764705882352  56.90901960784315 355.8513725490195  30.227882146835327 12.8482900390625 7.03289697265625 2023-09-15T14:47:56 7.38       420.21   5.36       305.08   17         28            4.05       23            17      23         4.045   27         98.79 23-09
2023-09-15T18:48:17.334720279Z 593.799625  8.764242424242425  56.93757575757577 499.0887878787878  20.74081254005432  12.851064453125  7.03289697265625 2023-09-15T14:48:17 10.8       615.02   7.33       417.41   17         28            4.045      27            17      28         4.045   27         98.8  23-09
2023-09-15T18:48:47.995700951Z 593.92475   14.634200000000007 57.0112           834.3860000000001  30.30963635444641  12.858171875     7.03289697265625 2023-09-15T14:48:47 16.31      930.01   10.94      623.1    17         28            4.05       28            17      28         4.045   27         98.82 23-09

compare query now to Batrium display  # looks ok
move PacketListner230915.py to Production under solarPi4 as PacketListner.py
change service & restart # done appears to be working see above
  sudo cp PacketListner.service /lib/systemd/system/
  sudo systemctl stop PacketListner.service
	sudo systemctl daemon-reload
	sudo systemctl enable PacketListner.service
  sudo systemctl start PacketListner.service

Sept 16, 2023
influx -precision 'rfc3339' -database 'battery_db' 

change PacketListner > s30.s30_battery 
copy battery measures to d1.ts30_battery; d1.tm5_battery; d1.tm30_battery; d1.td1_battery
select * into d1.ts30_battery from s30.battery
select * into d1.tm5_battery from m5.battery
select * into d1.tm30_battery from m30.battery
select * into d1.td1_battery from d1.battery
sudo systectl stop PacketListner
sudo systectl start PacketListner
sudo systectl status PacketListner

change cq_battery_m5 > m5.m5_battery 
select * from s30.s30_battery
select * into s30.s30_battery from d1.ts30_battery where time < ''
change cq_battery_m30 > m30.m30_battery
change cq_battery_d1 > d1.d1_battery  

	tm30_battery starts 2023-06-24T00:00:00Z
  td1_battery starts 2023-05-14T00:00:00Z 
  td1_battery 92450 records
  m30_battery record times look ok
  around 8/9 something else starts putting in records 8/18 lots of records 30 sec appart contains Ahr2empty    avgCurrent         avgVoltage     


sept 17, 2023
influx -precision 'rfc3339' -database 'battery_db' 
  next check on yr_mo_1 in ..._battery measures
    still in m30_battery & d1_battery only when query crosses between copied tags and cq written tags
try # journalctl -fu influxdb   # can't understand output

influx -precision 'rfc3339' -database 'battery_db' -execute 'select * from s30.s30_battery' -format csv > s30_battery.csv

get recent samples of each battery measure and check:
select * from s30.s30_battery where time > now() - 1m
time                           Ahr2empty avgCurrent          avgVoltage        avgWatts            interval           kWh_charge      kWh_discharge    local_dt            maxCurrent maxWatts minCurrent minWatts pak2ndMinT pak2ndMinT_ID pak2ndMinV pak2ndMinV_ID pakMinT pakMinT_ID pakMinV pakMinV_ID soc    yr_mo
2023-09-17T20:06:25.120207488Z 609.21925 -3.3344230769230765 56.96749999999999 -189.95269230769233 30.357096672058105 11.19965625     5.0420126953125  2023-09-17T16:06:25 -2.39      -136.29  -5.05      -287.68  20         27            4.05       27            20      27         4.05    27         101.36 23-09

select * from m5.m5_battery where time > now() - 10m
time                 avgWatts           interval          kWh_charge       kWh_discharge   local_dt            maxChargeCurrent maxChargeWatts maxDischargeCurrent maxDischargeWatts min_Ahr2empty min_Voltage        min_soc pakMinT pakMinV yr_mo
2023-09-17T20:00:00Z 215.55740173888964 284.5367429256439 11.1987744140625 5.0374169921875 2023-09-17T16:00:22 9.29             530.78         -4.28               -243.78           609.0190625   57.047777777777746 101.33  20      4.045   23-09

select * from m30.m30_battery where time > now() - 1h
time                 avgWatts          interval            kWh_charge   kWh_discharge local_dt            maxChargeCurrent maxChargeWatts maxDischargeCurrent maxDischargeWatts min_Ahr2empty min_Voltage       min_soc pakMinT pakMinV yr_mo
2023-09-17T19:30:00Z 96.90555033044546 0.49698217226399316 11.181171875 5.0372421875  2023-09-17T15:30:07 14.09            805.18         -10.33              -587.86           608.06175     56.92838709677422 101.17  20      4.045   23-09

select * from d1.d1_battery where time > now() - 2d
time                 avgWatts            interval           kWh_charge       kWh_discharge   local_dt            maxChargeCurrent maxChargeWatts maxDischargeCurrent maxDischargeWatts min_Ahr2empty min_Voltage       min_soc pakMinT pakMinV yr_mo yr_mo_1
2023-09-16T04:00:00Z -501.04112760344293 10.871109883189202 13.3294287109375 12.33090234375  2023-09-16T00:00:12 27.12            1410.96        -95.91              -4916.23          394.72640625  51.29085106382978 65.67   14      3.655   23-09 
2023-09-16T04:00:00Z 423.65392501889477  12.507826880613964 9.7444990234375  9.7164287109375 2023-09-16T11:20:24 96.27            5449.88        -67.27              -3508.28          408.28209375  52.05411764705883 67.93   14      3.7           23-09

next work on inverter tables
working on yr_mo_1  Explained: https://docs.influxdata.com/influxdb/v1/troubleshooting/frequently-asked-questions/#tag-and-field-key-with-the-same-name
Solution: To query a tag or field key appended with _1, you must drop the appended _1 and include the syntax ::tag or ::field.
SELECT "leaves"::tag, "leaves"::field FROM <database_name>.<retention_policy>."grape"
Remove a duplicate key: SELECT "field_key","field_key2","field_key3"
INTO <temporary_measurement> FROM <original_measurement>
WHERE <date range> GROUP BY "tag_key","tag_key2"
verify select * from  <temporary_measurement>
drop original measure; SELECT * INTO "original_measurement" FROM "temporary_measurement" GROUP BY *
Lesson: when select into use group by * to preserve tags

show measurements
DELETE FROM "h2o_quality" WHERE "randtag" = '3'
select count(local_dt) from m30.m30_battery where "yr_mo_1" = ''
TAG SET = The collection of tag keys and tag values on a point.
SERIES = A logical grouping of data defined by shared measurement, tag set, and field key.  Each shard contains a specific set of series. 
SHOW SERIES [ON <database_name>] [FROM_clause] [WHERE <tag_key> <operator> [ '<tag_value>' | <regular_expression>]] [LIMIT_clause] [OFFSET_clause]  # only for default retention policy
SHOW TAG KEYS [ON <database_name>] [FROM_clause] [WHERE <tag_key> <operator> ['<tag_value>' | <regular_expression>]] [LIMIT_clause] [OFFSET_clause]
SHOW TAG VALUES [ON <database_name>][FROM_clause] WITH KEY [ [<operator> "<tag_key>" | <regular_expression>] | [IN ("<tag_key1>","<tag_key2")]] [WHERE <tag_key> <operator> ['<tag_value>' | <regular_expression>]] [LIMIT_clause] [OFFSET_clause]
SHOW FIELD KEYS [ON <database_name>] [FROM <measurement_name>]
DROP SERIES FROM <measurement_name[,measurement_name]> WHERE <tag_key>='<tag_value>'
DROP removes series DELETE removes points from series

Notes for next visit: 
1.  query all RP.Measures for duplicate keys  RPs[s5, s30, m1, m5, m30, d1, d30]
   select * from m30.m30_battery limit 2
   select * into d1.t3m30_battery from m30.m30_battery group by "yr_mo"
   select * from d1.t3s30_battery limit 2


Sep 26, 2023
influx -precision 'rfc3339' -database 'battery_db' 
Measures: m1_temp; m5_temp;  m5.m5_battery, m30_temp; d1_temp, 
      s30_battery; m5_battery; m30_battery; d1_battery
Has double yr_mo key: s30.s30_battery, m5.m5_battery; m30.m30_battery, d1.d1_battery
    m1.m1_temp; m5.m5_temp; d1.d1_temp 
measures to drop: m30_test; t_d1_temp; td1_battery; temp; tm30_battery; tm5_battery; ts30_battery

Points copied with: select * into d1.ts30_battery from s30.battery
Lose their tags 
Lesson: when select into use group by * to preserve tags
YOU MUST select * into d1.ts30_battery from s30.battery group by *

It may not be worthwhile fixing the tags in the past points:
select * from d1.d1_battery order by time desc limit 5
time                 avgWatts            interval           kWh_charge       kWh_discharge    local_dt            maxChargeCurrent maxChargeWatts maxDischargeCurrent maxDischargeWatts min_Ahr2empty min_Voltage       min_m30Voltage min_soc pakMinT pakMinV yr_mo yr_mo_1
----                 --------            --------           ----------       -------------    --------            ---------------- -------------- ------------------- ----------------- ------------- -----------       -------------- ------- ------- ------- ----- -------
2023-09-25T04:00:00Z -429.34133546480416 23.717468697097562 16.739359375     17.32475390625   2023-09-25T00:00:18 124.49           6418.09        -117.61             -5674.95          128.366109375 47.18750000000003                21.35   11      3.31          23-09

select * from m30.m30_battery order by time desc limit 1
name: m30_battery
time                 avgWatts           interval            kWh_charge kWh_discharge     local_dt            maxChargeCurrent maxChargeWatts maxDischargeCurrent maxDischargeWatts min_Ahr2empty min_Voltage        min_soc pakMinT pakMinV yr_mo yr_mo_1
----                 --------           --------            ---------- -------------     --------            ---------------- -------------- ------------------- ----------------- ------------- -----------        ------- ------- ------- ----- -------
2023-09-26T18:30:00Z 169.72538197299806 0.48982475366857314 28.0911875 2.416378173828125 2023-09-26T14:30:14 7.1              405.01         -0.33               -18.84            606.77925     56.948999999999984 100.96  20      4.04          23-09

select * from m5.m5_battery order by time desc limit 1
name: m5_battery
time                 avgWatts           interval          kWh_charge      kWh_discharge   local_dt            maxChargeCurrent maxChargeWatts maxDischargeCurrent maxDischargeWatts min_Ahr2empty min_Voltage       min_soc pakMinT pakMinV yr_mo yr_mo_1
----                 --------           --------          ----------      -------------   --------            ---------------- -------------- ------------------- ----------------- ------------- -----------       ------- ------- ------- ----- -------
2023-09-26T19:10:00Z 241.13056282839477 286.7119586467743 28.144396484375 2.4166318359375 2023-09-26T15:10:30 6.19             352.84         2.91                165.88            608.813125    57.00274509803922 101.3   20      4.04          23-09

select * from s30.s30_battery order by time desc limit 1
name: s30_battery
time                          Ahr2empty   avgCurrent         avgVoltage        avgWatts           interval           kWh_charge     kWh_discharge   local_dt            maxCurrent maxWatts minCurrent minWatts pak2ndMinT pak2ndMinT_ID pak2ndMinV pak2ndMinV_ID pakMinT pakMinT_ID pakMinV pakMinV_ID soc    yr_mo yr_mo_1
----                          ---------   ----------         ----------        --------           --------           ----------     -------------   --------            ---------- -------- ---------- -------- ---------- ------------- ---------- ------------- ------- ---------- ------- ---------- ---    ----- -------
2023-09-26T19:16:33.10485634Z 609.2426875 3.9956862745098034 57.01764705882354 227.83529411764707 30.159207582473755 28.15115234375 2.4166318359375 2023-09-26T15:16:33 5.02       286.51   3.18       181.32   24         23            4.06       23            20      27         4.04    27         101.37       23-09

select * from m1.m1_temp order by time desc limit 1
name: m1_temp
time                           heat_interval heater heater_kWhr heater_watts interval  local_dt            temp_closet temp_outdoor temp_shed yr_mo yr_mo_1
----                           ------------- ------ ----------- ------------ --------  --------            ----------- ------------ --------- ----- -------
2023-09-26T19:17:14.588349897Z 0             0      196.754     0            60.217204 2023-09-26T15:17:14 24.9375     22.75        24.0625         23-09

select * from m5.m5_temp order by time desc limit 1
name: m5_temp
time                 avg_temp_closet avg_temp_outdoor avg_temp_shed heater heater_first_kWhr heater_last_kWhr heater_on heater_watts interval   local_dt            max_temp_closet min_temp_closet yr_mo yr_mo_1
----                 --------------- ---------------- ------------- ------ ----------------- ---------------- --------- ------------ --------   --------            --------------- --------------- ----- -------
2023-09-26T19:10:00Z 24.875          22.6125          24.125        0      196.754           196.754          0         0            300.689998 2023-09-26T15:10:13 24.875          24.875                23-09

select * from m30.m30_temp order by time desc limit 1
name: m30_temp
time                 avg_temp_closet avg_temp_outdoor   avg_temp_shed      heater heater_kWhr heater_on heater_watts interval    local_dt            max_temp_closet min_temp_closet yr_mo
----                 --------------- ----------------   -------------      ------ ----------- --------- ------------ --------    --------            --------------- --------------- -----
2023-09-26T18:30:00Z 24.85625        28.195833333333336 24.222916666666666 0      0           0         0            1805.375434 2023-09-26T14:30:06 24.875          24.8125         23-09

select * from d1.d1_temp order by time desc limit 1
name: d1_temp
time                 avg_temp_closet    avg_temp_outdoor   avg_temp_shed      heater_kWhr heater_on         interval           local_dt            max_temp_closet min_temp_closet pct_heater_on       yr_mo yr_mo_1
----                 ---------------    ----------------   -------------      ----------- ---------         --------           --------            --------------- --------------- -------------       ----- -------
2023-09-25T04:00:00Z 17.295713975694444 16.705566406250004 19.735807291666664 0           5.518738512500001 23.992775979942774 2023-09-25T00:00:56 19.5            14.625          0.23001667323170513       23-09

Sep 27, 2023
influx -precision 'rfc3339' -database 'battery_db'
fix inverter influx measures 
s5.inverter -> s5.s5_inverter
s30.inverter -> s30.s30_inverter
m5.inverter -> m5.m5_inverter
m30.inverter -> m30.m30_inverter
d1.inverter -> d1.d1_inverter
& fix CQs
select * into d1.td1_inverter from d1.inverter group by *
select count(local_dt) from d1.td1_inverter group by *
select * into d1.d1_inverter from d1.td1_inverter group by *
drop continuous query cq_inv_d1 on battery_db
CREATE CONTINUOUS QUERY cq_inv_d1 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.d1.d1_inverter FROM battery_db.m30.m30_inverter GROUP BY time(1d, 4h), * END

select * into d1.tm30_inverter from m30.inverter group by *
select count(local_dt) from d1.tm30_inverter group by *
select * into m30.m30_inverter from d1.tm30_inverter group by *
drop continuous query cq_inv_m30 on battery_db
CREATE CONTINUOUS QUERY cq_inv_m30 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.m30.m30_inverter FROM battery_db.m5.m5_inverter GROUP BY time(30m), * END

select * into d1.tm5_inverter from m5.inverter group by *
select count(local_dt) from d1.tm5_inverter group by *
select * into m5.m5_inverter from d1.tm5_inverter group by *
drop continuous query cq_inv_m5 on battery_db
CREATE CONTINUOUS QUERY cq_inv_m5 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.m5.m5_inverter FROM battery_db.s30.s30_inverter GROUP BY time(5m), * END

on Holt-Pi3-inv
change program packetListner output database and restart
filezilla service & .py to Holt-Pi3-inv ~/Programs/
sudo systemctl status MagnumMonitor.service
sudo systemctl stop MagnumMonitor.service
sudo cp MagnumMonitor.service /lib/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable MagnumMonitor.service
sudo systemctl status MagnumMonitor.service
On solarPi4
drop continuous query cq_inv_s30 on battery_db
select * into d1.ts30_inverter from s30.inverter group by *
select count(local_dt) from d1.ts30_inverter group by *
select * into s30.s30_inverter from d1.ts30_inverter group by *

CREATE CONTINUOUS QUERY cq_inv_s30 ON battery_db BEGIN SELECT sum(interval) AS interval, last(local_dt) AS local_dt, mean(avgWattsOut) AS avgWattsOut, max(maxWattsOut) AS maxWattsOut, mean(avgGenWattsIn) AS avgGenWattsIn, sum(genRunTime) AS genRunTime, last(genStatus) AS genStatus, last(genStartMode) AS genStartMode, last(inverterStatus) AS inverterStatus, last(inverterFault) AS inverterFault INTO battery_db.s30.s30_inverter FROM battery_db.s5.s5_inverter GROUP BY time(30s), * END

select * into d1.ts5_inverter from s5.inverter group by *
select count(local_dt) from d1.ts5_inverter group by *
select * into s5.s5_inverter from d1.ts5_inverter group by *

sudo systemctl start MagnumMonitor.service	
sudo systemctl status MagnumMonitor.service

drop measurement inverter
show measurements  # should be no "inverter"
