# Overview

```mermaid
---
title: Energy Flow
---
flowchart TD
    sps["☀️\nSolar panels\n(shed)"]
    spb["☀️\nSolar panels\n(barn)"]
    cc1("Charge controller")
    cc2("Charge controller")
    sps ---> cc1
    spb ---> cc2
    cc1 & cc2 -- DC 48v ---> mi(["⚡️Magnum inverter"])
    batt[(Battery)] <-- DC 48v ---> mi
    gen[Generator] -- AC In ---> mi
    mi == AC Out ===> house["🏠 House"]
```

```mermaid
---
title: Monitoring & Control
---
flowchart BT
    subgraph "🏠"
        gd(Grafana Dashboard)
        subgraph rp4 ["RPi 4"]
        idb[(InfluxDB)]
        btm("Batrium Packet Monitoring")
        end
        rp4 -- HTTP --> gd
    end
    
subgraph bd [Shed]
        pi0[/RPi Zero 2W/]
        pi0 -- WiFi ---> idb
        son["Sonoff 531\npower monitoring plug"]
            son <-- MQTT --> pi0
        mi[Magnum inverter]
    gc[Generator controller]
    mi & gc -- RS485 --> dl
    bbm[Batrium battery monitor] -- UDP WiFi --> btm    
    subgraph "RPi 3"
        dl(Datalogger) -- "WiFi" --> idb
    end
end  
    
    subgraph bc [Battery closet]
        blb["Heating bulbs (2 x 100w)"] --> son 
        btt["Temp sensor"] -- I2C --> pi0
        bat["Battery Bank"] --> bbm
    end
```


# LOG BOOK
- Aug 2011 
    Build house; Install Lead Acid batteries (16 Rolls S-530 6v 400Ahr)
    Magnum Inverter Model MS4448PAE (48v 4400w 36.7A output)
    Outback Charge Coltroller Flexmax80
    Solar Panels: 6 on shed; 12 on posts (installed Dec 2011)
    Generator: Perkins 403D-11 engine; 
- Jan 2012 Wiring House
- Feb 2012 Move in

- Nov - Dec 2019
    New Inverter: two Magnum MS4448PAE and new conection panel
    Solar Panels on Barn 16 panels in 4 strings of 4
    EP_Ever Charge Controller 10415AN Max 100A, 5000W, in 138V

- Jul 2020 
    Installed Lithium Ion Battery Bank
        28 packs of 120 cells (LGABB411865) in parallel
        (Spec: 2.6 Ahr; <0.070 ohms)
        Packs in two series strings of 14; Capacity ~ 600Ahr
    Batrium battery management system (Watchmon 4)
- Jul 31, 2020 
    Connected new battery; 
    ** Magnum inverter failed SPARKS & SMOKE  **
    Went to one inverter; waiting for replacement.
- Aug 11,2020
    Connected replacement inverter.

- Sep 13, 2020
    Found Outback battery negative lug had been seriously over heating. 
    Took out of service and replaced lug & nearby capacitor.
- Sep 24, 2020  Reinstalled Outback.

- Oct 11, 2020 Battery closet door complete 

- Oct 18, 2020 Added 60w bulb for heat on 24hr/day
- Oct 20, 2020 Bulb on timer 2.5 hr/day
- Oct 25? 2020 Bulb on 11pm to 7am 8hr/day
- Nov 14, 2020 Changed master inverter now on right to improve clocks keeping time
- Nov 16, 2020 SmartPlug thermostat & 100w bulb installed in battery closet
- Nov 27, 2020 Bat #28 gets very low when SOC<10%; changed Gen Start from 42.8 to 43.6v
- Dec 15, 2020 Added second drop light w/ 60w bulb to closet
- Dec 20, 2020 Outback failed output braker tripped keeps going to snooze mode.
- Dec 29, 2020 Changed closet temp control +3 degC; on @ 18C, off @ 20C
- Dec 31, 2020 Installed 2nd EPever charge controler in place of outback
- Jan 26, 2021 Gen Start voltage from 43.6 to 44.4v
- Feb 05, 2021 Port on RTR failed power out, gen ctrl goes to off with power fail
- Mar 02, 2021 2nd light bulb out; plug to other drop light bent prongs; replaced w/ 100w now draws 183w
- May 08, 2021 Wiring connected to Barn
- May 22, 2021 Wiring connected to Pond
- Jun 08, 2021 Unpluged Lights
- Sep 27, 2021 Closed Battery Closet Door
- Apr 06, 2022 Updated Batrium app "Tool Kit" from 2.0.12.0 to 2.17.15.0
             Updated Batrium firmware to 4.17.78
             changed cell type to custom; Bypass voltage: 4.05
- May 15, 2022 Door off battery closet
- May 28, 2022 Bat #29 = 3.661v; Bat #30 = 3.624v
- Jul 15, 2022 Changed low battery cutout voltage from 42.0v to 42.6v
- Sep 12, 2022 Added boost cells to packs: 10, 11, 12, 13, 25, 26, 27, 28 
            (damaged pack #2 arc 2 killed 2 cells)
- Sep 16, 2022 Bat #29 = 3.7v
- Sep 17, 2022 Closed Battery Closet Door
Nov 17, 2022 Changed battery heater to: on: 15.5C; off: 17.5C
- May 13, 2023 Opened battery closet door
- Sep     2023 Added cell to #27 boost pack
- Sep 25, 2023 Fix one cell disconnected Pack #27 (small wire to + terminal)
             Closed battery closet door; Plugged in heater lights to S31 Smart Plug
- Nov 02, 2023 Battery pack #27 getting down to ~2.8v when SOC ~18.7% DCV ~ 45.1
- Nov 21, 2023 Changed Generator start voltage from 44.4 to 45.6
- Nov 25, 2023 Changed #27 boost battery to 8 cells; burned out 100W heater lamp replaced.
- Dec 09, 2023 Changed trigger voltage for logging lowPacks to shunt v < 47volts
- Dec 10, 2023 Changed closet temp setpoint on = 16.5; off = 18.5 
                Worked on data logger for basement bedroom temp and Ra concentration
- Dec 16, 2023 Analized lowPack Generator ran 12/10&11 #27 is now strongest; 
            #24 weakest #22 next could use one more cell. Could lower gen start back to 44.4v
- Dec 19, 2023 Gen ran 12/18 @19:20-23:50 SOC 20.22; Gen out 4000W; battery in 2780W;
            pack #25&24 weakest at 3.17v
            pak_25 3.17; 24 3.175; 20 3.185; 21 3.19; 14 3.195; 07 3.2; 13 3.2; 22 3.2;
            11 3.205; 26 3.21; 12 3.215; 19 3.22; 28 3.22; 02 3.23; 03 3.23; 08 3.23;
            23 3.235; 10 3.24; 04 3.25; 18 3.25; 06 3.26; 09 3.275; 15 3.28; 16 3.28;
            01 3.285; 05 3.305; 17 3.315; 27 3.37;
        #25 3.29v 21.68soc 130.34Ahr 46.55v; @gen on 3.17v 20.22soc 121.55Ahr 45.22v 
        delta 1.33v aprox 0.12v drop for #25; could lower gen on by ~1 volt 
- Dec 21, 2023 Gen start to 43.6 volts
- Dec 24, 2023 Gen on at 42.93 ran 12/23 @19:42  Min pak#22 2.955v next 24 soc:19.46 #27 strongest
- Jan 15, 2024 Changed order of Influx CQ for inverter to resolve interval sum ~74% of span.
- jan 19, 2024 Inverter CQs to base data, first(local_dt)
- Jan 29, 2024 @ 12:50 changed closet temp setpoint: on from 16.5 -> 17.5; off from 18.5 -> 19.5
- Jan 30, 2024 add inverter watts out when generator is running as genInvWattsOut to MagnumMonitor.py 
            added m5_energy to influx from CQs on inverter, battery, temp 
            [time; Ahr2empty; avgGenWattsIn; avgWattsOut; avg_temp_closet; avg_temp_outdoor; avg_temp_shed; batWatts; genInvWattsOut; genRunTime; heater_first_kWhr; heater_last_kWhr; heater_on; kWh_charge; kWh_discharge; maxWattsOut; max_temp_closet; min_soc; min_temp_closet; pakMinV; pakMinV_ID; soc; voltage; yr_mo]
- Feb 01, 2024 Added exponential weighted closet temp to DietPi and CQs.


# SETTINGS
Oct 2020  
MAGNUM  2023-08-09 12:54:30

frame history
- inv_status	64 = 0x40  = INVERTMODE
- inv_fault	0 = No Fault
- inv_DC_v	562
- inv_DC_a	29
- AC_out_v	122
- AC_in_v	0
- inv_LED	1  = Inverter LED on Remote 'ON'
- charger_LED	0
- inv_rev	61  = 6.1
- bat_temp	25
- xformer_temp	57
- FET_temp	42
- inv_model	115 = MS4448PAE
- stack_mode	1 = Parallel stack - master
- AC_in_a	0
- AC_out_a	10
- AC_hz	600
- inv_toggle	0  
- charger_toggle	0
- eq_toggle	0
- search_w	5   = 5w
- bat_Ah	600     = 600 Ah
- bat_type	144  = absorption at 14.4 volts
- absorp_v	144
- Charge_a_pct	40   = 40%
- shore_a	30
- rmt_rev	32      = 3.2
- Parallel_pct	0
- force_charge	0
- gen_auto_start	1
- low_bat_cut_out	426  = 42.6 v
- AC_in_cut_out_v	155  = 80 v
- float_charge_v	560  
- eq_charge_v	0
absorb_hrs	10
timeOfDay_hour	12
timeOfDay_minute	55
gen_run_hrs1	20
gen_start_temp	0
gen_start_DC_v	444  = 44.4 v
quite_time	0
gen_start_time	96
gen_stop_time	0
gen_stop_DC_v	520   = 52.0 v
gen_Vstart_delay	120
gen_Vstop_delay	120
gen_max_on_hrs	60
gen_SOC_start	0
gen_SOC_stop	90
gen_start_DC_a	0
gen_Astart_delay	120
gen_stop_DC_a	4
gen_Astop_delay	120
quiet_time_start	96
quiet_time_end	40
gen_exercise_days	0
gen_exercise_start_time	32
gen_exercise_hrs	10
top_off_minutes	0
gen_warm_up_sec	60
gen_cool_down_sec	60
bat_eff_pct	0
resets	0
bat_size_ah	600
ags_status	2
ags_rev	52
ags_temp	252
gen_run_hrs2	0
ags_bat_v	139
ags_days_since_run	0
bmk_soc	84
bmk_DC_v	5627
bmk_DC_a	1002
bmk_min_v	4083
bmk_max_v	5863
bmk_Ah_in_out	-96
bmk_Ah_trip	65535
bmk_cum_Ah_out	101500
bmk_rev	10
bmk_fault	1
rtr_rev	32  =  3.2

    Search Watts: 5
    Low Battery Cutout: 42.6v
    AC in: AUTO
    Inverter always powered when DC connected: Yes
    Threshold to start parallel: off
    Charger >
        AC input: 30A
        Low VAC drop: 80vac
        Battery: Custom
        Absorb done time: 1.0 hr
        Max Charge Rate: 50% time 24 hr (100% 60A each inverter)
        Final Charge Stage: Multi-Stage
        Days to remain when to EQ: off
    AGS >
        Gen Run DC volts > start: 44.4 v/120 sec; stop: 52.0 v/120 sec
        Gen Run > Time: off; AC amps: off; SOC: off; Temp: off
        Max run time when auto start: 3 hr
        Gen Quiet time: off; Exercise time: off
        Gen no load > Warm up: 60 sec; cool down: 60 sec
        Gen 100% SOC: off
    BMK >
        Charge efficency: Auto
        Battery size: 600 Ahr

OUTBACK   PW  141
    Current Limit: 80A
    Absorbing: 57.6v
    Float: 57.v
    Equalize: 57.6v  time: 1 hr
    Advanced > 
        Snooz mode: <0.6A wake: 6v 5 min
        Absorb end amps: 0A
        Rebulk Voltage: 53.2v
        V bat calibration: 56.0   0.0v
        (limit) RTS Comp A: 57.6v  F: 56.0v
            wide upper: 57.6   Lower: 54
        Auto restart: mode 2
        Auto polarity: Active High

EP EVER
    Device Info > Rated Voltage: 48v; Charge Current: 100A; Disc Current: 100A
    Test Operation > Load: off
    Control Parameters > 
        Battery Type: User; Batt AH: 600; 
        Temp Comp Coeff: 0.0 mv/deg C/2v
        Rated Voltage: 48
        Overvoltage disconnect: 59.0v
        Charge Limit: 58.0v
        Overvoltage reconnect: 58.0v
        Equal Charge: 57.8v
        Boost Charge: 57.6v
        Float charge: 57.0v
        Boost Reconnect: 42.2v
        Low voltage reconnect: 42.1v
        Undervoltage reconnect: 42.1v
        Undervoltage warning: 42.0v
        Low voltage disconnect: 42.0v
        Disconnect Limit: 42.0v
        Equalization time: 0 min
        Boost time: 60 min

BATRIUM    System ID: 6804    PIN: 897652
    Serial Number: 313605440
    CellMon:
        Batt type: Custom
        Lo Cell Volt: 2.90
        Nom. Cell Volt: 3.70
        Bypass Volt: 4.06
        Hi Cell Voltage: 4.20
        Lo Cell Celcius: -5
        Hi Cell Celcius: 55
        Ignore Lo Celcius: -40
        CellMon Type: LongMon
        Bypass Current Limit: 1.72
        Bypass Temp Limit: 75 C
        Bypass Impedance: 1.7
        Bypass Extra Mode: None
        Has Satellite: Off
        First Cell ID: Grp = 1;  Range = 1
        Last Cell ID:  Grp = 28;  Range = 28
        Dif Nominal: On
        Nom Series: 14
    Shunt:  Serial Number: 268228561
        Nominal Capacity: 601. Ah
        Reverse orientation: Off
        Idle Current Threshold - Charge:  0.15 A
        Idle Current Threshold - Discharge:  0.18 A
        Re-Calibrate Low SoC:  On  -1.5 %
        Re-Calibrate Hi SoC:   On  101.5 %
        Re-Calibrate in Bypass:  On
        Empty SoC% cycle threshold: 35.0
        Full SoC% cycle threshold: 85.0


BATTERY CLOSET HEATER
    On: 15.5C; Off: 17.5C

# PROCEDURES
Battery Swap Process
    Wait till pack voltage on string close to insert pack 
    Turn off string when charge current < 30A
    Unplug 4 pin longmon connector then 2 pin daisy chain
    Unbolt and swap pack
    Reconnect longmon first 2 pin then 4 pin connectors
    Get voltage between two strings close by turning solar off & on
    Turn solar off when charge current < 30A
    When voltage between strings matches turn string back on
    Turn solar back on 

# EQUIPMENT
    Batrium Battery Monitoring System
        28 Longmon 
        Watchmon 4 V4.3 w/ firmware: 4.17.78
        Software: WatchMonToolkit 2.17.15  (runs on Windows PC)

# COMPUTERS & OS SET-UP
    Rpi-4 with 2GB ram  name:"solarPi4"
        USE: Graphana dashboard web server; 
            Influx database host; 
            Packet listner to Batrium battery monitor
        OS: Raspberry Pi Bullseye 32bit

    Rpi-3 name:"Holt-Pi3-inv"
        USE: Monitor Magnum inverter bus & Log to Influx database

    Rpi-0/W name:"DietPi"
        USE: MQTT host;
            Monitor temperature and power to heater lights
            log to Influx
            Control S31 smart plug

# SOFTWARE
    Repository: https://github.com/dennisholt/Energy_Monitor



# INFLUX

## Retention Policies
retention policies
name    duration   shardGroupDuration replicaN default Duration 
----    --------   ------------------ -------- -------   Days
autogen 0s         168h0m0s           1        false
s5      120h0m0s   24h0m0s            1        true     5
s30     336h0m0s   24h0m0s            1        false    14
m1      504h0m0s   24h0m0s            1        false    21
m5      504h0m0s   24h0m0s            1        false    21
m30     2016h0m0s  24h0m0s            1        false    84
d1      17472h0m0s 168h0m0s           1        false    728
d30     0s         168h0m0s           1        false



## Continuous Queries
Database: battery_db
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