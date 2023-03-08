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
interval, local_dt, mo_yr    Note mo_yr is a tag groupby , * groups by all tags
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
  
CREATE CONTINUOUS QUERY "cq_temp_m5" ON "battery_db" 
RESAMPLE EVERY 6h FOR 7h
BEGIN
  SELECT mean("temp_closet") AS "avg_temp_closet",
    max("temp_closet") AS "max_temp_closet",
    min("temp_closet") AS "min_temp_closet",
    mean("temp_shed") AS "avg_temp_shed",
    mean("temp_outdoor") AS "avg_temp_outdoor",
    last("heater") AS "heater",
    sum("heater" * "interval") AS "heater_on",
    last("heater_watts") AS "heater_watts",
    sum("interval" * "hearter_watts") * 0.001/3600 AS "heater_kWhr",
    sum("interval") AS "interval",
    last("local_dt") AS "local_dt",
    last("mo_yr") AS "mo_yr"
  INTO "m5"."m5_temp"
  FROM "temp"
  GROUP BY time(5m), *   note: , * groups by all tags
END

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
    last("mo_yr") AS "mo_yr"
  INTO "m30"."m30_temp"
  FROM "m5"."m5_temp"
  GROUP BY time(30m), *   note: , * groups by all tags
END

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
    last("mo_yr") AS "mo_yr"
  INTO "d1"."d1_temp"
  FROM "m30"."m30_temp"
  GROUP BY time(1d), *   note: , * groups by all tags
END

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
    last("mo_yr") AS "mo_yr"
  INTO "d30"."d30_temp"
  FROM "d1"."d1_temp"
  GROUP BY "mo_yr"
END

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