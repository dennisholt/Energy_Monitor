#!/usr/bin python3
'''
May 5, 2023 by: Dennis Holt
Test subroutine to get UDP packet
also find max UDP packet size
'''
import socket
import struct
import time

def int_socket():
    conn = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(3))
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 0)
    return conn

def main():
    conn = int_socket()
    start = time.time()
    max_packet = 0
    while time.time() < start + 10: # run for 5 minutes
        mesType, batrum_data, max_packet = get_batrum_packet(conn, max_packet)
        readTime = time.strftime("%Y-%m-%dT%H:%M:%S",time.localtime())
        print(readTime, "message type= ", hex(mesType)," Max Packet= ",  max_packet)
    conn.close()

def get_batrum_packet(conn, max_packet):
    batrum_data = None
    while batrum_data is None:
        raw_data, addr = conn.recvfrom(256) # get a packet
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
            if raw_packet_size > max_packet:
                max_packet = raw_packet_size
            return mesType, batrum_data, max_packet

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

if __name__ == "__main__":
    main()
