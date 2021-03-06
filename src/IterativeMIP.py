# -*- coding: utf-8 -*-
"""
@Created at 2020/8/15 10:11
@Author: Kurt
@file:IterativeMIP.py
@Desc:
"""
from gurobipy import GRB
import gurobipy as gp
import numpy as np
from BOMGraph import BOMGraph
from utils import DefinedException
from IterativeLP import IterativeLP
import time

truth_function = np.sqrt
M = 9999


def cal_coefficient(x):
    """
    :return: derivation and intercept of sqrt function
    """
    if x == 0:
        return -9999, 0
    derivation = (1/2) * np.power(x, -1/2)
    intercept = 1/2 * np.power(x, 1/2)
    return derivation, intercept


class IterativeMIP(IterativeLP):
    def __init__(self, nodes, epsilon=0.1):
        super().__init__(nodes, epsilon)
        self.alpha = dict(zip(self.label_to_node.keys(), [1 / 2] * self.N))
        self.beta = dict(zip(self.label_to_node.keys(), [1 / 2] * self.N))

        self.y = self.model.addVars(self.N, vtype=GRB.BINARY, name='y')
        self.model.setParam("OutputFlag", True)

        for j, info in self.nodes.items():
            node_id = self.node_to_label[j]

            S = self.S[node_id]
            SI = self.SI[node_id]
            lead_time = info['lead_time']
            self.model.addConstr((SI+lead_time-S), GRB.LESS_EQUAL, M*self.y[node_id])

    def termination_criterion(self):

        flag = False
        error = 0
        # print("current alpha: {}".format(self.alpha))
        # print("current beta: {}".format(self.beta))
        for j, info in self.nodes.items():
            node_id = self.node_to_label[j]
            net_replenishment_period = round(self.SI[node_id].x + info['lead_time'] - self.S[node_id].x, 6)

            y = self.y[node_id].x

            error += info['holding_cost'] * abs(
                (self.alpha[node_id] * net_replenishment_period + y * self.beta[node_id])
                - round(truth_function(net_replenishment_period), 3))
            # print("Cum error: {}".format(error))
        print("Current error: {} of iteration: {}".format(error, self.iteration))
        if error <= self.epsilon / self.N:
            flag = True
        if self.update_error == error:
            flag = True
            print("No reduced error, iteration ends.")
        self.update_error = error
        return flag

    def iteration_process(self):
        while True:
            print("************************* New Iteration ***********************************")
            self.iteration += 1
            print("Current iter: {}".format(self.iteration))
            self.optimization()

            if self.model.status == GRB.OPTIMAL:
                print("Current optimal solution of approximation function: {}".format(
                    self.model.getObjective().getValue()))
                print("Current optimal solution of true function: {}".format(self.cal_optimal_value()))
                # print("Current appr obj value: {}".format(self.model.objVal))
                # print("Current true obj value: {}".format(self.cal_optimal_value()))
                # print("Solution: \n {}".format(self.model.getVars()))
                if self.termination_criterion():
                    self.optimal_value = self.cal_optimal_value()
                    break
                self.update_para()
            else:
                raise DefinedException("No solutions.")

    def optimization(self):
        self.obj = gp.LinExpr()
        for j, info in self.nodes.items():
            node_id = self.node_to_label[j]
            SI = self.SI[node_id]
            S = self.S[node_id]
            y = self.y[node_id]
            lead_time = info['lead_time']
            holding_cost = info['holding_cost']
            alpha = self.alpha[node_id]
            beta = self.beta[node_id]
            self.obj += holding_cost * (alpha * (SI + lead_time - S) + y * beta)
        self.model.setObjective(self.obj, GRB.MINIMIZE)
        self.model.optimize()

    def update_para(self):
        for j, info in self.nodes.items():
            node_id = self.node_to_label[j]
            net_replenishment_period = round(self.SI[node_id].x + info['lead_time'] - self.S[node_id].x, 6)
            y = self.y[node_id].x
            # print("---------------------------------------")
            # print("Current Net X:{}".format(net_replenishment_period))
            # print("Current y: {}".format(y))
            # print("previous alpha: {}".format(self.alpha[node_id]))
            # print("previous beta: {}".format(self.beta[node_id]))

            if abs(self.alpha[node_id] * net_replenishment_period + y * self.beta[node_id]) -\
                    round(truth_function(net_replenishment_period), 3) < 0.01:
                continue
            else:
                self.alpha[node_id], self.beta[node_id] = cal_coefficient(round(net_replenishment_period, 3))

            # print("updated alpha: {}".format(self.alpha[node_id]))
            # print("update beta: {}".format(self.beta[node_id]))

    def cal_optimal_value(self):
        optimal_value = 0
        for j, info in self.nodes.items():
            node_id = self.node_to_label[j]
            net_replenishment_period = self.SI[node_id].x + info['lead_time'] - self.S[node_id].x

            optimal_value += info['holding_cost'] * truth_function(round(net_replenishment_period, 3))

        return optimal_value


def parse_result(instance:IterativeMIP) -> None:
    with open("mip solution.txt", "w") as f:
        for j, info in instance.nodes.items():
            node_id = instance.node_to_label[j]
            SI = instance.SI[node_id]
            S = instance.S[node_id]
            # print("Node: {}, SI:{}, S: {}".format(j, SI.x, S.x))
            # print("Net replenishment period: {}".format(SI.x+info['lead_time']-S.x))
            f.write("{}\t{}\n".format(j, SI.x + info['lead_time'] - S.x))


if __name__ == "__main__":

    Nodes = BOMGraph("DAG.txt").nodes
    start = time.time()
    # print(Nodes)
    IMIP = IterativeMIP(nodes=Nodes)
    IMIP.iteration_process()
    parse_result(IMIP)
    print("Optimal value: {}".format(IMIP.optimal_value))
    print("Used cpu time：{}".format(time.time() - start))
