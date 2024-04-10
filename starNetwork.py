"""
Zigbee star topology

Scenario:
  A Zigbee network with start topology arquitecture.
  The network contains only one coordinator. The number of nodes can
  changed by the user.

  The coordinator receives all data from the nodes and treat information
  before closing the connection.

  Randomly, each node start a new connection with the coordinator.

"""

import itertools
import random
import numpy as np
import logging

import simpy

RANDOM_SEED = 42
NUN_NODES = 20

SIM_TIME = 20000

random.seed(RANDOM_SEED)

class NodesMgt:
    
    def __init__(self, env, numNodes) -> None:
        self.numNodes = numNodes
        self.listOfNodes = []
        self.env = env
        self.type = itertools.cycle(["Sensor", "Atuador", "Alarme"])
        self.nodeGenerator()
        self.coordinator = Coordinator(self.env)

    def appendNodeToList(self, n):
        self.listOfNodes.append(n)

    def selectNode(self):
        listNodes = [x for x in self.listOfNodes if x.beingUsed == 0]
        if (len(listNodes) == 0):
            return None
        choice = random.choice(self.listOfNodes)
        if(choice.beingUsed==0):
            choice.startTransmission()
            return choice

    def nodeGenerator(self):
        for i in range(self.numNodes):
            nd = Node(self.env, f"Node_{i}", next(self.type))
            self.appendNodeToList(nd)

    def showAllNodes(self):
        for ndName in self.listOfNodes:
            print(ndName)

class Coordinator:
    
    def __init__(self, env, capacity = 1, responseTime = 1) -> None:
        self.env = env
        self.capacity = capacity
        self.manage = simpy.Resource(env, capacity = capacity)
        self.responseTime = responseTime

    def answerToNode(self, _node, transmissionTime):
        yield self.env.timeout(transmissionTime)
        print(f"Coordinator answer to {_node} at {self.env.now: .2f}")

class Node:
    MIN_RATE = 10
    AVG_RATE = 400
    MAX_RATE = 500
    STD_RATE = 20

    MIN_PACK = 200
    AVG_PACK = 2000
    MAX_PACK = 3000
    STD_PACK = 400

    def __init__(self, env, name, type) -> None:
        self.name = name
        self.type = type
        self.env = env
        self.beingUsed = 0
        self.packageSize = self.AVG_PACK
        self.transmissionRate = self.AVG_RATE
        self.totalTransmitted = 0
        self.totalTime = 0
        self.initTime = 0
    
    def defineTransmissionRate(self):
        self.transmissionRate = min(max(self.MIN_RATE, np.random.normal(self.AVG_RATE, self.STD_RATE)), self.MAX_RATE)
    
    def __str__(self) -> str:
        if (self.totalTime != 0):
            avgTransmitted = self.totalTransmitted/self.totalTime
        else: 
            avgTransmitted = 0
        return f"""
    Nodename: {self.name};
    Node type: {self.type};
    Current Transmission Rate: {self.transmissionRate};
    Current Package Size: {self.packageSize};
    Total Data Transmitted: {self.totalTransmitted};
    Total Time Transmitted: {self.totalTime};
    Average Rate: {avgTransmitted}
    """
    
    def generatePackageSize(self):
        self.packageSize = min(max(self.MIN_PACK, np.random.normal(self.AVG_PACK, self.STD_PACK)), self.MAX_PACK)
        return self.packageSize
    
    def startTransmission(self):
        self.beingUsed = 1
    
    def endTransmission(self):
        self.totalTransmitted = self.totalTransmitted + self.packageSize
        self.totalTime = self.totalTime + self.packageSize / self.transmissionRate
        self.beingUsed = 0

def nodeProcess(env, nd, ndCoordinator):
    print(f"Node {nd.name} is trying to connect to coodinator at {env.now: .2f}.")
    with ndCoordinator.manage.request() as req:
        yield req
        print(f"Node {nd.name} started transmission at {env.now: .2f}.")
        yield env.process(ndCoordinator.answerToNode(nd.name, nd.packageSize/nd.transmissionRate))
        nd.endTransmission()
        print(f"Node {nd.name} finish transmission at {env.now: .2f}.")

def setup(env, ndMgt):
    ndMgt.showAllNodes()
    ndCoordinator = ndMgt.coordinator
    while True:
        random_time = max(2, np.random.normal(10, 5))
        yield env.timeout(random_time)
        nd = ndMgt.selectNode()
        if nd is not None:
            nd.defineTransmissionRate()
            nd.generatePackageSize()
            env.process(nodeProcess(env, nd, ndCoordinator))


if __name__ == '__main__':
    print("Starting Star Topology")
    env = simpy.Environment()
    ndMgt = NodesMgt(env, NUN_NODES)
    env.process(setup(env, ndMgt))
    env.run(until = SIM_TIME)
    ndMgt.showAllNodes()
