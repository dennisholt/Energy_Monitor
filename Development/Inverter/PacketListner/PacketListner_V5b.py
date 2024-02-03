#!/usr/bin python3
'''
Aug 4, 2022  by: Dennis Holt
UDP listener and parser for datalogging battery condition
especially near bottom charge
resources:
   https://kirands-python-networkinglinuxscripts.blogspot.com/2017/02/ethernet-header-ip-tcp-udp-packet.html
   run as service: https://learn.sparkfun.com/tutorials/how-to-run-a-raspberry-pi-program-on-startup/all
Batrium UDP destination port: 18542
Message type bytes 1-2
    415A Individual cell monitor Basic Status (subset for up to 16)
    5732 System iscovery Info (contains SOC, and shunt data)
Goal: monitor Batrium UDP and log datetime, message type, length to file = 'BatriumMessages.csv'
    Time, DateTime, Port, Message Type, Length
    write to 3 .csv files
Aug 15, 2022 Trying to get it to run as service. Made file paths fully specified; Commented out all print()
   Porblem with status being written out is status from previous time However time is current time.
Aug 24, 2022 make one record at each collection time; start collecting cum Ahr from message 3F34
'''
import socket
import struct
import textwrap
import time
import array

def main():
   
   f_status = open('/home/pi/Packet_Listner/Battery_Status_B.csv', 'a')
   
   # f_status.write('Time, DateTime, n01_v, n02_v, n03_v, n04_v, n05_v, ' +
   # 'n06_v, n07_v, n08_v, n09_v, n10_v, n11_v, n12_v, n13_v, n14_v, n15_v, ' +
   # 'n16_v, n17_v, n18_v, n19_v, n20_v, n21_v, n22_v, n23_v, n24_v, ' +
   # 'n25_v, n26_v, n27_v, n28_v, SOC, DC_V, DC_A, Ahr\n')

   t_start = time.time()
   need_soc = True
   need_nodes1_16 = True
   need_nodes17_28 = True 
   
   while True:
      # for idx in range(0, 30):
      t = time.time()
      if t >= t_start:
         conn = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(3))
         raw_data, addr = conn.recvfrom(1024) # get a packet
         dest_mac, src_mac, eth_proto, data = ethernet_frame(raw_data)
         conn.close()
         # 8 for IPv4 (we are only interested in IPv4 UDP packets)
         if eth_proto == 8 and len(data) >= 20:
         #   print('data length= ', len(data))
            version, header_length, ttl, proto, src, target, data = ipv4_packet(data)
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
               if mesType == 0x415A and (need_nodes1_16 or need_nodes17_28):
#                  print('0x415A message detected')
                  rx_node, records, first_id, last_id = struct.unpack('! 8x B B B B', data[:12])
         #         print('Records= {} first_id {} last_id {} Time {} DT {}'.format(records, first_id, last_id, t, dt))
                  out = ''
                  for i in range(0, records):
                     start = i * 11 + 12
                     node_id, min_v, max_v = struct.unpack('< B x H H', data[start:start+6])
                     min_v = min_v / 1000
                     max_v = max_v / 1000
                     node_v = round((min_v + max_v) / 2, 3)
         #             print('node {} voltage= {}'.format(node_id, node_v))
                     out = out + str(node_v)+ ', '
                  if first_id == 1 and need_nodes1_16:
                     out_a = out
                     need_nodes1_16 = False
                  elif first_id == 17 and need_nodes17_28:
                     out_b = out
                     need_nodes17_28 = False

#               elif mesType == 0x5732 and need_soc:
#                  print('0x5732 message detected', ' Time= ', dt, ' stat= ', str(need_status), ' 1-16= ', str(need_nodes1_16), ' 17-28= ', str(need_nodes17_28))
#                  soc_raw, shunt_v, shunt_c = struct.unpack('< 41x B H f', data[:48])
#                  soc = soc_raw * 0.5 - 5
#                  shunt_v = shunt_v / 100
#                  shunt_c = round(shunt_c / 1000, 2)
#                  out_c = str(soc) +', ' + str(shunt_v) + ', ' + str(shunt_c) + ', '
#                  print('SOC= {} Battery Voltage= {} Battery Current= {}'.format(soc, shunt_v, shunt_c ))
#                  print(out)
#                  f_status.write(out + '\n')
#                  need_status = False
                  
               elif mesType == 0x3F34 and need_soc:
                  shunt_v, shunt_c, soc, cap2empty = struct.unpack('< 12x H f 4x H 6x f', data[:34])
                  shunt_v = shunt_v / 100
                  shunt_c = round(shunt_c / 1000, 2)
                  soc = soc / 100  
                  cap2empty = cap2empty / 1000 
                  out_c = str(soc) +', ' + str(shunt_v) + ', ' + str(shunt_c) + ', ' + str(cap2empty)
 #                 print('SOC= {} Battery Voltage= {} Battery Current= {} Capacity= {}'.format(soc, shunt_v, shunt_c, cap2empty ))
         #          print(out)
                  need_soc = False
                  
# if we have everything time stamp, output and reset
               if not (need_soc or need_nodes1_16 or need_nodes17_28):
                  now = time.time()
                  dt = time.strftime('%m/%d %H:%M', time.localtime(now))
                  out = str(now) +', '+ dt +', ' + out_a + out_b + out_c  
                  f_status.write(out + '\n')
                  f_status.flush() 
                  if soc < 30:
                     time_step = 30       # if soc < 30% log every 30 sec
                  else: time_step = 900   # if soc >= 30% log every 15 min (900 sec)
                  t_start = now + time_step                 
                  out_a = out_b = out_c = out_d  = ''           
                  need_soc = True
                  need_nodes1_16 = True
                  need_nodes17_28 = True
               continue 
            else: continue    

   f_status.close() 


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
   (src_port, dest_port, sequence, acknowledgement, offset_reserved_flags) = struct.unpack('! H H L L H', offset = (offset_reserved_flags >> 12) * 4)
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

main()
