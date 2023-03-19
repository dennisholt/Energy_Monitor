#!/usr/bin python3
'''
March 18, 2023  Revising PacketListner_V5b.py to write batrium status stuff to Influx database.
by: Dennis Holt
UDP listener and parser for datalogging battery condition
resources:
   https://kirands-python-networkinglinuxscripts.blogspot.com/2017/02/ethernet-header-ip-tcp-udp-packet.html
   run as service: https://learn.sparkfun.com/tutorials/how-to-run-a-raspberry-pi-program-on-startup/all
Batrium UDP destination port: 18542
Batrium updates the message mapping here: https://github.com/Batrium/WatchMonUdpListener/tree/master/payload
Message type bytes 1-2
    415A Individual cell monitor Basic Status (subset for up to 16)
    5732 System is Info (contains SOC, and shunt data)

Before we get into the real logger
   Let's log the frequency these two message types occure

What we want to get:
   SOC, Ahr to empty, bat voltage, bat current, cum watts into bat
   min pack voltage, which pack
   min pack temp, which pack
   CQ cum energy into battery
      min/max watts out of bat
      min/max watts into bat
      generator run time

'''
import socket
import struct
# import textwrap
import time
import array
from influxdb import InfluxDBClient
import json

### Initialization ###
###    Globals     ###
influx_client = None
measure_interval = 60  # measure battery characteristics every x seconds

def influx_init():
# connect to influx database
    influx_client = InfluxDBClient(host='localhost', port=8086) # 'solarPi4'
    influx_client.switch_database('battery_db')
    return influx_client

def main():
   then = time.time()
   # set up ethernet socket 
   socket_conn = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(3))

   # connect to influx database
   influx_client = influx_init()

# Let's find out how frequently the two batrium packets of interest are transmitted.
   while True:
      # collect UDP packets  and calc aggregate measures
      # after measure_interval write data to influx; reset aggregates and go back to collecting
      # perhaps make measure a class 
      # how to handle time interval between UDP updates into avg etc...
      time.sleep(reading_interval)
      t = time.time()
      cycle = cycle +1
 #     if cycle > 3: 
 #        break
      if time.strftime("%Y-%m-%d", time.localtime(t)) != today:
         today, local_offset = setLocalOffset()              #  (daily)
         print("it'a a new day")

      raw_data, addr = socket_conn.recvfrom(1024) # get a packet
      dest_mac, src_mac, eth_proto, data = ethernet_frame(raw_data)
         
      # 8 for IPv4 (we are only interested in IPv4 UDP packets)
      if eth_proto == 8 and len(data) >= 20:
         print('data length= ', len(data))
         version, header_length, ttl, proto, src, target, data = ipv4_packet(data)
         print('proto= ', proto)
      else: continue
      
      # ICMP
      if proto == 1:
         icmp_type, code, checksum, data = icmp_packet(data)
#           print('\t' + 'ICMP packet ')
         
      # TCP
      elif proto == 6:
         src_port, dest_port, sequence, acknowledgement, flag_urg, flag_ack, flag_psh, flag_rst, flag_syn, flag_fin, data = tcp_segment(data)
#            print('\t' + 'TCP packet ')

      # UDP
      elif proto == 17:
         src_port, dest_port, length, data = udp_segment(data)
         if dest_port == 18542:
            mesType = batrum_packet(data)
            print("dest_port=", dest_port, " mesType=", mesType)
            if mesType == 0x3F34:
               shunt_v, shunt_c, soc, cap2empty = struct.unpack('< 12x H f 4x H 6x f', data[:34])
               shunt_v = shunt_v / 100
               shunt_c = round(shunt_c / 1000, 2)
               DC_Watts = shunt_v * shunt_c
               soc = soc / 100  
               cap2empty = cap2empty / 1000 
               out_c = str(soc) +', ' + str(shunt_v) + ', ' + str(shunt_c) + ', ' + str(cap2empty)
               print('SOC= {} Battery Voltage= {} Battery Current= {} Capacity= {}'.format(soc, shunt_v, shunt_c, cap2empty ))
               print(out_c)
#  Every time we get message type 0x3F34 extract SOC etc and output to influx
               now = time.time()
               interval = then - now
               localTime = time.localtime(now)
               readTime = time.strftime("%Y-%m-%dT%H:%M:%S",localTime)+local_offset
         #    print("readTime[1:19]=",readTime[0:19])
               json_body=[{'measurement': 'power','time':time.strftime("%Y-%m-%dT%H:%M:%S",localTime),
                  'fields':{'local_dt':readTime[0:19],
                     'interval':interval,
                     'SOC':soc,
                     'Bat_Ahr':cap2empty, 
                     'Bat_Watts_in':DC_Watts, 
                     'DC_V':shunt_v, 
                     'DC_A':shunt_c}}]
               ret = influx_client.write_points(json_body)
               then = now
      else: continue    
   socket_conn.close()
# end main()

def batrum_packet(data):
   mesType = struct.unpack('< x H', data[:3])[0]
#   DataLen = len(data)
#   out = '{:04X}'.format(mesType) +', ' + str(DataLen)
#   print(out)
   return mesType

# Unpack Ethernet frame
def ethernet_frame(raw_data):
   dest, src_mac, proto = struct.unpack('! 6s 6s H', raw_data[:14])
   dest_mac = get_mac_addr(dest)
   src_mac = get_mac_addr(src_mac)
   protocol = socket.htons(proto)
   data = raw_data[14:]
   return dest_mac, src_mac, protocol, data

# Return properly formatted MAC addresses (like 0A:CE:92:9D:63:14)
def get_mac_addr(bytes_addr):
   bytes_str = map('{:02x}'.format, bytes_addr)
   mac_addr = ':'.join(bytes_str).upper()
   return mac_addr

# Unpacks IPv4 packet
def ipv4_packet(data):
   version_header_length = data[0]
   version = version_header_length >> 4
   header_length = (version_header_length & 15) * 4
   ttl, proto, src, target = struct.unpack('! 8x B B 2x 4s 4s', data[:20])
   src_ip = ipv4(src)
   target_ip = ipv4(target)
   data = data[header_length:]
   return version, header_length, ttl, proto, src_ip, target_ip, data

# Returns properly formatted IPv4 addresses
def ipv4(addr):
   ip_addr = '.'.join(map(str, addr))
   return ip_addr

# Unpacks ICMP packet
def icmp_packet(data):
   icmp_type, code, checksum = struct.unpack('! B B H', data[:4])
   return icmp_type, code, checksum, data[4:]

# Unpacks TCP segment
def tcp_segment(data):
   (src_port, dest_port, sequence, acknowledgement, offset_reserved_flags) = struct.unpack('! H H L L H', data[:14])
   offset = (offset_reserved_flags >> 12) * 4
   flag_urg = (offset_reserved_flags & 32) >> 5
   flag_ack = (offset_reserved_flags & 16) >> 5
   flag_psh = (offset_reserved_flags &  8) >> 5
   flag_rst = (offset_reserved_flags &  4) >> 5
   flag_syn = (offset_reserved_flags &  2) >> 5
   flag_fin = (offset_reserved_flags &  1) >> 5
   return src_port, dest_port, sequence, acknowledgement, flag_urg, flag_ack, flag_psh, flag_rst, flag_syn, flag_fin, data[offset:]

# Unpacks UDP segment
def udp_segment(data):
   src_port, dest_port, size = struct.unpack('! H H H 2x', data[:8])
   data = data[8:]
   return src_port, dest_port, size, data

# Formats multi-line data
def format_multi_line(prefix, string, size = 80):
   size -= len(prefix)
   if isinstance(string, bytes):
      string = ' '.join(r'{:02x}'.format(byte) for byte in string)
      if size % 2:  # 0 = False
         size += 1
   return '\n'.join([prefix + line for line in textwrap.wrap(string, size)])

if __name__ == "__main__":
    main()
