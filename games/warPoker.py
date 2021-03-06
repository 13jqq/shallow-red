import asyncio
import copy
import random
import sys

#this is a simple one card poker variant AKA war
#http://www.cs.cmu.edu/~ggordon/poker/

numActions = 4

#don't need a context, so this is empty
class _Context:
    async def __aenter__(self):
        pass
    async def __aexit__(self, *args):
        pass

def getContext():
    return _Context()

def prettyPrintMove(move, req=None):
    return [move]

#our state machine for the game
class _Game():
    START = 0
    #dealing and ante are automatically done
    #p1 needs to bet
    P1_DEAL = 1
    #p1 inital bet of 0
    #p2 can either call or raise
    P2_CHECK = 2
    #p2 raised, p1 can match
    P1_RAISE = 3

    #p1 inital bet of 1
    #p2 can fold or call
    P2_CALL = 4

    #then the game ends
    END = 5

    #all possible actions
    DEAL = 'deal'
    FOLD = 'fold'
    CALL = 'call'
    RAISE = 'raise'
    
    actionDict = {
        P1_DEAL: [CALL, RAISE],#call is actually check but whatever
        P2_CHECK: [CALL, RAISE],
        P1_RAISE: [FOLD, CALL],
        P2_CALL: [FOLD, CALL],
        END: [],
    }

#actions no longer have a set index
#so I'm commenting this out to catch any old code trying to use this
"""
enumActionDict = {
    _Game.DEAL: 0,
    _Game.FOLD: 1,
    _Game.CALL: 2,
    _Game.RAISE: 3,
}
        
def enumAction(action):
    return enumActionDict[action]
"""

def panic():
    print("ERROR THIS SHOULD NEVER HAPPEN", file=sys.stderr)
    quit()

def getSeed():
    return random.random()


class Game:
    def __init__(self, context=None, history=[[],[]], seed=None, saveTrajectories=False, verbose=False, file=sys.stdout):
        self.history = history
        self.seed = seed
        if seed:
            self.random = random.Random(seed)
        else:
            self.random = random.Random()
        self.deck = list(range(2, 15))#offset of 2 because cards start at 2
        self.file = file
        self.saveTrajectories = saveTrajectories

        self.curActions = []

        #this won't get set properly until the history is applied
        self.dealer = 0

        #already anted up
        self.pot = [1, 1]
        self.bet = 0
        self.hands = [0, 0]
        self.state = _Game.START

        loop = asyncio.get_event_loop()
        self.winner = loop.create_future()
        self._winner = None

        if self.saveTrajectories:
            #list of (infoset, action)
            #for each player
            self.prevTrajectories = [[],[]]

        self.verbose = verbose
        self.infosets = [['start'],['start']]

    async def startGame(self):
        #dealer is determined by seed
        self.dealer = self.random.randrange(2)

        self.random.shuffle(self.deck)
        self.hands = [self.deck.pop(), self.deck.pop()]
        for i in range(2):
            self.infosets[i] += ['hand', str(self.hands[i])]

        if self.verbose:
            print('hands', self.hands, file=self.file)

        h = [copy.copy(self.history[0]), copy.copy(self.history[1])]
        while len(h[0]) or len(h[1]):
            player, req, actions = await self.getTurn()
            seed, actionIndex = h[player][0]
            del h[player][0]
            #ignore the seed, as the cards are already set
            await self.takeAction(player, actionIndex)

    async def getTurn(self):
        if self.state == _Game.START:
            self.curActions = [[_Game.DEAL]]
            self.curPlayer = self.dealer
            return (self.dealer, {}, self.curActions)

        if self.state == _Game.END:
            if self._winner == None:
                #only hand is a high card
                self._winner = 0 if self.hands[0] > self.hands[1] else 1

            loser = (self._winner + 1) % 2
            winnings = self.pot[loser]
            if self.verbose:
                print('winner:', self._winner, 'winnings:', '$' + str(winnings), file=self.file)
            self.winner.set_result((self._winner, winnings))
            self.curPlayer = self._winner
            self.curActions = []
            #normalize winnings to between -1 and 1
            return (self._winner, {'win': winnings / 2}, [])

        if self.state in [_Game.P1_DEAL, _Game.P1_RAISE]:
            player = (self.dealer + 1) % 2
        else:
            player = self.dealer

        actions = [[a] for a in _Game.actionDict[self.state]]

        self.curActions = actions
        self.curPlayer = player

        return (player, {}, actions)


    def getInfoset(self, player):
        if player == self.curPlayer:
            infoContext = ['OPTIONS']
            for i, action in enumerate(self.curActions):
                infoContext.append('@' + str(i))
                infoContext += action
            return self.infosets[player] + infoContext
        else:
            return self.infosets[player]

    async def takeAction(self, player, actionIndex):
        action = self.curActions[actionIndex][0]
        if self.verbose:
            print('player', player+1, 'takes action', action, file=self.file)
            print('bet:', self.bet, 'pot', self.pot, file=self.file)
        if self.saveTrajectories:
            self.prevTrajectories[player].append((copy.copy(self.getInfoset(player)), actionIndex, copy.copy(self.curActions)))

        self.curActions = []
        #all actions are public
        for i in range(2):
            #infosets are always in first person
            p = 0 if i == player else 1
            self.infosets[i] += [str(p), action]


        #I could probably simplify this by reducing the number of actions to 2
        #but then we lose some error detection
        if self.state == _Game.START:
            if action == _Game.DEAL:
                self.dealer = player
                self.state = _Game.P1_DEAL
            else:
                panic()
        elif self.state == _Game.P1_DEAL:
            if action == _Game.CALL:
                self.state = _Game.P2_CHECK
            elif action == _Game.RAISE:
                self.bet += 1
                self.pot[player] += self.bet
                self.state = _Game.P2_CALL
            else:
                panic()
        elif self.state == _Game.P2_CHECK:
            if action == _Game.CALL:
                self.state = _Game.END
            elif action == _Game.RAISE:
                self.bet += 1
                self.pot[player] += self.bet
                self.state = _Game.P1_RAISE
            else:
                panic()
        elif self.state == _Game.P1_RAISE:
            if action == _Game.FOLD:
                self.state = _Game.END
                self._winner = (player + 1) % 2
            elif action == _Game.CALL:
                self.pot[player] += self.bet
                self.state = _Game.END
            else:
                panic()
        elif self.state == _Game.P2_CALL:
            if action == _Game.FOLD:
                self.state = _Game.END
                self._winner = (player + 1) % 2
            elif action == _Game.CALL:
                self.pot[player] += self.bet
                self.state = _Game.END
            else:
                panic()
        else:
            panic()

