"""
data_loader.py
Loads and normalizes the static JSON data files used by the Lineups engine.
"""

import json
import pandas as pd


def map_play_to_event(result_raw, description):
    """Map a raw play-by-play result to a normalized (event_type, out_kind) pair.

    Returns (None, None) for plays that should be filtered out
    (pitching changes, wild pitches, stolen bases, etc.).
    """
    r = (result_raw or '').strip().lower()
    d = (description or '').strip().lower()

    # Filter non-batter events
    if 'pitching change' in d:
        return None, None
    if 'wild pitch' in d:
        return None, None
    if 'steals' in d or 'stolen base' in d:
        return None, None
    if r in {'caught stealing 2b', 'caught stealing home'}:
        return None, None

    # Hits
    if 'home run' in r:
        return 'home_run', None
    if r == 'triple':
        return 'triple', None
    if r == 'double':
        return 'double', None
    if r == 'single':
        return 'single', None

    # Walks / HBP
    if r in {'walk', 'intent walk', 'hit by pitch'}:
        return 'walk', None

    # Errors
    if r == 'field error':
        return 'reach_on_error', None

    # Outs by result string
    fly_out_results = {'flyout', 'lineout', 'pop out', 'bunt pop out', 'sac fly'}
    ground_out_results = {
        'groundout', 'bunt groundout', 'forceout', 'grounded into dp',
        'double play', 'strikeout double play', 'fielders choice',
        'fielders choice out', 'sac bunt',
    }

    if r in fly_out_results:
        return 'out', 'fly'
    if r in ground_out_results:
        return 'out', 'ground'
    if r == 'strikeout':
        return 'out', 'other'

    # Fallback: match on description text
    if 'grounds out' in d or "fielder's choice" in d:
        return 'out', 'ground'
    if 'flies out' in d or 'lines out' in d or 'pops out' in d:
        return 'out', 'fly'
    if 'strikes out' in d:
        return 'out', 'other'
    if 'walks' in d or 'intentionally walks' in d or 'hit by pitch' in d:
        return 'walk', None
    if 'homers' in d:
        return 'home_run', None
    if 'triples' in d:
        return 'triple', None
    if 'doubles' in d:
        return 'double', None
    if 'singles' in d:
        return 'single', None

    return 'unknown', 'other'


def normalize_play_by_play(raw_games):
    """Convert raw API play-by-play records into a simulation-ready DataFrame.

    Returns (DataFrame, filtered_count).
    """
    rows = []
    filtered = 0

    for game in raw_games:
        game_id = game.get('gameID')
        plays = game.get('allPlayByPlay') or []
        for idx, play in enumerate(plays, start=1):
            player_id = play.get('playerID')
            if not player_id:
                filtered += 1
                continue

            event_type, out_kind = map_play_to_event(
                play.get('result'), play.get('description')
            )
            if event_type is None:
                filtered += 1
                continue

            rows.append({
                'game_id': game_id,
                'sequence_number': idx,
                'player_id': str(player_id),
                'result_raw': play.get('result'),
                'description': play.get('description'),
                'event_type': event_type,
                'out_kind': out_kind,
                'inning': play.get('inning'),
            })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(['game_id', 'sequence_number']).reset_index(drop=True)
    return df, filtered


def load_data(eligible_path='eligible_players.json',
              play_by_play_path='allPlayByPlay_data.json'):
    """Load and return (gameplay_eligible_players, plays_df).

    ``gameplay_eligible_players`` is the list of player dicts that have at
    least one play in the normalized DataFrame.
    """
    with open(eligible_path, 'r') as f:
        eligible_players = json.load(f)['players']

    with open(play_by_play_path, 'r') as f:
        all_play_by_play = json.load(f)

    plays_df, _filtered = normalize_play_by_play(all_play_by_play)
    playable_ids = set(plays_df['player_id'].astype(str).unique())

    gameplay_eligible = [
        p for p in eligible_players
        if str(p['playerID']) in playable_ids
    ]

    return gameplay_eligible, plays_df
