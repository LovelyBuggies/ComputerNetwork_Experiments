# -*- coding:utf-8 -*-

import json
import socket, time


class Address():
    def __init__(self, ip, mask: int, port: int):
        self.ip = ip;
        self.mask = mask;
        self.port = port;

    def __eq__(self, another):
        return self.ip == another.ip and self.mask == another.mask and self.port == another.port;


class Packet():
    def __init__(self, src: Address = None, dest: Address = None, payload=None, packetType: int = None):
        self.src = src;
        self.dest = dest;
        self.payload = payload;
        self.packetType = packetType;  # 0表示普通数据包，1表示OSPF的链路状态信息数据包,2表示该数据包是一条发送数据包的指令

    # 序列化之后，就可以把序列化后的内容写入磁盘，或者通过网络传输到别的机器上
    def serialize(self):
        return json.dumps(self, default=lambda obj: obj.__dict__);

    def deserialize(self, serialization):
        d = json.loads(serialization);
        self.src = Address(d['src']['ip'], d['src']['mask'], d['src']['port']);
        self.dest = Address(d['dest']['ip'], d['dest']['mask'], d['dest']['port']);
        self.payload = d['payload'];
        self.packetType = int(d['packetType']);


class OSPF_ForwardingTableEntry():
    def __init__(self, dest: str = None, nextHop: str = None):
        self.dest = dest;
        self.nextHop = nextHop;

    def __str__(self):
        return "dest: " + str(self.dest) + ", next-hop: " + str(self.nextHop);


class RIP_RoutingTableEntry():
    def __init__(self, dest: str = None, nextHop: str = None, hopsToDest: int = 0):
        self.dest = dest;
        self.nextHop = nextHop;
        self.hopsToDest = hopsToDest;

    def __str__(self):
        return "dest: " + str(self.dest) + ", next-hop: " + str(self.nextHop) + ", hops-to-dest: " + str(
            self.hopsToDest);


def address_To_name(addr: Address):
    for nodeName in {'D', 'B', 'C', 'A', 'E'}:  # ...................
        if addr == name_To_address(nodeName):
            return nodeName;


def name_To_address(name):
    with open('../Configuration/Nodes/' + name + '.txt', 'r') as f:
        f.readline();

        ip = f.readline().strip();  # strip()把末尾的'\n'删掉
        mask = int(f.readline().strip());
        port = int(f.readline().strip());
        return Address(ip, mask, port);


def get_node_neighbors(name):
    neighbors = {};

    with open('../Configuration/Topo/Cost.txt', 'r') as f:
        line = '';
        for i in range(ord(name) - ord('A') + 1):
            line = f.readline().strip();

        count = 0;
        for n in line.split():
            if int(n) > 0:
                neighbors[chr(65 + count)] = (name_To_address(chr(65 + count)), int(n));
            count += 1;
    return neighbors;


class Node():
    '''
    name: str  # eg: 'A', 'B'
    address: Address
    neighbors: dict  # eg: {'D': (<__main__.Address object at 0x7f3c575d7a90>, 60), 'E': (<__main__.Address object at 0x7f3c575d7ac8>, 20), 'C': (<__main__.Address object at 0x7f3c575d7a58>, 80)}
    socket: socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    '''

    def __init__(self, name):
        self.name = name;
        self.address = name_To_address(name);
        self.neighbors = get_node_neighbors(name);

        self.receiveSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM);  # 采用UDP
        self.receiveSocket.bind((self.address.ip, self.address.port));  # 用于接收数据，相当于UDP server
        self.sendSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM);  # 用于发送数据

        self.OSPF_forwardingTable = [];
        self.RIP_routingTable = [];

    def printOutputMessageHeader(self):
        print(self.name + '(' + time.strftime("%H:%M:%S", time.localtime()) + ') >>> ', end='');

    def printOSPFForwardingTable(self):
        print('   OSPF Forwarding Table of', self.name, ':');
        for i in range(len(self.OSPF_forwardingTable)):
            print(i, ' ****** ', self.OSPF_forwardingTable[i]);

    def printRIPRoutingTable(self):
        print('            RIP Table of', self.name, ':');
        for i in range(len(self.RIP_routingTable)):
            print(i, ' ****** ', self.RIP_routingTable[i]);

    def send_a_normal_packet(self, dest: Address, payload, packetType):
        sendpkt = Packet(self.address, dest, payload, packetType);
        self.forward_a_normal_packet(sendpkt);

    def forward_a_normal_packet(self, recvPkt: Packet):
        packetDest = address_To_name(recvPkt.dest);
        packetSrc = address_To_name(recvPkt.src);

        if packetDest == self.name:
            self.printOutputMessageHeader();
            print('Receive a normal packet. [', 'FROM:', packetSrc, ', CONTENT:', recvPkt.payload, ']');
        # response
        else:
            # OSPF查找自己的forwarding table
            if self.OSPF_forwardingTable:
                for i in range(len(self.OSPF_forwardingTable)):

                    if self.OSPF_forwardingTable[i].dest == packetDest:
                        nextHopAddr = name_To_address(self.OSPF_forwardingTable[i].nextHop);
                        self.sendSocket.sendto(recvPkt.serialize().encode(), (nextHopAddr.ip, nextHopAddr.port));

                        self.printOutputMessageHeader();
                        if packetSrc == self.name:
                            print('Sending a normal packet. [ TO:', packetDest, ', CONTENT:', recvPkt.payload,
                                  ', NEXT-HOP:', self.OSPF_forwardingTable[i].nextHop, ']');
                        else:
                            print('Forwarding a normal packet. [', 'FROM:', packetSrc, ', TO:', packetDest,
                                  ', NEXT-HOP:', self.OSPF_forwardingTable[i].nextHop, ']');

            # RIP
            elif self.RIP_routingTable:
                for i in range(len(self.RIP_routingTable)):

                    if self.RIP_routingTable[i].dest == packetDest:
                        nextHopAddr = name_To_address(self.RIP_routingTable[i].nextHop);
                        self.sendSocket.sendto(recvPkt.serialize().encode(), (nextHopAddr.ip, nextHopAddr.port));

                        self.printOutputMessageHeader();
                        if packetSrc == self.name:
                            print('Sending a normal packet. [ TO:', packetDest, ', CONTENT:', recvPkt.payload,
                                  ', NEXT-HOP:', self.RIP_routingTable[i].nextHop, ']');
                        else:
                            print('Forwarding a normal packet. [', 'FROM:', packetSrc, ', TO:', packetDest,
                                  ', NEXT-HOP:', self.RIP_routingTable[i].nextHop, ']');

