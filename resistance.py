'''
This program simulates various player stategies for the party game 
  "The Resistance" - http://en.wikipedia.org/wiki/The_Resistance_(party_game)
'''
import collections
import math
import operator
import random

class Player(object):
  def __init__(self, player_id):
    self.id = player_id
    self.failed_missions = 0
    self.successful_missions = 0

  def pick_commandos(self, game, mission):
    '''Returns list of players to be on commandos team for potential mission '''
    raise NotImplementedError

  def vote(self, game, candidate_mission):
    '''Returns 'Pass' or 'Reject' based on players startegy in game'''
    raise NotImplementedError

  def pick_mission_card(self, game, mission):
    '''Returns eiter "Success" or "Fail" based on strategy of player given state 
        of game and current mission.
    '''
    raise NotImplementedError

class ResistencePlayer(Player):
  def player_evaluator(self, player):
    ''' Stategy: pick players with more successes than failures '''
    return player.successful_missions - player.failed_missions *2

  def vote(self, game, candidate_mission):
    your_team = self.pick_commandos(game, candidate_mission)

    their_team_evaluation = sum([ self.player_evaluator(p) for p in candidate_mission.commandos])
    your_team_evaluation = sum([ self.player_evaluator(p) for p in your_team])

    # reject teams that don't meat your strategy
    if your_team_evaluation > their_team_evaluation: 
      return 'Reject'
    
    return 'Pass'

  def pick_commandos(self, game, mission):
    team = [self]
    options = game.players.values()
    options.sort(cmp=lambda p1,p2 : self.player_evaluator(p2) - self.player_evaluator(p1))
    team += options[:mission.num_commandos-1]

    return team

  def pick_mission_card(self, *args, **kwargs): 
    '''Resistance cannot Fail mission'''
    return "Success"

class SpyPlayer(Player):
  def vote(self, game, candidate_mission):
    return 'Pass'

  def pick_commandos(self, game, mission):
    commandos = [self]
    if mission.fails_required > 1:
      for player in game.players.values():
        if isinstance(player, SpyPlayer):
          commandos += [player]

    return commandos

  def pick_mission_card(self, mission):
    num_spies = len([ c for c in mission.commandos if isinstance(c, SpyPlayer) ])

     # if spies can fail mission and win game in doing so, expose identity
    if num_spies > mission.fails_required and mission.spies_can_win_game:
      return "Fail"

    if num_spies > mission.fails_required:
      return "Pass"
    return "Fail"


class Mission(object):
  def __init__(self, game):
    self.spies_can_win_game = game.spy_wins == 2
    self.mission_number = len(game.missions)
    self.num_commandos = game.get_commands_for_mission_number(self.mission_number)

    if self.mission_number == 4 and game.num_players >= 7:
      self.fails_required = 2 
    else:
      self.fails_required = 1

    self.commandos = [] # populated by leader
    self.outcome = None # populated in play
    self.outcome_cards = [] # populated in play

  def play(self):
    for player in self.commandos:
      self.outcome_cards += [player.pick_mission_card(self)]

    if self.outcome_cards.count("Fail") >= self.fails_required:
      self.outcome = "Fail"
    else:
      self.outcome = "Success"

    for player in self.commandos:
      if self.outcome == 'Fail':
        player.failed_missions += 1
      else:
        player.successful_missions += 1

  def __str__(self):
    return self.outcome

class ResistanceGame(object):
  # outer dictionary is missions, inner dictionary is # players
  commandos_per_mission_per_player = {
    0: { 5:2, 6:2, 7:2, 8:3, 9:3, 10:3 },
    1: { 5:3, 6:3, 7:3, 8:4, 9:4, 10:4 },
    2: { 5:2, 6:4, 7:3, 8:4, 9:4, 10:4 },
    3: { 5:3, 6:3, 7:4, 8:5, 9:5, 10:5 },
    4: { 5:3, 6:4, 7:4, 8:5, 9:5, 10:5 },
  }

  def __init__(self, num_players):
    self.num_players = num_players
    self.num_spies = math.ceil(num_players / 3)

    self.players = {}
    for player_id in range(num_players):
      if player_id > self.num_spies:
        self.players[player_id] = ResistencePlayer(player_id)
      else:
        self.players[player_id] = SpyPlayer(player_id)

    self.player_order = range(num_players)
    random.shuffle(self.player_order)

    self.past_votes = []
    self.missions = []
    self.step = 0

  @property
  def spy_wins(self):
    return len([ m for m in self.missions if m.outcome == "Fail"])

  @property
  def resistance_wins(self):
    return len([ m for m in self.missions if m.outcome == "Success"])

  def get_commands_for_mission_number(self, mission_number):
    return self.commandos_per_mission_per_player[mission_number][self.num_players]

  def run(self):
    round = 0
    step = 0
    winner = ""
    while 1:
      # game is over when either side wins 3 missions
      if 3 == self.spy_wins:
        winner = "Spies"
        break
      elif 3 == self.resistance_wins:
        winner = "Resistance"
        break
      else:
        # new leader
        leader_id = self.player_order[round % self.num_players]
        leader = self.players[leader_id]

        # create candidate mission
        mission = Mission(self) 
        mission.commandos = leader.pick_commandos(self, mission)

        if 'Pass' == self.vote(mission, step):
          mission.play()
          self.missions += [ mission ]
          step = 0
        else:
          step += 1

      round += 1
    return winner

  def vote(self, mission, step):
    if step == 5:
      votes = dict([(player.id, "Pass") for player in self.players.values()])
    else:
      votes = dict([(player.id, player.vote(self, mission)) for player in self.players.values()])

    self.past_votes += [votes]
    if votes.values().count("Pass") > votes.values().count("Reject"):
      return "Pass"
    return "Reject"

def main():
  print "Players\t  Resistance Wins\tSpy Wins"
  for num_players in range(5, 11):
    wins = collections.defaultdict(int)
    for n in range(1000):
      game = ResistanceGame(num_players)
      wins[game.run()] += 1
    print "{0!s}\t\t{1!s}\t\t{2!s}".format(num_players, wins.get('Resistance',0), wins.get('Spies',0))

if __name__ == "__main__":
  main()
