#!/usr/bin python3
'''
May 1, 2023 by: Dennis Holt
UDP listener and parser for datalogging battery condition
msg0X415A ~ 1478ms # lowest 2 pack voltage and temp with pack ID
msg0X3F34 ~ 591ms # shunt volts current watts capacity to empty
msg0X3233 ~ 26.3sec # SOC, kWh Charge, kWh Discharge
'''
from influxdb import InfluxDBClient
import socket
import struct
import textwrap
import time
from dataclasses import dataclass

# define data classes for shunt and pack
@dataclass
class Shunt:
    count: int = 0
    time: float = 0
    sumVoltage: float = 0
    sumCurrent: float = 0
    minCurrent: float = 999.
    maxCurrent: float = -999.
    sumWatts: float = 0
    minWatts: float = 999.
    maxWatts: float = -999.
    Ahr2empty: float = 0

@dataclass
class Pack:
    VoltageMin: float = 99.9
    Voltage2ndMin: float = 99.9
    PakMinV: int = 0
    Pak2ndMinV: int = 0
    TempMin: float = 99.9
    Temp2ndMin: float = 99.9
    PakMinT: int = 0
    Pak2ndMinT: int = 0
    need_1_16: bool = True
    need_17_28: bool = True

def socket_init():
    '''Connect to packet socket'''
    conn = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(3))
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 0)
    return conn

def influx_init():
    '''connect to influx database'''
    influx_client = InfluxDBClient(host='localhost', port=8086) # 'solarPi4'
    influx_client.switch_database('battery_db')
    return influx_client

def sortSecond(elem):
    return elem[1]

def sortThird(elem):
    return elem[2]

def main():
    influx_client = influx_init()  # connect to influx database
    packet_conn = socket_init()     # connect to socket API
    start = time.time()
    node_list = []
    pack = Pack()
    shunt = Shunt()
    while time.time() < start + 50: # run for 5 minutes
        mesType, batrum_data = get_batrum_packet(packet_conn)
        if mesType == 0x415A:
            process_415A(batrum_data, node_list, pack)

        elif mesType == 0X3F34:
            process_3F34(batrum_data, shunt)

        elif mesType == 0X3233:
            process_3233(batrum_data, pack, shunt)

        else: continue

    packet_conn.close()
    influx_client.close()

def get_batrum_packet(packet_conn):
    batrum_data = None
    while batrum_data is None:
        raw_data, addr = packet_conn.recvfrom(256) # get a packet
        dest_mac, src_mac, eth_proto, data = ethernet_frame(raw_data)
        raw_packet_size = len(raw_data)

        # 8 for IPv4 (we are only interested in IPv4 UDP packets)
        if eth_proto == 8 and len(data) >= 20:
        #   print('data length= ', len(data))
            version, header_length, ttl, proto, src, target, data = ipv4_packet(data)
        else: continue

        # ICMP
        if proto == 1:
            icmp_type, code, checksum, data = icmp_packet(data)
        #   print('\t' + 'ICMP packet ')
            continue

        # TCP
        elif proto == 6:
            src_port, dest_port, sequence, acknowledgement, flag_urg, flag_ack,\
                    flag_psh, flag_rst, flag_syn, flag_fin, data = tcp_segment(data)
        #   print('\t' + 'TCP packet ')
            continue

        # UDP
        elif proto == 17:
            src_port, dest_port, length, data = udp_segment(data)
            if dest_port != 18542:
                continue
            batrum_data = data
            mesType = struct.unpack('< x H', data[:3])[0]
            return mesType, batrum_data

def process_415A(batrum_data, node_list, pack):
    '''Individual battery pack data: save lowest two voltage and temp plus pack ID'''
    rx_node, records, first_id, last_id = struct.unpack('! 8x B B B B', batrum_data[:12])
    # print('Records= {} first_id {} last_id {} Time {} DT {}'.format(records, first_id, last_id, t, dt))
    #print(pack)
    #print('first_ID= ', first_id)
    for i in range(0, records):
        st = i * 11 + 12
        node_id, min_v, max_v, min_t = struct.unpack('< B x H H B', batrum_data[st:st+7])
        min_v = min_v / 1000
        max_v = max_v / 1000
        node_t = min_t - 40
        node_v = round((min_v + max_v) / 2, 3)
        node_list.append((node_v,node_t,node_id)) 
        #print('node {} voltage= {} temp= {}'.format(node_id, node_v, node_t))
    #print(node_list)
    # out = out + str(node_v)+ ', '
    if first_id == 1:
        pack.need_1_16 = False
    elif first_id == 17:
        pack.need_17_28 = False
    #print('A check for complete node_list')
    if (not pack.need_1_16  and not pack.need_17_28): # Have new record?
        # sort in voltage order and replace saved if lower
        node_list.sort()
        #print(node_list)
        if pack.VoltageMin > node_list[0][0]:
            pack.VoltageMin = node_list[0][0]
            pack.PakMinV = node_list[0][2]
        if pack.Voltage2ndMin > node_list[1][0]:
            pack.Voltage2ndMin = node_list[1][0]
            pack.Pak2ndMinV = node_list[1][2]
        node_list.sort(key=sortSecond)
        if pack.TempMin > node_list[0][1]:
            pack.TempMin = node_list[0][1]
            pack.PakMinT = node_list[0][2]
        if pack.Temp2ndMin > node_list[1][1]:
            pack.Temp2ndMin = node_list[1][1]
            pack.Pak2ndMinT = node_list[1][2]
        node_list = []
        pack.need_1_16 = True
        pack.need_17_28 = True
        #print('pack class= ', pack)

def process_3F34(batrum_data, shunt):
    '''shunt voltage and current save for averaging'''
    # shunt_v, shunt_c, soc, cap2empty = struct.unpack('< 12x H f 4x H 6x f', data[:34])
    s_v, s_c, s_w, soc, Ahr2empty = struct.unpack('< 12x H 2f H 6x f', batrum_data[:34])
    s_c = round(s_c / 1000, 2)
    s_w = round(s_w, 2)
    shunt.count += 1
    if shunt.time == 0.0:
        shunt.time = time.time()
    shunt.sumVoltage += s_v / 100
    shunt.sumCurrent += s_c
    shunt.minCurrent = min(shunt.minCurrent, s_c)
    shunt.maxCurrent = max(shunt.maxCurrent, s_c)
    shunt.sumWatts += s_w
    shunt.minWatts = min(shunt.minWatts, s_w)
    shunt.maxWatts = max(shunt.maxWatts, s_w)
    shunt.Ahr2empty = Ahr2empty / 1000   # in Ahr
    #print('SOC= {} Battery Voltage= {} Battery Current= {} Battery W= {} Capacity= {}'.format(soc, s_v, s_c, s_w, Ahr2empty ))
    # SOC= 99.51 Battery Voltage= 56.88 Battery Current= 1.74 Battery kW= 0.09919441986083985 Capacity= 598.1108125

def process_3233(batrum_data, pack, shunt):
    '''msg0x3233 only every ~ 30 min process SOC etc and write everything to influx'''
    soc, cap2empty, kWh_charge, kWh_discharge = struct.unpack('< 32x H 3f', batrum_data[:46])
    soc = soc / 100  
    # cap2empty = cap2empty / 1000    # in watt hours
    kWh_charge = kWh_charge / 1000
    kWh_discharge = kWh_discharge / 1000
#   out_c = str(soc) +', ' + str(shunt_v) + ', ' + str(shunt_c) + ', ' + str(cap2empty)
    print('SOC= {} kWh Charge= {} kWh Discharge= {}'.format(soc, kWh_charge, kWh_discharge))
    # SOC= 99.5 Ahr to empty= 30978.724 kWh Charge= 26.960185546875 kWh Discharge= 3.383803466796875
    print(pack)
    s_interval = time.time() - shunt.time
    print('shunt interval= ', s_interval)
    print(shunt)

def ethernet_frame(raw_data):
    '''Unpack Ethernet frame'''
    dest, src_mac, proto = struct.unpack('! 6s 6s H', raw_data[:14])
    dest_mac = get_mac_addr(dest)
    src_mac = get_mac_addr(src_mac)
    protocol = socket.htons(proto)
    data = raw_data[14:]
    return dest_mac, src_mac, protocol, data

def get_mac_addr(bytes_addr):
    '''Return properly formatted MAC addresses (like 0A:CE:92:9D:63:14)'''
    bytes_str = map('{:02x}'.format, bytes_addr)
    mac_addr = ':'.join(bytes_str).upper()
    return mac_addr

def ipv4_packet(data):
    '''Unpacks IPv4 packet'''
    version_header_length = data[0]
    version = version_header_length >> 4
    header_length = (version_header_length & 15) * 4
    ttl, proto, src, target = struct.unpack('! 8x B B 2x 4s 4s', data[:20])
    src_ip = ipv4(src)
    target_ip = ipv4(target)
    data = data[header_length:]
    return version, header_length, ttl, proto, src_ip, target_ip, data

def ipv4(addr):
    '''Returns properly formatted IPv4 addresses'''
    ip_addr = '.'.join(map(str, addr))
    return ip_addr

def icmp_packet(data):
    '''Unpacks ICMP packet'''
    icmp_type, code, checksum = struct.unpack('! B B H', data[:4])
    return icmp_type, code, checksum, data[4:]

def tcp_segment(data):
    '''Unpacks TCP segment'''
    (src_port, dest_port, sequence, acknowledgement, offset_reserved_flags) = \
        struct.unpack('! H H L L H', data[:14])
    offset = (offset_reserved_flags >> 12) * 4
    flag_urg = (offset_reserved_flags & 32) >> 5
    flag_ack = (offset_reserved_flags & 16) >> 5
    flag_psh = (offset_reserved_flags &  8) >> 5
    flag_rst = (offset_reserved_flags &  4) >> 5
    flag_syn = (offset_reserved_flags &  2) >> 5
    flag_fin = (offset_reserved_flags &  1) >> 5
    return src_port, dest_port, sequence, acknowledgement, flag_urg, flag_ack,\
          flag_psh, flag_rst, flag_syn, flag_fin, data[offset:]

def udp_segment(data):
    '''Unpacks UDP segment'''
    src_port, dest_port, size = struct.unpack('! H H H 2x', data[:8])
    data = data[8:]
    return src_port, dest_port, size, data

def format_multi_line(prefix, string, size = 80):
    '''Formats multi-line data'''
    size -= len(prefix)
    if isinstance(string, bytes):
        string = ' '.join(r'{:02x}'.format(byte) for byte in string)
        if size % 2:  # 0 = False
            size += 1
    return '\n'.join([prefix + line for line in textwrap.wrap(string, size)])

if __name__ == "__main__":
    main()
