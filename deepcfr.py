#!/usr/bin/env python3

import asyncio
import collections
import copy
import math
import numpy as np
import random
import sys

import config
import model
import dataStorage

#Deep MCCFR

#based on this paper
#https://arxiv.org/pdf/1811.00164.pdf

#this agent breaks some compatibility with the other agents
#which I think is fine as we generally do all of our searching ahead of time
#so we'll need new runner functions

class DeepCfrAgent:
    #each player gets one of each model
    #advModels calculates advantages
    #stratModels calculates average strategy

    #branch limit is the maximum number of actions taken
    #actions that aren't taken are probed (i.e. rolled out)

    #depth limit is the maximum number of turns taken from the root
    #after the limit it hit, all games are evaluated via rollout
    #this agent is only applied at the root, so depth limit might
    #significantly affect the quality of late-game strategies
    #(although we could use RM to find new late-game strategies,
    #but that's outside the scope of this agent)

    #resumeIter is the iteration to resume from
    #this really should be a paremeter to the search function,
    #but we need to know about it when we initialize the models
    #this is a problem with our agent being made for a one-shot training cycle
    #instead of multiple training cycles like the others
    def __init__(
            self,
            writeLock,
            trainingBarrier,
            sharedDict,
            advModels=None, stratModels=None,
            verbose=False):

        self.pid = -1


        self.writeLock = writeLock
        self.trainingBarrier = trainingBarrier
        self.sharedDict = sharedDict

        if config.resumeIter == None:
            #fresh start, delete old data
            dataStorage.clearData()
            

        #if the adv models are passed in, assume we aren't responsible for sharing them
        if advModels:
            self.advModels = advModels
            self.manageSharedModels = False
        else:
            self.advModels = [full.model.DeepCfrModel(name='adv' + str(i), softmax=False, writeLock=writeLock, sharedDict=sharedDict) for i in range(2)]
            self.manageSharedModels = True

        if stratModels:
            self.stratModels = stratModels
        else:
            self.stratModels = [full.model.DeepCfrModel(name='strat' + str(i), softmax=True, writeLock=writeLock, sharedDict=sharedDict) for i in range(2)]

        #flag so if we never search, we don't bother training
        self.needsTraining = False

        self.verbose = verbose

    async def search(self, context, pid=0, limit=100, innerLoops=1, seed=None, history=[[],[]]):
        self.pid = pid

        start = config.resumeIter if config.resumeIter else 0

        if self.pid == 0:
            print(end='', file=sys.stderr)
        for i in range(start, limit):
            if self.pid == 0:
                print('\rTurn Progress: ' + str(i) + '/' + str(limit), end='', file=sys.stderr)

            #this is mainly used for setting a condition breakpoint
            #there's probably a better way
            #if i == 5:
                #print('ready for debugging')

            #for self.small games, this is necessary to get a decent number of samples
            for j in range(innerLoops):
                self.needsTraining = True
                #we want each game tree traversal to use the same seed
                if seed:
                    curSeed = seed
                else:
                    curSeed = config.game.getSeed()
                game = config.game.Game(context=context, seed=curSeed, history=history, verbose=self.verbose)
                await game.startGame()
                await self.cfrRecur(context, game, curSeed, history, i)



            #save our adv data after each iteration
            #so the non-zero pid workers don't have data cached
            self.advModels[i % 2].clearSampleCache()
            #go ahead and clear our strat caches as well
            #just in case the program is exited
            for j in range(2):
                self.stratModels[j].clearSampleCache()

            #only need to train about once per iteration
            self.trainingBarrier.wait()
            if self.pid == 0:
                if self.needsTraining:
                    self.advTrain(i % 2)
                if self.manageSharedModels:
                    self.sharedDict['advNet' + str(i % 2)] = self.advModels[i % 2].net
                else:
                    self.advModels[i % 2].shareMemory()
            self.trainingBarrier.wait()
            #broadcast the new network back out
            if self.manageSharedModels:
                self.advModels[i % 2].net = self.sharedDict['advNet' + str(i % 2)]
            #else:
                #self.advModels[i % 2].shareMemory()
            self.needsTraining = False

            if self.pid == 0:
                print('\nplaying games', file=sys.stderr)

            
        #clear the sample caches so the master agent can train with our data
        for sm in self.stratModels:
            sm.clearSampleCache()

        self.trainingBarrier.wait()

        if self.pid == 0:
            print(file=sys.stderr)

    def advTrain(self, player):
        model = self.advModels[player]
        model.train(epochs=config.advEpochs)

    def stratTrain(self):
        if self.pid == 0:
            print('training strategy', file=sys.stderr)
        #we train both strat models at once
        for model in self.stratModels:
            model.train(epochs=config.stratEpochs)

    def getProbs(self, player, infoset, actions):
        sm = self.stratModels[player]
        stratProbs = sm.predict(infoset, trace=True)
        print('infoset', infoset)
        print('strat probs', stratProbs)
        actionNums = [config.game.enumAction(a) for a in actions]
        probs = []
        for n in actionNums:
            probs.append(stratProbs[n])
        probs = np.array(probs)

        pSum = np.sum(probs)
        if pSum > 0:
            return probs / np.sum(probs)
        else:
            return np.array([1 / len(actions) for a in actions])

    #recursive implementation of cfr
    #history is a list of (seed, player, action) tuples
    #assumes the game has already had the history applied
    async def cfrRecur(self, context, game, startSeed, history, iter, depth=0, q=1, rollout=False):
        if config.depthLimit and depth > config.depthLimit:
            rollout = True

        onPlayer = iter % 2
        offPlayer = (iter + 1) % 2

        player, req, actions = await game.getTurn()

        if 'win' in req:
            if player == onPlayer:
                return (req['win'] + 2) / 4
            else:
                return (-1 * req['win'] + 2) / 4

        #game uses append, so we have to make a copy to keep everything consistent when we get advantages later
        infoset = copy.copy(game.getInfoset(player))

        if player == offPlayer:
            #get probs so we can sample a single action
            probs, _ = self.regretMatch(offPlayer, infoset, actions, -1)
            exploreProbs = probs * (1 - config.exploreRate) + config.exploreRate / len(actions)
            action = np.random.choice(actions, p=exploreProbs)
            #save sample for final average strategy
            if not rollout:
                self.updateProbs(offPlayer, infoset, actions, probs, iter // 2 + 1)

            if depth == 1 and self.pid == 0:
                print('offplayer ' + str(player) + ' hand ' + str(game.hands[player]) + ' probs', list(zip(actions, probs)), file=sys.stderr)
            await game.takeAction(player, req, action)

            if player == 0:
                newHistory = [history[0] + [(None, action)], history[1]]
            else:
                newHistory = [history[0], history[1] + [(None, action)]]

            return await self.cfrRecur(context, game, startSeed, newHistory, iter, depth=depth, rollout=rollout, q=q)

        elif player == onPlayer:
            #get probs, which action we take depends on the configuration
            probs, regrets = self.regretMatch(onPlayer, infoset, actions, depth)
            if depth == 1 and self.pid == 0:
                print('onplayer ' + str(player) + ' hand ' + str(game.hands[player]) + ' probs', list(zip(actions, probs)), 'advs', regrets, file=sys.stderr)
            if rollout:
                #we pick one action according to the current strategy
                actions = [np.random.choice(actions, p=probs)]
                actionIndices = [0]
            elif config.branchingLimit:
                #select a set of actions to pick
                #chance to play randomly instead of picking the best actions
                exploreProbs = probs# * (0.9) + 0.1 / len(probs)
                #there might be some duplicates but it shouldn't matter
                actionIndices = np.random.choice(len(actions), config.branchingLimit, p=exploreProbs)
            else:
                #we're picking every action
                actionIndices = list(range(len(actions)))

            #get expected reward for each action
            rewards = []
            gameUsed = False

            for i in range(len(actions)):
                action = actions[i]

                #use rollout for non-sampled actions
                if not i in actionIndices:
                    curRollout = True
                else:
                    curRollout = rollout

                #don't have to re-init game for the first action
                if gameUsed:
                    game = config.game.Game(context, seed=startSeed, history=history, verbose=self.verbose)
                    await game.startGame()
                    await game.getTurn()
                else:
                    gameUsed = True

                #I want to see if we get good results by keeping the RNG the same
                #this is closer to normal external sampling
                #seed = await game.resetSeed()
                await game.takeAction(player, req, action)
                #historyEntry = (None, player, action)

                if player == 0:
                    newHistory = [history[0] + [(None, action)], history[1]]
                else:
                    newHistory = [history[0], history[1] + [(None, action)]]

                r = await self.cfrRecur(context, game, startSeed, newHistory, iter, depth=depth+1, rollout=curRollout, q=q*probs[i])
                rewards.append(r)

            if self.verbose:
                print('infoset', infoset)
                print('actions, probs, and rewards', list(zip(actions, probs, rewards)))
            if not rollout:
                #save sample of advantages
                stateExpValue = 0
                for p,r in zip(probs, rewards):
                    stateExpValue += p * r
                advantages = [r - stateExpValue for r in rewards]
                #CFR+, anyone?
                #also using the sqrt(t) equation from that double neural cfr paper
                #advantages = [math.sqrt(iter // 2) * g / math.sqrt(iter // 2 + 1) + (r - stateExpValue) / math.sqrt(iter // 2 + 1) for r, g in zip(rewards, regrets)]
                if depth == 1 and self.pid == 0:
                    print('onplayer', player, 'hand', game.hands[player], 'new advs', list(zip(actions, advantages)), 'exp value', stateExpValue, file=sys.stderr)
                #print('advantages', advantages)

                am = self.advModels[onPlayer]
                am.addSample(infoset, zip(actions, advantages), iter // 2 + 1)

                #if depth == 0 and self.pid == 0:
                    #print('player', str(onPlayer), file=sys.stderr)
                    #print('stateExpValue', stateExpValue, 'from', list(zip(probs, rewards)), file=sys.stderr)
                    #print('advantages', list(zip(actions, advantages)), file=sys.stderr)

                return stateExpValue
            else:
                #we can't calculate advantage, so we can't update anything
                #we only have one reward, so just return it
                return rewards[0]

   
    #generates probabilities for each action
    #based on modeled advantages
    def regretMatch(self, player, infoset, actions, depth):
        am = self.advModels[player]
        advs = am.predict(infoset)
        actionNums = [config.game.enumAction(a) for a in actions]
        probs = []
        for n in actionNums:
            probs.append(max(0, advs[n]))
        #if depth == 0 and self.pid == 0:
            #print('predicted advantages', [(action, advs[n]) for action, n in zip(actions, actionNums)], file=sys.stderr)
        probs = np.array(probs)
        pSum = np.sum(probs)
        if pSum > 0:
            return probs / pSum, advs
        else:
            #pick the best action with probability 1
            best = None
            for i in range(len(actionNums)):
                n = actionNums[i]
                if best == None or advs[n] > advs[actionNums[best]]:
                    best = i
            probs = [0 for a in actions]
            probs[best] = 1
            return np.array(probs), advs
            #actually, play randomly
            """
            return np.array([1 / len(actions) for a in actions]), advs
            """

    #adds sample of current strategy
    def updateProbs(self, player, infoset, actions, probs, iter):
        sm = self.stratModels[player]
        sm.addSample(infoset, zip(actions, probs), iter)
