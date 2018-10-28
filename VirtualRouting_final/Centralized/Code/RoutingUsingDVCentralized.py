# -*- coding:utf-8 -*-
# 采用RIP

import socket, threading, time
from DataStructure import *


'''
	lastTimeRecvPktFromNode:dict  # eg: {'A': 1513933432.4340003, 'E': 1513933427.1768813}
'''
global lastTimeRecvPktFromNode;


def send_distance_vector_once(node:Node):
	# node.printOutputMessageHeader();
	# print('sending DV after updating... ');
	n_addr = name_To_address('M');
	sendpkt = Packet(node.address, n_addr, node.RIP_routingTable, 1);
	node.socket.sendto(sendpkt.serialize().encode(), (n_addr.ip, n_addr.port));


# 相邻路由器周期性(30s)地交换距离向量
def send_distance_vector_periodcally(node: Node):
	while True:
		# node.printOutputMessageHeader();
		# print('sending DV periodcally... ');
		
		lock.acquire();
		try:
			n_addr = name_To_address('M');
			sendpkt = Packet(node.address, n_addr, node.RIP_routingTable, 1);
			node.socket.sendto(sendpkt.serialize().encode(), (n_addr.ip, n_addr.port));
		finally:
			lock.release();

		time.sleep(30);

# 启动周期性地交换距离向量的线程
def start_send_distance_vector_periodcally_thread(node: Node):
	t = threading.Thread(target=send_distance_vector_periodcally, args=(node,), name='SendDistanceVectorThread');
	t.start();


# 监听是否收到数据包，并处理收到的数据包
def start_UDP_listener_thread(node: Node):
	t = threading.Thread(target=handle_receiving_packet, args=(node,), name='UDPListenerThread');
	t.start();

def handle_receiving_packet(node: Node):
	while True:
		data, addr = node.socket.recvfrom(1024);  # 接收数据
		recvPkt = Packet();
		recvPkt.deserialize(bytes.decode(data));

	
		if recvPkt.packetType == 0:  # 0表示普通数据包，1表示ORIP响应报文数据包,2表示该数据包是一条发送数据包的指令
			handle_receiving_normal_packet(node, recvPkt);
		elif recvPkt.packetType == 1:
			handle_receiving_RIP_distance_vector_packet(node, recvPkt);
		elif recvPkt.packetType == 2:
			handle_receiving_command_packet(node, recvPkt);


def handle_receiving_normal_packet(node: Node, recvPkt: Packet):
	node.forward_a_normal_packet(recvPkt);


def handle_receiving_RIP_distance_vector_packet(node: Node, recvPkt: Packet):
	# node.printOutputMessageHeader();
	# print('receive DV pkt from:', node_recv_from);
	lock.acquire();
	try:
		for i in range(len(recvPkt.payload)):
			isInNodeRoutingTable = False;
			temp = str(i);
			recvEntry = RIP_RoutingTableEntry(recvPkt.payload[temp]['dest'], recvPkt.payload[temp]['nextHop'], recvPkt.payload[temp]['hopsToDest']);
			change = False;
			for j in range(len(node.RIP_routingTable)):
				# print(node.RIP_routingTable[j].dest == recvEntry.dest);
				if (node.RIP_routingTable[j].dest == recvEntry.dest):
					node.RIP_routingTable[j] = recvEntry;
					change = True;
				
			if (change == False):
				node.RIP_routingTable.append(recvEntry);
				
			
		print('RIP forwarding table after updating... ');
		node.printRIPRoutingTable();
	finally:
		lock.release();
	

	

def handle_receiving_command_packet(node: Node, recvPkt: Packet):
	node.send_a_normal_packet(name_To_address(recvPkt.payload), 'Hello, I\'m ' + str(node.name) + '.', 0);


def start_check_neighbor_nodes_alive_periodcally_thread(node: Node):
	t = threading.Thread(target=check_neighbor_nodes_alive_periodcally, args=(node,), name='CheckNeighborNodesAliveThread');	
	t.start();

# 周期性地检查其他节点是否down掉
def check_neighbor_nodes_alive_periodcally(node: Node):
	while True:
		lock.acquire();
		try:
			# node.printOutputMessageHeader();
			# print('periodcally check..., alive neighbors:', node.aliveNeighbors);

			aliveNodes = node.aliveNeighbors.copy();

			for nodeName in aliveNodes:
				if time.time() - lastTimeRecvPktFromNode[nodeName] > 60:

					node.printOutputMessageHeader();
					print('periodcally check...,', nodeName, 'is down...');
					node.aliveNeighbors.remove(nodeName);

					
					# 采用 "毒性反转" 解决路由环路
					#  当一条路径信息变为无效之后，路由器并不立即将它从路由表中删除，而是用16，即不可达的度量值将它广播出去。
					for i in range(len(node.RIP_routingTable)):
						if node.RIP_routingTable[i].dest == nodeName or node.RIP_routingTable[i].nextHop == nodeName:
							node.RIP_routingTable[i].hopsToDest = 16;

					# 更新本地路由后，向相邻的的alive的节点发送distance vector
					send_distance_vector_once(node);
					# print the new routing table
					node.printOutputMessageHeader();
					print('RIP routing table after updating... ');
					node.printRIPRoutingTable();

		finally:
			lock.release();

		time.sleep(30);





if __name__ == "__main__":
	lastTimeRecvPktFromNode = {};

	nodeName = input('Input the name of this router: ');
	a = Node(nodeName);
	print('router info:', a.name, a.address.port);

	a.RIP_routingTable.append(RIP_RoutingTableEntry(dest=nodeName, nextHop='-', hopsToDest=0));
	
	a.aliveNeighbors = set();

	lock = threading.Lock();
	start_UDP_listener_thread(a);
	start_send_distance_vector_periodcally_thread(a);
