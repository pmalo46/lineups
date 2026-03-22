"""
engine.py
Fantasy baseball two-team simulation engine.

Extracted from team_lineup_two_team_game.ipynb with no logic changes.
"""

import copy
from collections import deque


# ---------------------------------------------------------------------------
# Team template helpers
# ---------------------------------------------------------------------------

def empty_team_template():
    """Return a blank team roster structure."""
    return {
        'C':  {'id': '', 'name': '', 'lineup_slot': ''},
        '1B': {'id': '', 'name': '', 'lineup_slot': ''},
        '2B': {'id': '', 'name': '', 'lineup_slot': ''},
        '3B': {'id': '', 'name': '', 'lineup_slot': ''},
        'SS': {'id': '', 'name': '', 'lineup_slot': ''},
        'OF': [{'id': '', 'name': '', 'lineup_slot': ''} for _ in range(3)],
        'DH': {'id': '', 'name': '', 'lineup_slot': ''},
        'PH': [{'id': '', 'name': '', 'lineup_slot': '', 'bench_order': ''} for _ in range(6)],
    }


def get_selected_ids(selected_players):
    """Return the set of player IDs currently on a roster."""
    ids = set()
    for pos in ['C', '1B', '2B', '3B', 'SS', 'DH']:
        if selected_players[pos].get('id'):
            ids.add(selected_players[pos]['id'])
    for player in selected_players['OF']:
        if player.get('id'):
            ids.add(player['id'])
    for player in selected_players['PH']:
        if player.get('id'):
            ids.add(player['id'])
    return ids


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_team_setup(selected_players):
    starter_slots = []
    names = []
    ids = []

    for pos in ['C', '1B', '2B', '3B', 'SS', 'DH']:
        player = selected_players[pos]
        if not player.get('id') or not player.get('lineup_slot'):
            return False, f'Missing starter selection or lineup slot at {pos}.'
        starter_slots.append(player['lineup_slot'])
        names.append(player['name'])
        ids.append(player['id'])

    for idx, player in enumerate(selected_players['OF'], start=1):
        if not player.get('id') or not player.get('lineup_slot'):
            return False, f'Missing OF{idx} selection or lineup slot.'
        starter_slots.append(player['lineup_slot'])
        names.append(player['name'])
        ids.append(player['id'])

    if sorted(starter_slots) != list(range(1, 10)):
        return False, 'Lineup slots must be exactly 1-9 with no duplicates.'

    ph_names = [p['name'] for p in selected_players['PH'] if p.get('id')]
    ph_ids = [p['id'] for p in selected_players['PH'] if p.get('id')]
    names.extend(ph_names)
    ids.extend(ph_ids)

    if len(names) != len(set(names)):
        return False, 'Duplicate player found within the team roster.'
    if len(ids) != len(set(ids)):
        return False, 'Duplicate player IDs found within the team roster.'

    return True, 'OK'


def validate_head_to_head_setup(away, home):
    ok, msg = validate_team_setup(away)
    if not ok:
        return False, f'Away setup invalid: {msg}'

    ok, msg = validate_team_setup(home)
    if not ok:
        return False, f'Home setup invalid: {msg}'

    overlap = get_selected_ids(away).intersection(get_selected_ids(home))
    if overlap:
        return False, 'The same player appears on both rosters.'

    return True, 'OK'


# ---------------------------------------------------------------------------
# Lineup helpers
# ---------------------------------------------------------------------------

def build_lineup_and_bench(selected_players):
    starters = []
    for pos in ['C', '1B', '2B', '3B', 'SS', 'DH']:
        player = selected_players[pos]
        if player.get('lineup_slot'):
            starters.append((pos, copy.deepcopy(player)))
    for player in selected_players['OF']:
        if player.get('lineup_slot'):
            starters.append(('OF', copy.deepcopy(player)))

    starters = deque(sorted(starters, key=lambda item: item[1]['lineup_slot']))
    ph = deque(sorted(
        [copy.deepcopy(p) for p in selected_players['PH'] if p.get('id')],
        key=lambda item: item['bench_order'],
    ))
    return starters, ph


def summarize_team_roster(selected_players):
    starters = []
    for pos in ['C', '1B', '2B', '3B', 'SS', 'DH']:
        starters.append(selected_players[pos])
    starters.extend(selected_players['OF'])
    starters = sorted(starters, key=lambda p: p['lineup_slot'])

    return {
        'batting_order': [p['name'] for p in starters],
        'batting_order_text': ', '.join(p['name'] for p in starters),
        'bench_text': ', '.join(
            p['name']
            for p in sorted(selected_players['PH'], key=lambda p: p.get('bench_order', 999))
            if p.get('id')
        ),
    }


def build_player_play_map(df):
    player_play_map = {}
    for player_id, group in df.groupby('player_id', sort=False):
        first_game = group['game_id'].iloc[0]
        player_rows = group[group['game_id'] == first_game].sort_values('sequence_number')
        player_play_map[player_id] = player_rows.to_dict(orient='records')
    return player_play_map


# ---------------------------------------------------------------------------
# Game state machine
# ---------------------------------------------------------------------------

class FantasyGameTwoTeam:
    def __init__(self, verbose=True):
        self.inning = 1
        self.half = 'top'
        self.outs = 0
        self.bases = {'1B': None, '2B': None, '3B': None}
        self.score = {'away': 0, 'home': 0}
        self.batting_team = 'away'
        self.fielding_team = 'home'
        self.current_batter = None
        self.game_over = False
        self.log = []
        self.verbose = verbose
        self.termination_reason = None
        self.team_exhausted = {'away': False, 'home': False}
        self.team_stats = {
            'away': {'sac_flies': 0, 'double_plays': 0, 'hits': 0, 'errors': 0, 'stranded_2b': 0, 'stranded_3b': 0},
            'home': {'sac_flies': 0, 'double_plays': 0, 'hits': 0, 'errors': 0, 'stranded_2b': 0, 'stranded_3b': 0},
        }

    def team_label(self, team_key=None):
        team_key = team_key or self.batting_team
        return 'Away' if team_key == 'away' else 'Home'

    def record(self, message):
        if self.verbose:
            print(message)
        self.log.append(message)

    def format_bases(self):
        return {
            base: runner['name'] if runner is not None else None
            for base, runner in self.bases.items()
        }

    def print_state(self):
        self.record(
            f"Score: Away {self.score['away']}, Home {self.score['home']} "
            f"| Outs: {self.outs} | Bases: {self.format_bases()}"
        )

    def start_half(self):
        self.record(f"{self.half.title()} {self.inning} - {self.team_label()} batting")

    def score_runner(self, runner_name):
        self.score[self.batting_team] += 1
        self.record(f"{self.team_label()} scores: {runner_name}")

    # -- Hits ---------------------------------------------------------------

    def hit(self, bases_advanced, action_text):
        batter_name = self.current_batter['name']
        self.team_stats[self.batting_team]['hits'] += 1
        self.record(f"{self.team_label()} | {batter_name} {action_text}.")

        if bases_advanced == 1 and self.bases['2B']:
            runner = self.bases['2B']
            self.bases['2B'] = None
            self.score_runner(runner['name'])

        if bases_advanced == 2 and self.bases['1B']:
            runner = self.bases['1B']
            self.bases['1B'] = None
            self.score_runner(runner['name'])

        runs_scored = []
        for base in reversed(range(1, 4)):
            runner = self.bases[f'{base}B']
            if runner is not None:
                new_base = base + bases_advanced
                if new_base > 3:
                    runs_scored.append(runner['name'])
                else:
                    self.bases[f'{new_base}B'] = runner
                self.bases[f'{base}B'] = None

        for runner_name in runs_scored:
            self.score_runner(runner_name)

        if bases_advanced > 3:
            self.score_runner(batter_name)
        else:
            self.bases[f'{bases_advanced}B'] = self.current_batter

    # -- Walk ---------------------------------------------------------------

    def walk(self):
        batter_name = self.current_batter['name']
        self.record(f"{self.team_label()} | {batter_name} walks.")

        if self.bases['1B'] and self.bases['2B'] and self.bases['3B']:
            self.score_runner(self.bases['3B']['name'])
            self.bases['3B'] = self.bases['2B']
            self.bases['2B'] = self.bases['1B']
        elif self.bases['1B'] and self.bases['2B']:
            self.bases['3B'] = self.bases['2B']
            self.bases['2B'] = self.bases['1B']
        elif self.bases['1B']:
            self.bases['2B'] = self.bases['1B']

        self.bases['1B'] = self.current_batter

    # -- Half-inning transitions --------------------------------------------

    def advance_half(self):
        just_finished = f"{self.half.title()} {self.inning}"
        stranded = []
        if self.bases['2B']:
            self.team_stats[self.batting_team]['stranded_2b'] += 1
            stranded.append(f"2B: {self.bases['2B']['name']}")
        if self.bases['3B']:
            self.team_stats[self.batting_team]['stranded_3b'] += 1
            stranded.append(f"3B: {self.bases['3B']['name']}")
        if stranded:
            self.record(f"{self.team_label()} strands runners at " + ', '.join(stranded) + '.')
        self.record(f"End {just_finished}")
        self.bases = {'1B': None, '2B': None, '3B': None}
        self.outs = 0

        if self.half == 'top':
            self.half = 'bottom'
            self.batting_team = 'home'
            self.fielding_team = 'away'
            self.start_half()
            return

        if self.inning >= 9:
            self.game_over = True
            self.termination_reason = 'completed_9'
            return

        self.inning += 1
        self.half = 'top'
        self.batting_team = 'away'
        self.fielding_team = 'home'
        self.start_half()

    # -- Outs ---------------------------------------------------------------

    def describe_regular_out(self, result_raw, out_kind):
        batter_name = self.current_batter['name']
        result = (result_raw or '').strip().lower()
        if 'strikeout' in result:
            return f"{self.team_label()} | {batter_name} strikes out."
        if 'lineout' in result:
            return f"{self.team_label()} | {batter_name} lines out."
        if 'pop out' in result:
            return f"{self.team_label()} | {batter_name} pops out."
        if 'fly' in result or out_kind == 'fly':
            return f"{self.team_label()} | {batter_name} flies out."
        if 'ground' in result or 'forceout' in result or 'fielder' in result or out_kind == 'ground':
            return f"{self.team_label()} | {batter_name} grounds out."
        return f"{self.team_label()} | {batter_name} is out."

    def out(self):
        self.outs += 1
        if self.outs >= 3:
            self.print_state()
            self.advance_half()

    def double_play(self):
        batter_name = self.current_batter['name']
        self.team_stats[self.batting_team]['double_plays'] += 1
        if self.bases['1B'] and self.bases['2B'] and self.bases['3B']:
            forced_runner = self.bases['3B']['name']
            self.record(
                f"{self.team_label()} | {batter_name} grounds into double play. "
                f"{forced_runner} is out at home."
            )
            self.bases['3B'] = self.bases['2B']
            self.bases['2B'] = self.bases['1B']
            self.bases['1B'] = None
        else:
            if self.bases['1B']:
                forced_runner = self.bases['1B']['name']
                self.record(
                    f"{self.team_label()} | {batter_name} grounds into double play. "
                    f"{forced_runner} is out at 2B."
                )
                self.bases['1B'] = None
            else:
                self.record(f"{self.team_label()} | {batter_name} grounds into double play.")

            if self.bases['2B']:
                self.bases['3B'] = self.bases['2B']
                self.bases['2B'] = None

        self.out()
        self.out()

    def sac_fly(self):
        batter_name = self.current_batter['name']
        self.team_stats[self.batting_team]['sac_flies'] += 1
        if self.bases['3B'] and self.outs < 2:
            runner_name = self.bases['3B']['name']
            self.record(
                f"{self.team_label()} | {batter_name} flies out, "
                f"{runner_name} tags and scores."
            )
            self.bases['3B'] = None
            self.score_runner(runner_name)
        else:
            self.record(f"{self.team_label()} | {batter_name} flies out.")
        self.out()

    # -- Event dispatch -----------------------------------------------------

    def process_event(self, event_type, result_raw='', out_kind='other'):
        if event_type == 'single':
            self.hit(1, 'singles')
        elif event_type == 'double':
            self.hit(2, 'doubles')
        elif event_type == 'triple':
            self.hit(3, 'triples')
        elif event_type == 'home_run':
            self.hit(4, 'homers')
        elif event_type == 'walk':
            self.walk()
        elif event_type == 'reach_on_error':
            self.team_stats[self.fielding_team]['errors'] += 1
            self.hit(1, 'reaches on error')
        elif event_type == 'out':
            if self.outs < 2 and self.bases['1B'] and out_kind == 'ground':
                self.double_play()
            elif self.outs < 2 and self.bases['3B'] and out_kind == 'fly':
                self.sac_fly()
            else:
                self.record(self.describe_regular_out(result_raw, out_kind))
                self.out()
        else:
            self.record(self.describe_regular_out(result_raw, out_kind))
            self.out()

        if not self.game_over:
            self.print_state()


# ---------------------------------------------------------------------------
# Top-level simulation runner
# ---------------------------------------------------------------------------

def run_two_team_simulation(away_selected, home_selected, plays_df, verbose=False):
    """Run a full head-to-head simulation. Returns a result dict."""
    away_selected = copy.deepcopy(away_selected)
    home_selected = copy.deepcopy(home_selected)

    valid, message = validate_head_to_head_setup(away_selected, home_selected)
    if not valid:
        return {
            'completed_nine': False,
            'termination_reason': 'invalid_setup',
            'final_inning': None,
            'final_half': None,
            'away_score': None,
            'home_score': None,
            'away_sac_flies': 0, 'home_sac_flies': 0,
            'away_double_plays': 0, 'home_double_plays': 0,
            'away_remaining_ph': 0, 'home_remaining_ph': 0,
            'away_hits': 0, 'home_hits': 0,
            'away_errors': 0, 'home_errors': 0,
            'away_stranded_2b': 0, 'home_stranded_2b': 0,
            'away_stranded_3b': 0, 'home_stranded_3b': 0,
            'away_exhausted': False, 'home_exhausted': False,
            'play_log': [],
            'game': None,
            'validation_message': message,
            'away_roster_summary': summarize_team_roster(away_selected) if get_selected_ids(away_selected) else {},
            'home_roster_summary': summarize_team_roster(home_selected) if get_selected_ids(home_selected) else {},
        }

    play_map = build_player_play_map(plays_df)
    away_lineup_queue, away_ph_queue = build_lineup_and_bench(away_selected)
    home_lineup_queue, home_ph_queue = build_lineup_and_bench(home_selected)

    team_state = {
        'away': {'lineup_queue': away_lineup_queue, 'ph_queue': away_ph_queue},
        'home': {'lineup_queue': home_lineup_queue, 'ph_queue': home_ph_queue},
    }

    game = FantasyGameTwoTeam(verbose=verbose)
    game.start_half()

    play_index = {}
    for team_key in ['away', 'home']:
        for _, player in team_state[team_key]['lineup_queue']:
            play_index.setdefault(str(player['id']), 0)
        for player in team_state[team_key]['ph_queue']:
            play_index.setdefault(str(player['id']), 0)

    def mark_team_exhausted(team_key):
        game.team_exhausted[team_key] = True
        game.record(
            f"{game.team_label(team_key)} lineup is exhausted. "
            "Remaining half-innings will be automatic outs."
        )

    def play_automatic_half(team_key):
        game.record(
            f"{game.team_label(team_key)} has no usable batters. "
            "Automatic three-up, three-down."
        )
        while game.outs < 3 and not game.game_over and game.batting_team == team_key:
            game.record(f"{game.team_label(team_key)} | Automatic out.")
            game.out()
            if not game.game_over and game.batting_team == team_key:
                game.print_state()

    try:
        while not game.game_over:
            team_key = game.batting_team
            lineup_queue = team_state[team_key]['lineup_queue']
            ph_queue = team_state[team_key]['ph_queue']

            if game.team_exhausted[team_key]:
                play_automatic_half(team_key)
                continue

            if not lineup_queue:
                mark_team_exhausted(team_key)
                play_automatic_half(team_key)
                continue

            processed_at_bat = 0
            turns = len(lineup_queue)

            for _ in range(turns):
                if game.game_over or game.batting_team != team_key:
                    break

                pos, player_info = lineup_queue.popleft()
                pid = str(player_info['id'])
                batter_plays = play_map.get(pid, [])
                idx = play_index.get(pid, 0)

                if idx >= len(batter_plays):
                    if ph_queue:
                        sub = ph_queue.popleft()
                        game.record(
                            f"{game.team_label(team_key)} | Pinch-hitting  "
                            f"{sub['name']} for {player_info['name']}."
                        )
                        player_info = sub
                        pid = str(player_info['id'])
                        batter_plays = play_map.get(pid, [])
                        idx = play_index.get(pid, 0)
                    else:
                        game.record(
                            f"{game.team_label(team_key)} | {player_info['name']} "
                            "has no remaining at-bats and no PH available."
                        )
                        continue

                if idx < len(batter_plays):
                    play = batter_plays[idx]
                    game.current_batter = player_info
                    game.process_event(
                        play['event_type'],
                        play.get('result_raw', ''),
                        play.get('out_kind', 'other'),
                    )
                    play_index[pid] = idx + 1
                    lineup_queue.append((pos, player_info))
                    processed_at_bat += 1
                else:
                    game.record(
                        f"{game.team_label(team_key)} | {player_info['name']} "
                        "has no usable plays. Skipping."
                    )

            if not game.game_over and game.batting_team == team_key and processed_at_bat == 0:
                mark_team_exhausted(team_key)
                play_automatic_half(team_key)
                continue

        if game.game_over and game.termination_reason is None:
            game.termination_reason = 'completed_9'

    except Exception as exc:
        game.termination_reason = 'error'
        game.record(f'Runtime error: {exc}')

    completed_nine = bool(game.game_over and game.termination_reason == 'completed_9')

    return {
        'completed_nine': completed_nine,
        'termination_reason': game.termination_reason,
        'final_inning': game.inning,
        'final_half': game.half,
        'away_score': game.score['away'],
        'home_score': game.score['home'],
        'away_sac_flies': game.team_stats['away']['sac_flies'],
        'home_sac_flies': game.team_stats['home']['sac_flies'],
        'away_double_plays': game.team_stats['away']['double_plays'],
        'home_double_plays': game.team_stats['home']['double_plays'],
        'away_remaining_ph': len(team_state['away']['ph_queue']),
        'home_remaining_ph': len(team_state['home']['ph_queue']),
        'away_hits': game.team_stats['away']['hits'],
        'home_hits': game.team_stats['home']['hits'],
        'away_errors': game.team_stats['away']['errors'],
        'home_errors': game.team_stats['home']['errors'],
        'away_stranded_2b': game.team_stats['away']['stranded_2b'],
        'home_stranded_2b': game.team_stats['home']['stranded_2b'],
        'away_stranded_3b': game.team_stats['away']['stranded_3b'],
        'home_stranded_3b': game.team_stats['home']['stranded_3b'],
        'away_exhausted': game.team_exhausted['away'],
        'home_exhausted': game.team_exhausted['home'],
        'play_log': game.log,
        'game': game,
        'validation_message': message,
        'away_roster_summary': summarize_team_roster(away_selected),
        'home_roster_summary': summarize_team_roster(home_selected),
    }
