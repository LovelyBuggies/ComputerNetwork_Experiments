# -*- coding:utf-8 -*-
# 采用开放最短路径优先（OSPF）选路协议

import socket, threading, time
from DataStructure import *

'''
	nodesInTopo:set(str)  # eg: {'D', 'B', 'C', 'A', 'E'}
	nodesAliveInTopo:set(str)  # eg: {'D', 'B', 'C', 'A', 'E'}
	edgesInTopo:dict{dict}  # eg: {'A': {'D': 60, 'E': 20, 'C': 80}}
	lastTimeRecvPktFromNode:dict  # eg: {'A': 1513933432.4340003, 'E': 1513933427.1768813}
'''
global nodesInTopo, nodesAliveInTopo, edgesInTopo, lastTimeRecvPktFromNode;


# 向控制主机周期性地发送节点node的链路状态信息
def send_link_state_periodcally(node: Node):
    while True:

        n_addr = name_To_address('M');
        sendpkt = Packet(node.address, n_addr, node.neighbors, 1);
        node.sendSocket.sendto(sendpkt.serialize().encode(), (n_addr.ip, n_addr.port));

        time.sleep(30);


# 启动周期性地发送链路状态的线程
def start_broadcast_link_state_periodcally_thread(node: Node):
    t = threading.Thread(target=send_link_state_periodcally, args=(node,), name='SendcastLinkStateThread');
    t.start();


# 监听是否收到数据包，并处理收到的数据包
def start_UDP_listener_thread(node: Node):
    t = threading.Thread(target=handle_receiving_packet, args=(node,), name='UDPListenerThread');
    t.start();


def handle_receiving_packet(node: Node):
    while True:
        data, addr = node.receiveSocket.recvfrom(1024);  # 接收数据

        recvPkt = Packet();
        recvPkt.deserialize(bytes.decode(data));

        if recvPkt.packetType == 0:  # 0表示普通数据包，1表示controller返回的路由表，2表示该数据包是一条发送数据包的指令
            handle_receiving_normal_packet(node, recvPkt);
        elif recvPkt.packetType == 1:
            handle_receiving_forwarding_table(node, recvPkt);
        elif recvPkt.packetType == 2:
            handle_receiving_command_packet(node, recvPkt);


def handle_receiving_forwarding_table(node: Node, recvPkt: Packet):
    lock.acquire();
    try:
        node.OSPF_forwardingTable.clear();
        recvForwardingTable = recvPkt.payload;
        node.OSPF_forwardingTable.clear();
        for k in recvForwardingTable:
            node.OSPF_forwardingTable.append(OSPF_ForwardingTableEntry(dest=k['dest'], nextHop=k['nextHop']));
        node.printOutputMessageHeader();
        print('OSPF forwarding table after updating... ');
        node.printOSPFForwardingTable();
    finally:
        lock.release();


def handle_receiving_normal_packet(node: Node, recvPkt: Packet):
    node.forward_a_normal_packet(recvPkt);


def handle_receiving_command_packet(node: Node, recvPkt: Packet):
	node.send_a_normal_packet(name_To_address(recvPkt.payload), 'Hello, I\'m ' + str(node.name) + '.', 0);


def address_To_name(addr: Address):
    for nodeName in nodesInTopo:
        if addr == name_To_address(nodeName):
            return nodeName;


if __name__ == "__main__":
    nodesInTopo = set(['A', 'B', 'C', 'D', 'E']);
    nodesAliveInTopo = set();
    edgesInTopo = {};
    lastTimeRecvPktFromNode = {};

    nodeName = input('Input the name of this router: ');
    a = Node(nodeName);
    print('router info: ', a.name, a.address.port);

    nodesAliveInTopo.add(nodeName);
    edgesInTopo[nodeName] = {};
    for n in a.neighbors.keys():
        edgesInTopo[nodeName][n] = a.neighbors[n][1];

    lock = threading.Lock();

    start_UDP_listener_thread(a);
    start_broadcast_link_state_periodcally_thread(a);


