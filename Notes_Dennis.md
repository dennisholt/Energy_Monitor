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
    