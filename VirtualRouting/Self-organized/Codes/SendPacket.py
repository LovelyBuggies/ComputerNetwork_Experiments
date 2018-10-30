# -*- coding:utf-8 -*-
# 通过给节点发送一个包含指令（send）的数据包来操控节点发送数据

import socket
from DataStructure import *


src = input("Input the source of this packet(eg: 'A', 'B'..., 'E'): ");
dest =  input("Input the destination of this packet(eg: 'A', 'B'..., 'E'): ");

srcAddr = name_To_address(src);

commandSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM);  #  采用UDP
# commandSocket.bind(('127.0.0.1', 29999));

payload = dest;
sendpkt = Packet(Address('127.0.0.1', 24, 29999), srcAddr, payload, 2);
commandSocket.sendto(sendpkt.serialize().encode(), (srcAddr.ip, srcAddr.port));
