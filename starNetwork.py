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

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import font_manager as fm
from matplotlib import rc, rcParams

import itertools
import random
import numpy as np
import pandas as pd
import simpy

RANDOM_SEED = 42
NUN_NODES = [1,3,5,8]

SIM_TIME = 60
# 1h: 3600
# 2h: 7200
# 3h: 10800
# 4h: 14400
# 5h: 18000
# 6h: 21600
# 7h: 25200
# 8h: 28800

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
        # print(f"Coordinator answer to {_node} at {self.env.now: .2f}")

class Node:
    MIN_RATE = 10
    AVG_RATE = 400
    MAX_RATE = 500
    STD_RATE = 20

    RATE_ZIGBEE = 250_000 #bps
    RATE_BLE = 1_000_000 #bps

    MIN_PACK = 200
    AVG_PACK = 2000
    MAX_PACK = 3000
    STD_PACK = 400

    PACK = 80_000 #bits

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
        self.count = 0
    
    def defineTransmissionRate(self):
        # self.transmissionRate = min(max(self.MIN_RATE, np.random.normal(self.AVG_RATE, self.STD_RATE)), self.MAX_RATE)
        self.transmissionRate = self.RATE_ZIGBEE
    
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
        # self.packageSize = min(max(self.MIN_PACK, np.random.normal(self.AVG_PACK, self.STD_PACK)), self.MAX_PACK)
        self.packageSize = self.PACK
        return self.packageSize
    
    def startTransmission(self):
        self.beingUsed = 1
    
    def endTransmission(self):
        self.totalTransmitted = self.totalTransmitted + self.packageSize
        self.totalTime = self.totalTime + self.packageSize / self.transmissionRate
        self.count = self.count + 1
        self.beingUsed = 0

df = pd.DataFrame()

def nodeProcess(env, nd, ndCoordinator):
    global df
    t0 = env.now
    # print(f"Node {nd.name} is trying to connect to coodinator at {env.now: .2f}.")
    with ndCoordinator.manage.request() as req:
        yield req
        t1 = env.now
        # print(f"Node {nd.name} started transmission at {env.now: .2f}.")
        yield env.process(ndCoordinator.answerToNode(nd.name, nd.packageSize/nd.transmissionRate))
        nd.endTransmission()
        t2 = env.now
        # print(f"Node {nd.name} finish transmission at {env.now: .2f}.")
    data = {
            "Node": [nd.name],
            "Count": [nd.count],
            "PackageSize": [nd.packageSize],
            "Rate": [nd.transmissionRate],
            "Trying to connect [T0]": [t0],
            "Transmission Start [T1]": [t1],
            "Transmission Finish [T2]": [t2],
            "T0 - T1": [t1 - t0],
            "T1 - T2": [t2 - t1],
            "T0 - T2": [t2 - t0]
    }
    dfAux = pd.DataFrame.from_dict(data=data)
    df = pd.concat([df, dfAux], ignore_index=True)

def setup(env, ndMgt):
    ndMgt.showAllNodes()
    ndCoordinator = ndMgt.coordinator
    while True:
        random_time = 0.05 # max(2, np.random.normal(10, 5))
        yield env.timeout(random_time)
        nd = ndMgt.selectNode()
        if nd is not None:
            nd.defineTransmissionRate()
            nd.generatePackageSize()
            env.process(nodeProcess(env, nd, ndCoordinator))


if __name__ == '__main__':
    dfSummary = pd.DataFrame()
    colorIter = itertools.cycle(['blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'black', 'white', 'orange', 'purple'])
    fig, axe = plt.subplots(1,1, figsize=(3,4))
    plt.subplots_adjust(left=0.05, bottom=0.1, right=0.90, top=0.90, wspace=0.2, hspace=0.6)
    print("Starting Star Topology")
    for i in NUN_NODES:
        df = pd.DataFrame()
        env = simpy.Environment()
        ndMgt = NodesMgt(env, i)
        env.process(setup(env, ndMgt))
        env.run(until = SIM_TIME)
        ndMgt.showAllNodes()
        print(df)
        df.to_excel(f"Zigbee_{i}.xlsx")
        colorIten = next(colorIter)
        total = len(df.index) * 80_000_000
        dfAux = pd.DataFrame.from_dict(
            {
                "NumOfNodes": [i],
                "Total Data": [total]
            }
        )
        dfSummary = pd.concat([dfSummary, dfAux], ignore_index=True)
        df_n = df
        axe.plot(df_n['Trying to connect [T0]'], df_n['T0 - T1'], c = colorIten, label = f"{i} nodes")
        plt.title("Delay de conexão para Zigbee na topologia estrela com diferentes número de nós", fontname="Times New Roman", weight='bold', fontsize = 25)
        plt.ylabel("Tempo entre a solicitação e a conexão (s)", fontname="Times New Roman Bold", fontsize=20, fontweight='bold')
        plt.xlabel("Tempo decorrido do inicio da simulação (s)", fontname="Times New Roman Bold", fontsize=20, fontweight='bold')
        axe.tick_params(labelsize=20, length=3, width=0.7)
        axe.legend(fontsize = 16, loc = 'upper right', prop={'family': "Times New Roman"})
    print(dfSummary)

    plt.show()
