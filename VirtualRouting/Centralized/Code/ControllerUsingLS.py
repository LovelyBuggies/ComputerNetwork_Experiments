# -*- coding:utf-8 -*-
# 集中式路由控制模块

import socket, threading, time
from DataStructure import *

global nodesInTopo, nodesAliveInTopo, edgesInTopo, lastTimeRecvPktFromNode, forwardingTables;
forwardingTables = {'A': [], 'B': [], 'C': [], 'D': [], 'E': []}

def handle_receiving_packet(node: Node):
    while True:
        data, addr = node.receiveSocket.recvfrom(1024);  # 接收数据

        recvPkt = Packet();
        recvPkt.deserialize(bytes.decode(data));

        if recvPkt.packetType == 1:  # 0表示普通数据包，1表示OSPF的链路状态信息数据包,2表示该数据包是一条发送数据包的指令
            handle_receiving_OSPF_link_state_packet(node, recvPkt);


def address_To_name(addr: Address):
    for nodeName in nodesInTopo:
        if addr == name_To_address(nodeName):
            return nodeName;


def handle_receiving_OSPF_link_state_packet(node: Node, recvPkt: Packet):
    node_recv_from = address_To_name(recvPkt.src);
    neighbors = get_node_neighbors(node_recv_from);
    client = {'name': node_recv_from, 'address': recvPkt.src, 'neighbors': neighbors};

    lock.acquire();
    try:
        lastTimeRecvPktFromNode[node_recv_from] = time.time();

        # node.printOutputMessageHeader();
        # print('receive OSPF packet from: ', node_recv_from, recvPkt.src.port, recvPkt.packetType);

        nodesAliveInTopo.add(node_recv_from);
        node.printOutputMessageHeader();
        print('alive nodes: ', nodesAliveInTopo);

        edgesInTopo[node_recv_from] = {};
        for n in recvPkt.payload.keys():
            edgesInTopo[node_recv_from][n] = recvPkt.payload[n][1];
    finally:
        lock.release();

    run_dijkstra_algorithm(node, client);


def start_UDP_listener_thread(node: Node):
    t = threading.Thread(target=handle_receiving_packet, args=(node,), name='UDPListenerThread');
    t.start();


def run_dijkstra_algorithm(node: Node, client: dict):
    okay = set([client['name']]);
    notOkay = nodesAliveInTopo.copy();
    notOkay.remove(client['name']);

    # initialization
    Dist = {};
    prev_step = {};
    for v in notOkay:
        if v in client["neighbors"]:
            Dist[v] = edgesInTopo[client['name']][v];
            prev_step[v] = client['name'];
        else:
            Dist[v] = float('inf');

    # loop
    while len(notOkay) > 0:
        min_node = '';
        min_cost = float('inf');
        for v in notOkay:
            if Dist[v] <= min_cost:
                min_cost = Dist[v];
                min_node = v;

        notOkay.remove(min_node);
        okay.add(min_node);

        for v in notOkay:
            if v in edgesInTopo[min_node]:
                if Dist[v] > Dist[min_node] + edgesInTopo[min_node][v]:
                    Dist[v] = Dist[min_node] + edgesInTopo[min_node][v];
                    prev_step[v] = min_node;
            elif min_node in edgesInTopo[v]:
                if Dist[v] > Dist[min_node] + edgesInTopo[v][min_node]:
                    Dist[v] = Dist[min_node] + edgesInTopo[v][min_node];
                    prev_step[v] = min_node;

    construct_forwarding_table(client, prev_step);
    return_forwarding_table(node, client);




def construct_forwarding_table(client: dict, prev_step: dict):
    # construct forwarding table of the parameter'node'
    next_step_from_current_node = {};

    for x in prev_step.keys():
        if prev_step[x] == client['name']:
            next_step_from_current_node[x] = x;
        else:
            temp = x;
            while prev_step[temp] != client['name']:
                temp = prev_step[temp];
            next_step_from_current_node[x] = temp;

    forwardingTables[client['name']].clear();
    for k in next_step_from_current_node.keys():
        forwardingTables[client['name']].append(OSPF_ForwardingTableEntry(dest=k, nextHop=next_step_from_current_node[k]));


#向发送请求的节点返回路由表
def return_forwarding_table(node: Node, client: dict):
    targetAddr = client['address'];
    targetForwardingTabel = forwardingTables[client['name']];
    sendpkt = Packet(node.address, targetAddr,targetForwardingTabel , 1);
    node.sendSocket.sendto(sendpkt.serialize().encode(), (targetAddr.ip, targetAddr.port));


# 周期性地检查其他节点是否down掉
def check_nodes_alive_periodcally(node: Node):
    while True:
        lock.acquire();
        try:

            aliveNodes = nodesAliveInTopo.copy();

            for nodeName in aliveNodes:
                if nodeName != node.name:
                    if time.time() - lastTimeRecvPktFromNode[nodeName] > 60:
                        nodesAliveInTopo.remove(nodeName);
                        node.printOutputMessageHeader();
                        print('periodcally check...,', nodeName, 'is down...');
        finally:
            lock.release();

        time.sleep(20);


def start_check_nodes_alive_periodcally_thread(node: Node):
	t = threading.Thread(target=check_nodes_alive_periodcally, args=(node,), name='CheckNodesAliveThread');
	t.start();


if __name__ == "__main__":
    nodesInTopo = set(['A', 'B', 'C', 'D', 'E', 'M']);
    nodesAliveInTopo = set();
    edgesInTopo = {};
    lastTimeRecvPktFromNode = {};

    nodeName = 'M';
    m = Node(nodeName);
    print('router info: ', m.name, m.address.port);

    lock = threading.Lock();

    start_UDP_listener_thread(m);
    start_check_nodes_alive_periodcally_thread(m);