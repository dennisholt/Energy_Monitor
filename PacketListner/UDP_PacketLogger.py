#!/usr/bin python3
'''
March 19, 2023  log UDP packets to Influx database.
by: Dennis Holt
Purpose: to find frequency and contents of packets.

'''
import socket
import struct
# import textwrap
import time
import array
from influxdb import InfluxDBClient
import json

### Initialization ###

def influx_init():
# connect to influx database
    influx_client = InfluxDBClient(host='localhost', port=8086) # 'solarPi4'
    influx_client.switch_database('battery_db')
    return influx_client

def main():
    # set up ethernet socket 
    socket_conn = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(3))

    # connect to influx database
    influx_client = influx_init()

    # Let's find out how frequently batrium packets are transmitted.
    count = 0
    while True:  # count < 15:
        raw_data, addr = socket_conn.recvfrom(1024) # get a packet
        dest_mac, src_mac, eth_proto, data = ethernet_frame(raw_data)
            
        # 8 for IPv4 (we are only interested in IPv4 UDP packets)
        if eth_proto == 8 and len(data) >= 20:
    #         print('data length= ', len(data))
            version, header_length, ttl, proto, src, target, data = ipv4_packet(data)
    #         print('proto= ', proto)
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
            src_port, dest_port, size, data = udp_segment(data)
            if dest_port == 18542:
                mesType = struct.unpack('< x H', data[:3])[0]
                if size < 34:
                    size = 34
                mesBod = data[:size].hex(' ')
                json_body=[
                    {"measurement": "mes" + hex(mesType), 
                    "tags":{"MesType":hex(mesType)},
                    "time":time.time_ns(),
                    "fields":{"body":mesBod}
                }]
#                print(json_body)
                count = count + 1
                ret = influx_client.write_points(json_body)
        else: continue    
    socket_conn.close()
    influx_client.close()
    exit()
# end main()

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

if __name__ == "__main__":
    main()
