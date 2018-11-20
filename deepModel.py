#!/usr/bin/env python3

import numpy as np
import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

import modelInput

#model of the network
class Net(nn.Module):
    def __init__(self, softmax=False, width=1000):
        super(Net, self).__init__()

        self.softmax = softmax

        #simple feed forward
        self.fc1 = nn.Linear(modelInput.stateSize, width)
        self.fc2 = nn.Linear(width, width)
        self.fc3 = nn.Linear(width, modelInput.numActions)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        if self.softmax:
            x = F.softmax(self.fc3(x), dim=0)
        else:
            x = self.fc3(x)
        return x

class DeepCfrModel:

    #for advantages, the input is the state vector
    #and the output is a vector of each move's advantage
    #for strategies, the input is the state vector
    #and the output is a vector of each move's probability

    #so the inputs are exactly the same (modelInput.stateSize), and the outputs
    #are almost the same (modelInput.numActions)
    #strategy is softmaxed, advantage is not


    def __init__(self, softmax, lr=0.0001):
        self.dataSet = []
        self.labelSet = []
        self.iterSet = []

        #TODO init our network so that we initially output 0 for everything

        self.net = Net(softmax=softmax)
        self.optimizer = optim.Adam(self.net.parameters(), lr=lr)

    def addSample(self, data, label, iter):
        self.dataSet.append(modelInput.stateToTensor(data))

        labelDense = np.zeros(modelInput.numActions)
        for action, value in label:
            n = modelInput.enumAction(action)
            labelDense[n] = value
        self.labelSet.append(labelDense)

        self.iterSet.append(iter)

    def predict(self, state):
        data = modelInput.stateToTensor(state)
        data = torch.from_numpy(data).float()
        return self.net(data).detach().numpy()

    def train(self, epochs=100):
        #can't train without any samples
        if len(self.dataSet) == 0:
            return

        dataSet = np.array(self.dataSet)
        labelSet = np.array(self.labelSet)
        iterSet = np.array(self.iterSet)
        for i in range(epochs):
            sampleIndices = np.random.choice(len(dataSet), 32)

            sampleData = dataSet[sampleIndices]
            data = torch.from_numpy(sampleData).float()

            sampleLabels = labelSet[sampleIndices]
            labels = torch.from_numpy(sampleLabels).float()

            sampleIters = iterSet[sampleIndices]
            iters = torch.from_numpy(sampleIters).float()

            self.optimizer.zero_grad()
            ys = self.net(data)

            #loss function from the paper
            loss = torch.sum(iters.view(32,1) * ((labels - ys) ** 2))
            #loss = torch.sum(iters * ((labels - ys) ** 2).t())
            #print the last 10 losses
            if i > epochs-11:
                print(loss, file=sys.stderr)
            loss.backward()
            self.optimizer.step()

