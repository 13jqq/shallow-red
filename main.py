#!/usr/bin/env python3

import asyncio
import collections
import copy
import math
import numpy as np
import os
import random
import sys
import subprocess

import moves
from game import Game
import model
import modelInput
import montecarlo.rm as rm
import montecarlo.exp3 as exp3

humanTeams = [

    '|ditto|choicescarf|H|transform|Timid|252,,4,,,252||,0,,,,|||]|zygarde|earthplate|H|thousandarrows,coil,extremespeed,bulldoze|Impish|252,252,,,4,|||||]|dragonite|lifeorb|H|extremespeed,outrage,icepunch,dragondance|Jolly|4,252,,,,252|M||||',

    '|gliscor|toxicorb|H|earthquake,toxic,substitute,protect|Jolly|252,156,,,100,|M||||]|tapulele|focussash||moonblast,psychic,calmmind,shadowball|Timid|4,,,252,,252||,0,,,,|||]|gyarados|sitrusberry||waterfall,icefang,stoneedge,dragondance|Adamant|156,252,,,,100|M||||',

]

vgcTeams = [

    '|salazzle|focussash||protect,flamethrower,sludgebomb,fakeout|Timid|,,,252,,252||||50|]|kyogre|choicescarf||waterspout,originpulse,scald,icebeam|Modest|4,,,252,,252||,0,,,,||50|]|tapulele|lifeorb||psychic,moonblast,dazzlinggleam,protect|Modest|4,,,252,,252||,0,,,,||50|]|incineroar|figyberry|H|flareblitz,knockoff,uturn,fakeout|Adamant|236,4,4,,236,28|M|||50|]|lunala|spookyplate||moongeistbeam,psyshock,tailwind,protect|Timid|4,,,252,,252||,0,,,,||50|]|toxicroak|assaultvest|1|poisonjab,lowkick,fakeout,feint|Adamant|148,108,4,,244,4|F|||50|',

]

#1v1 teams in packed format
ovoTeams = [
    '|mimikyu|mimikiumz||willowisp,playrough,swordsdance,shadowsneak|Jolly|240,128,96,,,44|||||]|zygarde|groundiumz|H|thousandarrows,coil,substitute,rockslide|Impish|248,12,248,,,|||||]|volcarona|buginiumz|H|bugbuzz,quiverdance,substitute,overheat|Timid|,,52,224,,232||,0,,,,|||',

    '|naganadel|choicespecs||sludgewave,dracometeor,hiddenpowergrass,fireblast|Timid|56,,,188,64,200||,0,,,,|||]|zygarde|groundiumz|H|coil,substitute,bulldoze,thousandarrows|Impish|252,,220,,,36|||||]|magearna|fairiumz||calmmind,painsplit,irondefense,fleurcannon|Modest|224,,160,,,124||,0,,,,|||',

    '|pyukumuku|psychiumz|H|lightscreen,recover,soak,toxic|Sassy|252,,4,,252,||,0,,,,0|||]|charizard|charizarditex||flamecharge,outrage,flareblitz,swordsdance|Jolly|64,152,40,,,252|||||]|mew|keeberry||taunt,willowisp,roost,amnesia|Timid|252,,36,,,220||,0,,,,|||',

    '|tapulele|psychiumz||psychic,calmmind,reflect,moonblast|Calm|252,,60,,196,||,0,,,,|||]|charizard|charizarditex||willowisp,flamecharge,flareblitz,outrage|Jolly|252,,,,160,96|||||]|pheromosa|fightiniumz||bugbuzz,icebeam,focusblast,lunge|Modest|,,160,188,,160|||||',

    '|charmander|lifeorb||flareblitz,brickbreak,dragondance,outrage|Adamant|,252,,,4,252|M||||]|bulbasaur|chestoberry||gigadrain,toxic,sludgebomb,rest|Quiet|252,4,,252,,|M|,0,,,,|||]|squirtle|leftovers||fakeout,aquajet,hydropump,icebeam|Quiet|252,4,,252,,|M||||',
]

#please don't use a stall team
singlesTeams = [
    '|azelf|focussash||stealthrock,taunt,explosion,flamethrower|Jolly|,252,,4,,252|||||]|crawdaunt|focussash|H|swordsdance,knockoff,crabhammer,aquajet|Adamant|,252,,,4,252|||||]|mamoswine|focussash|H|endeavor,earthquake,iceshard,iciclecrash|Jolly|,252,,,4,252|||||]|starmie|electriumz|H|hydropump,thunder,rapidspin,icebeam|Timid|,,,252,4,252||,0,,,,|||]|scizor|ironplate|1|swordsdance,bulletpunch,knockoff,superpower|Adamant|,252,4,,,252|||||]|manectric|manectite|1|voltswitch,flamethrower,signalbeam,hiddenpowergrass|Timid|,,,252,4,252||,0,,,,|||',

    'crossy u lossy|heracross|flameorb|1|closecombat,knockoff,facade,swordsdance|Jolly|,252,,,4,252|||||]chuggy buggy|scizor|choiceband|1|bulletpunch,uturn,superpower,pursuit|Adamant|112,252,,,,144|||||]woofy woof|manectric|manectite|1|thunderbolt,voltswitch,flamethrower,hiddenpowerice|Timid|,,,252,4,252||,0,,,,|||]batzywatzy|crobat|flyiniumz|H|bravebird,defog,roost,uturn|Jolly|,252,,,4,252|||||]soggy froggy|seismitoad|leftovers|H|stealthrock,scald,earthpower,toxic|Bold|244,,252,,,12||,0,,,,|||]bitchy sissy|latias|choicescarf||dracometeor,psychic,trick,healingwish|Timid|,,,252,4,252||,0,,,,|||',
]

#restricted 2v2 doubles, with teams of 2 mons
tvtTeams = [
    '|kyogre|choicescarf||waterspout,scald,thunder,icebeam|Modest|4,,,252,,252||,0,,,,|||]|tapulele|lifeorb||protect,psychic,moonblast,allyswitch|Timid|36,,,252,,220||,0,,,,|||',

    'I hate anime|tapufini|choicescarf||muddywater,dazzlinggleam,haze,icebeam|Modest|12,,,252,,244||,0,,,,||50|]Anime is life|salazzle|focussash||fakeout,sludgebomb,flamethrower,protect|Timid|4,,,252,,252||||50|',

    'can\'t trust others|garchomp|groundiumz|H|earthquake,rockslide,substitute,protect|Adamant|12,156,4,,116,220|M|||50|]dirty dan|mukalola|aguavberry|1|knockoff,poisonjab,shadowsneak,protect|Adamant|188,244,44,,20,12|M|||50|',

    '|venusaur|focussash|H|protect,sludgebomb,grassknot,sleeppowder|Modest|4,,,252,,252|M|,0,,,,||50|]|groudon|figyberry||precipiceblades,rockslide,swordsdance,protect|Jolly|116,252,,,,140||||50|',

    '|lunala|spookyplate||moongeistbeam,psyshock,psychup,protect|Timid|4,,,252,,252||,0,,,,||50|]|incineroar|figyberry|H|flareblitz,knockoff,uturn,fakeout|Adamant|236,4,4,,236,28|M|||50|',

    '|kartana|assaultvest||leafblade,smartstrike,sacredsword,nightslash|Jolly|204,4,4,,84,212||||50|]|tapukoko|choicespecs||thunderbolt,dazzlinggleam,discharge,voltswitch|Timid|140,,36,204,28,100||,0,,,,||50|',

    '|tapulele|choicespecs||thunderbolt,psychic,moonblast,dazzlinggleam|Modest|252,,,252,,||,0,,,,||50|]|kartana|focussash||detect,leafblade,sacredsword,smartstrike|Jolly|,252,,,4,252||||50|'
]


#location of the modified ps executable
PS_PATH = '/home/sam/builds/Pokemon-Showdown/pokemon-showdown'
PS_ARG = 'simulate-battle'

async def playRandomGame(teams, format, ps=None):
    if not ps:
        ps = await getPSProcess()
    seed = [
        random.random() * 0x10000,
        random.random() * 0x10000,
        random.random() * 0x10000,
        random.random() * 0x10000,
    ]

    game = Game(ps, format=format, teams=teams, seed=[0,0,0,0], verbose=True)

    async def randomAgent(queue, cmdHeader):
        while True:
            req = await queue.get()
            if req[0] == Game.END:
                break

            print('getting actions')
            actions = moves.getMoves(format, req[1])
            state = req[1]['state']
            print(cmdHeader, 'actions', actions)

            action = random.choice(actions)
            print(cmdHeader, 'picked', action)
            await game.cmdQueue.put(cmdHeader + action)

    await game.startGame()
    gameTask = asyncio.gather(randomAgent(game.p1Queue, '>p1'),
            randomAgent(game.p2Queue, '>p2'))
    asyncio.ensure_future(gameTask)
    winner = await game.winner
    gameTask.cancel()
    print('winner:', winner)
    return winner


#plays two separately trained agents
#I just copied and pasted playTestGame and duplicated all the search functions
#so expect this to take twice as long as playTestGame with the same parameters
async def playCompGame(teams, limit1=100, limit2=100, format='1v1', numProcesses1=1, numProcesses2=1, file=sys.stdout, initMoves=([],[]), valueModel1=None, valueModel2=None):
    try:

        mainPs = await getPSProcess()

        searchPs1 = [await getPSProcess() for i in range(numProcesses1)]
        searchPs2 = [await getPSProcess() for i in range(numProcesses2)]

        seed = [
            random.random() * 0x10000,
            random.random() * 0x10000,
            random.random() * 0x10000,
            random.random() * 0x10000,
        ]

        game = Game(mainPs, format=format, teams=teams, seed=seed, verbose=True, file=file)

        await game.startGame()

        mcSearch1 = rm.mcSearchRM
        getProbs1 = rm.getProbsRM
        combineData1 = rm.combineRMData

        #mcSearch2 = rm.mcSearchRM
        #getProbs2 = rm.getProbsRM
        #combineData2 = rm.combineRMData

        mcSearch2 = exp3.mcSearchExp3
        getProbs2 = exp3.getProbsExp3
        combineData2 = exp3.combineExp3Data


        if not valueModel1:
            valueModel1 = model.BasicModel()
        if not valueModel2:
            valueModel2 = model.BasicModel()

        #holds the montecarlo data
        #each entry goes to one process
        #this will get really big with n=3 after 20ish turns if you
        #don't purge old data
        mcDatasets1 = []
        mcDatasets2 = []

        #likelihood of the search agent picking random moves
        #decreases exponentially as the search goes on
        def gamma1(iter):
            #return 1 / 2 ** (1 + 10 * iter / limit1)
            return 0.3
        def gamma2(iter):
            #return 1 / 2 ** (1 + 10 * iter / limit2)
            return 0.3
        mcDatasets1 = [{
            'gamma': gamma1,
            'getExpValue': valueModel1.getExpValue,
            'addReward': valueModel1.addReward,
        }, {
            'gamma': gamma1,
            'getExpValue': valueModel1.getExpValue,
            'addReward': valueModel1.addReward,
        }]
        mcDatasets2 = [{
            'gamma': gamma2,
            'getExpValue': valueModel2.getExpValue,
            'addReward': valueModel2.addReward,
        }, {
            'gamma': gamma2,
            'getExpValue': valueModel2.getExpValue,
            'addReward': valueModel2.addReward,
        }]

        #moves with probabilites below this are not considered
        probCutoff = 0.03

        #this needs to be a coroutine so we can cancel it when the game ends
        #which due to concurrency issues might not be until we get into the MCTS loop
        async def play():
            i = 0
            #actions taken so far by in the actual game
            p1Actions = []
            p2Actions = []
            #we reassign this later, so we have to declare it nonlocal
            nonlocal mcDatasets1
            nonlocal mcDatasets2
            while True:
                i += 1
                print('starting turn', i, file=sys.stderr)

                #don't search if we aren't going to use the results
                if len(initMoves[0]) == 0 or len(initMoves[1]) == 0:
                    #I suspect that averaging two runs together will
                    #give us more improvement than running for twice as long
                    #and it should run faster than a single long search due to parallelism

                    searches1 = []
                    searches2 = []
                    for j in range(numProcesses1):
                        search1 = mcSearch1(
                                searchPs1[j],
                                format,
                                teams,
                                limit=limit1,
                                seed=seed,
                                p1InitActions=p1Actions,
                                p2InitActions=p2Actions,
                                mcData=mcDatasets1,
                                pid=j,
                                posReg=True,
                                initExpVal=0,
                                probScaling=2,
                                regScaling=1.5)
                        searches1.append(search1)

                    for j in range(numProcesses2):
                        search2 = mcSearch2(
                                searchPs2[j],
                                format,
                                teams,
                                limit=limit2,
                                seed=seed,
                                p1InitActions=p1Actions,
                                p2InitActions=p2Actions,
                                mcData=mcDatasets2)#,
                                #pid=j,
                                #posReg=True,
                                #initExpVal=0.5,
                                #probScaling=2,
                                #regScaling=1.5)
                        searches2.append(search2)



                    await asyncio.gather(*searches1)
                    await asyncio.gather(*searches2)
                    #await asyncio.gather(*searches1, *searches2)

                    #combine the processes results together, purge unused information
                    #this assumes that any state that isn't seen in two consecutive iterations isn't worth keeping
                    #it also takes a little bit of processing but that should be okay
                    print('combining', file=sys.stderr)

                    mcDatasets1 = combineData1([mcDatasets1], valueModel1)[0]
                    mcDatasets2 = combineData2([mcDatasets2], valueModel2)[0]

                #this assumes that both player1 and player2 get requests each turn
                #which I think is accurate, but most formats will give one player a waiting request
                #this will lock up if a player causes an error, so don't do that

                #TODO this signature is ugly, reorganize it so we can just pass an index
                async def playTurn(queue, myMcData, actionList, cmdHeader, initMoves, getProbs):

                    request = await queue.get()

                    if len(initMoves) > 0:
                        action = initMoves[0]
                        del initMoves[0]
                        print('|c|' + cmdHeader + '|Turn ' + str(i) + ' pre-set action:', action, file=file)
                    else:
                        #figure out what kind of action we need
                        state = request[1]['stateHash']
                        actions = moves.getMoves(format, request[1])

                        #the mcdatasets are all combined, so we can just look at the first
                        data = myMcData[0]
                        probs = getProbs(data, state, actions)
                        normProbs = np.array([p if p > probCutoff else 0 for p in probs])
                        normProbs = normProbs / np.sum(normProbs)

                        for j in range(len(actions)):
                            if normProbs[j] > 0:
                                print('|c|' + cmdHeader + '|Turn ' + str(i) + ' action:', actions[j],
                                        'prob:', '%.1f%%' % (normProbs[j] * 100), file=file)

                        action = np.random.choice(actions, p=normProbs)

                    actionList.append(action)
                    await game.cmdQueue.put(cmdHeader + action)

                #await playTurn(game.p1Queue, [data[0] for data in mcDatasets1], p1Actions, '>p1', initMoves[0], getProbs1)
                #await playTurn(game.p2Queue, [data[1] for data in mcDatasets2], p2Actions, '>p2', initMoves[1], getProbs2)
                await playTurn(game.p1Queue, [mcDatasets1[0]], p1Actions, '>p1', initMoves[0], getProbs1)
                await playTurn(game.p2Queue, [mcDatasets2[1]], p2Actions, '>p2', initMoves[1], getProbs2)

        gameTask = asyncio.ensure_future(play())
        winner = await game.winner
        gameTask.cancel()
        print('winner:', winner, file=sys.stderr)
        return winner

    except Exception as e:
        print(e, file=sys.stderr)

    finally:
        mainPs.terminate()
        for ps in searchPs1:
            ps.terminate()
        for ps in searchPs2:
            ps.terminate()


#trains a model for the given format with the given teams
#returns the trained model
async def trainModel(teams, format, games=100, epochs=100, valueModel=None):
    try:
        searchPs = await getPSProcess()

        if not valueModel:
            valueModel = model.TrainedModel(alpha=0.0001)

        def getExpValue(*args):
            return valueModel.getExpValue(*args)
        def addReward(*args):
            return valueModel.addReward(*args)

        def gamma(iter):
            return 0.3

        mcData = [{
            'gamma': gamma,
            'getExpValue': valueModel.getExpValue,
            'addReward': addReward,
        }, {
            'gamma': gamma,
            'getExpValue': valueModel.getExpValue,
            'addReward': addReward,
        }]


        print('starting network training', file=sys.stderr)
        for i in range(epochs):
            print('epoch', i, 'running', file=sys.stderr)
            valueModel.t = i / epochs
            await rm.mcSearchRM(
                    searchPs,
                    format,
                    teams,
                    limit=games,
                    #seed=seed,
                    #p1InitActions=p1Actions,
                    #p2InitActions=p2Actions,
                    mcData=mcData,
                    initExpVal=0,
                    probScaling=2,
                    regScaling=1.5)

            print('epoch', i, 'training', file=sys.stderr)
            valueModel.train(epochs=10)

    except:
        raise

    finally:
        searchPs.terminate()
    return valueModel


async def playTestGame(teams, limit=100, format='1v1', numProcesses=1, valueModel=None, file=sys.stdout, initMoves=([],[])):
    try:

        mainPs = await getPSProcess()

        searchPs = [await getPSProcess() for i in range(numProcesses)]

        seed = [
            random.random() * 0x10000,
            random.random() * 0x10000,
            random.random() * 0x10000,
            random.random() * 0x10000,
        ]

        game = Game(mainPs, format=format, teams=teams, seed=seed, verbose=True, file=file)



        #holds the montecarlo data
        #each entry goes to one process
        #this will get really big with n=3 after 20ish turns if you
        #don't purge old data
        #mcDatasets = []

        def gamma(iter):
            return 0.3

        if not valueModel:
            valueModel = model.BasicModel()

        #for i in range(numProcesses):
            #mcDatasets.append([{
        mcDataset = [{
            'gamma': gamma,
            'getExpValue': valueModel.getExpValue,
            'addReward': valueModel.addReward,
        }, {
            'gamma': gamma,
            'getExpValue': valueModel.getExpValue,
            'addReward': valueModel.addReward,
        }]


        #moves with probabilites below this are not considered
        probCutoff = 0.03

        await game.startGame()

        #this needs to be a coroutine so we can cancel it when the game ends
        #which due to concurrency issues might not be until we get into the MCTS loop
        async def play():
            i = 0
            #actions taken so far by in the actual game
            p1Actions = []
            p2Actions = []
            #we reassign this later, so we have to declare it nonlocal
            nonlocal mcDataset
            while True:
                i += 1
                print('starting turn', i, file=sys.stderr)

                #don't search if we aren't going to use the results
                if len(initMoves[0]) == 0 or len(initMoves[1]) == 0:
                    #I suspect that averaging two runs together will
                    #give us more improvement than running for twice as long
                    #and it should run faster than a single long search due to parallelism

                    searches = []
                    for j in range(numProcesses):
                        #search = exp3.mcSearchExp3(
                        search = rm.mcSearchRM(
                                searchPs[j],
                                format,
                                teams,
                                limit=limit,
                                seed=seed,
                                p1InitActions=p1Actions,
                                p2InitActions=p2Actions,
                                mcData=mcDataset,
                                pid=j,
                                initExpVal=0,
                                probScaling=2,
                                regScaling=1.5,
                                verbose=False)
                        searches.append(search)


                    await asyncio.gather(*searches)

                    #combine the processes results together, purge unused information
                    #this assumes that any state that isn't seen in two consecutive iterations isn't worth keeping
                    #it also takes a little bit of processing but that should be okay
                    print('combining', file=sys.stderr)
                    #mcDatasets = exp3.combineExp3Data(mcDatasets)
                    mcDataset = rm.combineRMData([mcDataset], valueModel)[0]

                #this assumes that both player1 and player2 get requests each turn
                #which I think is accurate, but most formats will give one player a waiting request
                #this will lock up if a player causes an error, so don't do that

                async def playTurn(queue, myMcData, actionList, cmdHeader, initMoves):

                    request = await queue.get()

                    if len(initMoves) > 0:
                        action = initMoves[0]
                        del initMoves[0]
                        print('|c|' + cmdHeader + '|Turn ' + str(i) + ' pre-set action:', action, file=file)
                    else:
                        #figure out what kind of action we need
                        state = request[1]['stateHash']
                        actions = moves.getMoves(format, request[1])

                        #the mcdatasets are all combined, so we can just look at the first
                        data = myMcData[0]
                        #probs = exp3.getProbsExp3(data, state, actions)
                        probs = rm.getProbsRM(data, state, actions)
                        #remove low probability moves, likely just noise
                        #this can remove every action, but if that's the case then it's doesn't really matter
                        #as all the probabilites are low
                        normProbs = np.array([p if p > probCutoff else 0 for p in probs])
                        normProbs = normProbs / np.sum(normProbs)

                        for j in range(len(actions)):
                            actionString = moves.prettyPrintMove(actions[j], request[1])
                            if normProbs[j] > 0:
                                print('|c|' + cmdHeader + '|Turn ' + str(i) + ' action:', actionString,
                                        'prob:', '%.1f%%' % (normProbs[j] * 100), file=file)

                        action = np.random.choice(actions, p=normProbs)

                    actionList.append(action)
                    await game.cmdQueue.put(cmdHeader + action)

                #await playTurn(game.p1Queue, [data[0] for data in mcDatasets], p1Actions, '>p1', initMoves[0])
                #await playTurn(game.p2Queue, [data[1] for data in mcDatasets], p2Actions, '>p2', initMoves[1])
                await playTurn(game.p1Queue, [mcDataset[0]], p1Actions, '>p1', initMoves[0])
                await playTurn(game.p2Queue, [mcDataset[1]], p2Actions, '>p2', initMoves[1])


        gameTask = asyncio.ensure_future(play())
        winner = await game.winner
        gameTask.cancel()
        print('winner:', winner, file=sys.stderr)

    except:
        raise

    finally:
        mainPs.terminate()
        for ps in searchPs:
            ps.terminate()


async def getPSProcess():
    return await asyncio.create_subprocess_exec(PS_PATH, PS_ARG,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE)

async def main():
    format = '1v1'
    #format = '2v2doubles'
    #format='singles'
    #format='vgc'

    #teams = (singlesTeams[0], singlesTeams[1])
    #gen 1 starters mirror
    teams = (ovoTeams[4], ovoTeams[4])

    #groudon vs lunala vgv19
    #teams = (tvtTeams[3], tvtTeams[4])
    #fini vs koko vgc17
    #teams = (tvtTeams[1], tvtTeams[5])

    #vgc19 scarf kyogre mirror
    #teams = (vgcTeams[0], vgcTeams[0])

    #lunala mirror
    #teams = (tvtTeams[4], tvtTeams[4])

    #salazzle/fini vs lele/kartana singles
    #teams = (tvtTeams[1], tvtTeams[6])
    #initMoves = ([' team 21'], [' team 12'])

    #initMoves = ([' team 12'], [' team 12'])
    #initMoves = ([' team 1'], [' team 1'])
    initMoves = ([], [])

    """
    ps = await getPSProcess()
    try:
        await playRandomGame(teams, format=format, ps=ps)
    finally:
        ps.terminate()
    """


    trainedModel = model.TrainedModel(alpha=0.0001)
    #valueModel = model.BasicModel()
    #valueModel = model.CombinedModel(trainedModel, basicModel)
    #await trainModel(teams=teams, format=format, games=100, epochs=100, valueModel=trainedModel)
    trainedModel.training = False
    #valueModel.compare = True
    #valueModel.t = 1
    #await humanGame(humanTeams, format='1v1', limit=300)
    #await playTestGame(teams, format=format, limit=3000, numProcesses=3, initMoves=initMoves)

    limit1 = 100
    numProcesses1 = 1
    limit2 = 300
    numProcesses2 = 1
    bot1Wins = 0
    bot2Wins = 0
    for i in range(200):
        valueModel1 = model.BasicModel()
        #valueModel2 = trainedModel
        valueModel2 = model.BasicModel()
        with open(os.devnull, 'w') as devnull:
            result = await playCompGame(teams, format=format, limit1=limit1, limit2=limit2, numProcesses1=numProcesses1, numProcesses2=numProcesses2, initMoves=initMoves, valueModel1=valueModel1, valueModel2=valueModel2, file=devnull)
        if result == 'bot1':
            bot1Wins += 1
        elif result == 'bot2':
            bot2Wins += 1
        print('bot1Wins', bot1Wins, 'bot2Wins', bot2Wins)

    """
    i = 0
    while True:
        limit = 1000 * 2 ** i
        print('starting game with limit', limit, file=sys.stderr)
        with open('iterout' + str(i) + '.txt', 'w') as file:
            await playTestGame(teams, format='2v2doubles', limit=limit, valueModel=valueModel, numProcesses=1, initMoves=initMoves, file=file)
        i += 1
    """

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
