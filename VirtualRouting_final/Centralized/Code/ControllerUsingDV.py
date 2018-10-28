# -*- coding:utf-8 -*-
# 采用RIP

import socket, threading, time
from DataStructure import *


'''
	lastTimeRecvPktFromNode:dict  # eg: {'A': 1513933432.4340003, 'E': 1513933427.1768813}
'''
global lastTimeRecvPktFromNode, rip_table, nodesInTopo, nodesAliveInTopo, m, allNeighbor;


def send_distance_vector_once(node:Node):
	# node.printOutputMessageHeader();
	# print('sending DV after updating... ');
	for n in allNeighbor[node]:
		if n in nodesAliveInTopo:
			if n != node:
				n_addr = name_To_address(n);
				sendpkt = Packet(m.address, n_addr, rip_table[n], 1);
				m.socket.sendto(sendpkt.serialize().encode(), (n_addr.ip, n_addr.port));


# 相邻路由器周期性(30s)地交换距离向量
def send_distance_vector_periodcally(node: Node):
	while True:
		# node.printOutputMessageHeader();
		# print('sending DV periodcally... ');
		
		lock.acquire();
		try:
			for n in node.neighbors:
				if n != node.name:
					n_addr = name_To_address(n);
					sendpkt = Packet(node.address, n_addr, node.RIP_routingTable, 1);
					node.sendSocket.sendto(sendpkt.serialize().encode(), (n_addr.ip, n_addr.port));
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

	
		if recvPkt.packetType == 1:  # 0表示普通数据包，1表示ORIP响应报文数据包,2表示该数据包是一条发送数据包的指令
			handle_receiving_RIP_distance_vector_packet(node, recvPkt);


def handle_receiving_normal_packet(node: Node, recvPkt: Packet):
	node.forward_a_normal_packet(recvPkt);


def handle_receiving_RIP_distance_vector_packet(node: Node, recvPkt: Packet):
	node_recv_from = address_To_name(recvPkt.src);
	neighbors = get_node_neighbors(node_recv_from);
	if node_recv_from not in allNeighbor.keys():
		allNeighbor[node_recv_from] = neighbors;
	client = {'name': node_recv_from, 'address': recvPkt.src, 'neighbors': neighbors};
	
	# node.printOutputMessageHeader();
	# print('receive DV pkt from:', node_recv_from);

	lock.acquire();
	try:

		if node_recv_from not in nodesAliveInTopo:
			nodesAliveInTopo.add(node_recv_from);
			rip_table[node_recv_from] = {};
		
		node.printOutputMessageHeader();
		print('alive nodes: ', nodesAliveInTopo);
		#if node_recv_from in node.neighbors.keys():
		#	node.aliveNeighbors.add(node_recv_from);
		
		
		lastTimeRecvPktFromNode[node_recv_from] = time.time();

		
		changeRoutingTable = False;
		rip_table[node_recv_from] = {};
		# 合并节点自己的RIP表和收到的RIP表
		for i in range(len(recvPkt.payload)):
			isInNodeRoutingTable = False;
			recvEntry = RIP_RoutingTableEntry(recvPkt.payload[i]['dest'], recvPkt.payload[i]['nextHop'], recvPkt.payload[i]['hopsToDest']);
			rip_table[node_recv_from][i] = recvEntry;
			
		temp = rip_table[node_recv_from].copy();
		for v in client['neighbors']:
			if v in nodesAliveInTopo:
				tempTable = rip_table[v].copy();
				isInNodeRoutingTable = False;
				for i in range(len(rip_table[node_recv_from])):
					for j in range(len(rip_table[v])):
						# 收到的RIP表中和节点自己的RIP表dest相同的条目
						if temp[i].dest == rip_table[v][j].dest:
							isInNodeRoutingTable = True;

							if temp[i].hopsToDest < tempTable[j].hopsToDest-1:
								rip_table[v][j].nextHop = address_To_name(recvPkt.src);
								rip_table[v][j].hopsToDest = temp[i].hopsToDest + 1;
								changeRoutingTable = True;
							else:
								if tempTable[j].nextHop == address_To_name(recvPkt.src):
									if rip_table[v][j].hopsToDest != temp[i].hopsToDest + 1:
										rip_table[v][j].hopsToDest = temp[i].hopsToDest + 1;
										changeRoutingTable = True;
									
										if rip_table[v][j].hopsToDest > 16:
											rip_table[v][j].hopsToDest = 16;
					
					# 收到的RIP表中和节点自己的RIP表dest不同的条目
					if not isInNodeRoutingTable:
						mytemp = RIP_RoutingTableEntry(temp[i].dest, temp[i].nextHop, temp[i].hopsToDest);
						mytemp.nextHop = node_recv_from;
						mytemp.hopsToDest += 1;
						if mytemp.hopsToDest > 16:
							mytemp.hopsToDest = 16;
						k = len(rip_table[v]);
						rip_table[v][k] = mytemp;
						changeRoutingTable = True;


				# 更新本地路由后，向相邻的的alive的节点发送distance vector
				if changeRoutingTable:
					#send_distance_vector_once(Node(v));
					n_addr = name_To_address(v);
					sendpkt = Packet(node.address, n_addr, rip_table[v], 1);
					node.socket.sendto(sendpkt.serialize().encode(), (n_addr.ip, n_addr.port));
					# print the new routing table
					# node.printOutputMessageHeader();
					print('RIP routing table after updating... ');
					# node.printRIPRoutingTable();

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

			aliveNodes = nodesAliveInTopo.copy();

			for nodeName in aliveNodes:
				if time.time() - lastTimeRecvPktFromNode[nodeName] > 60:

					node.printOutputMessageHeader();
					print('periodcally check...,', nodeName, 'is down...');
					nodesAliveInTopo.remove(nodeName);

					
					# 采用 "毒性反转" 解决路由环路
					#  当一条路径信息变为无效之后，路由器并不立即将它从路由表中删除，而是用16，即不可达的度量值将它广播出去。
					for v in allNeighbor[nodeName]:
						if v != nodeName and (v in nodesAliveInTopo):
							for i in range(len(rip_table[v])):
								if rip_table[v][i].dest == nodeName or rip_table[v][i].nextHop == nodeName:
									rip_table[v][i].hopsToDest = 16;

					# 更新本地路由后，向相邻的的alive的节点发送distance vector
					send_distance_vector_once(nodeName);
					# print the new routing table
					node.printOutputMessageHeader();
					print('RIP routing table after updating... ');
					# node.printRIPRoutingTable();

		finally:
			lock.release();

		time.sleep(30);





if __name__ == "__main__":
	nodesInTopo = set(['A', 'B', 'C', 'D', 'E', 'M']);
	nodesAliveInTopo = set();
	edgesInTopo = {};
	lastTimeRecvPktFromNode = {};
	allNeighbor = {};
	
	nodeName = 'M';
	m = Node(nodeName);
	print('router info: ', m.name, m.address.port);
	
	rip_table = {};

	# RIP_routingTable.append(RIP_RoutingTableEntry(dest=nodeName, nextHop='-', hopsToDest=0));
	
	lock = threading.Lock();
	start_UDP_listener_thread(m);
	start_check_neighbor_nodes_alive_periodcally_thread(m);
