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
NUN_NODES = 5

SIM_TIME = 2000

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
        a = 1
        while True:
            choice = random.choice(self.listOfNodes)
            if(choice.beingUsed==0):
                choice.startTransmission()
                return choice



    def nodeGenerator(self):
        for i in range(self.numNodes):
            print(i)
            nd = Node(self.env, f"Node_{i}", next(self.type))
            self.appendNodeToList(nd)

    def showAllNodes(self):
        for ndName in self.listOfNodes:
            print(ndName)
            print()

class Coordinator:
    
    def __init__(self, env, capacity = 1, responseTime = 1) -> None:
        self.env = env
        self.capacity = capacity
        self.manage = simpy.Resource(env, capacity = capacity)
        self.responseTime = responseTime

    def answerToNode(self, _node, transmissionTime):
        yield self.env.timeout(transmissionTime)
        print(f"Answer {_node} at {self.env.now: .2f}")

class Node:
    MIN_RATE = 10
    AVG_RATE = 40
    MAX_RATE = 50
    STD_RATE = 20

    MIN_PACK = 200
    AVG_PACK = 1000
    MAX_PACK = 3000
    STD_PACK = 800


    def __init__(self, env, name, type) -> None:
        self.name = name
        self.type = type
        self.env = env
        self.beingUsed = 0
        self.packageSize = self.AVG_PACK
        self.transmissionRate = self.AVG_RATE
    
    def defineTransmissionRate(self):
        self.transmissionRate = min(max(self.MIN_RATE, np.random.normal(self.AVG_RATE, self.STD_RATE)), self.MAX_RATE)
    
    def __str__(self) -> str:
        return f"""
                Nodename: {self.name};
                Node type: {self.type};
                Current Transmission Rate: {self.transmissionRate};
                Current Package Size: {self.packageSize};
                Total Data Transmitted: -;
                Avarage Transmission Rate: -;
            \n
            """
    
    def generatePackageSize(self):
        self.packageSize = min(max(self.MIN_PACK, np.random.normal(self.AVG_PACK, self.STD_PACK)), self.MAX_PACK)
        return self.packageSize
    
    def startTransmission(self):
        self.beingUsed = 1
    
    def endTransmission(self):
        self.beingUsed = 0



def setup(env):
    ndMgt = NodesMgt(env, NUN_NODES)
    ndMgt.showAllNodes()
    while True:
        random_time = max(10, np.random.normal(100, 20))
        yield env.timeout(random_time)
        nd = ndMgt.selectNode()
        nd.defineTransmissionRate()
        nd.generatePackageSize()
        print(f"Node name {nd.name} is trying to connect to coodinator at {env.now: .2f}.")
        ndCoordinator = ndMgt.coordinator
        with ndCoordinator.manage.request() as req:
            yield req
            print(f"Node name {nd.name} started transmission.")
            yield env.process(ndCoordinator.answerToNode(nd.name, nd.packageSize/nd.transmissionRate))
            nd.endTransmission()
            print(f"Node {nd.name} finish transmission")
        


print("Starting Star Topology")

env = simpy.Environment()
env.process(setup(env))
env.run(until = SIM_TIME)


    
# ndMgt.showAllNodes()

# listOfNodesConnected = []

# def node(env, name, coordinator):
#     global listOfNodesConnected
#     print(f"Node {name} trying to contact cordenator at {env.now: .2f}")
#     with coordinator.manage.request() as request:
#         listOfNodesConnected.append(name)
#         yield request
#         print(listOfNodesConnected)
#         print(f"Node {name} connect to coordinator at {env.now: .2f}")
#         yield env.process(coordinator.answerToNode(name))
#         listOfNodesConnected.remove(name)
#         print(f"Node {name} finish sent package to coordinator at {env.now: .2f}")