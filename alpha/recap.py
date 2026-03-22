"""
recap.py
Game recap generation — local fallback and optional AI-powered version.
"""

import os


def extract_scoring_summary(play_log):
    """Pull out scoring half-innings from the play log."""
    innings = []
    current_half = None
    current_events = []

    for line in play_log:
        if line.startswith('Top ') or line.startswith('Bottom '):
            if current_half is not None:
                innings.append((current_half, current_events))
            current_half = line
            current_events = []
            continue
        if current_half is not None:
            current_events.append(line)
    if current_half is not None:
        innings.append((current_half, current_events))

    scoring_halves = []
    for half_label, events in innings:
        scoring_events = [e for e in events if 'scores:' in e]
        if scoring_events:
            scoring_halves.append((half_label, scoring_events))
    return scoring_halves


def build_local_recap(sim_result):
    """Build a plain-text recap without any AI model."""
    away_score = sim_result['away_score']
    home_score = sim_result['home_score']
    winner = (
        'Away' if away_score > home_score
        else 'Home' if home_score > away_score
        else 'Neither team'
    )
    scoring_halves = extract_scoring_summary(sim_result['play_log'])

    lead_line = (
        f"{winner} won {away_score}-{home_score}."
        if winner != 'Neither team'
        else f"The game ended tied at {away_score}-{home_score}."
    )
    opening = [lead_line]

    if sim_result['completed_nine']:
        opening.append('The game reached a full nine innings.')
    else:
        opening.append(
            f"The game did not reach a normal finish because "
            f"{sim_result['termination_reason']}."
        )

    if sim_result['away_exhausted'] or sim_result['home_exhausted']:
        exhausted = []
        if sim_result['away_exhausted']:
            exhausted.append('away lineup exhausted')
        if sim_result['home_exhausted']:
            exhausted.append('home lineup exhausted')
        opening.append('Roster note: ' + ', '.join(exhausted) + '.')

    body = []
    if scoring_halves:
        for half_label, events in scoring_halves[:4]:
            body.append(f"{half_label}: {' '.join(events)}")
    else:
        body.append(
            'Neither offense produced many scoring threats, '
            'and the game was shaped mostly by outs and lineup attrition.'
        )

    detail_bits = []
    detail_bits.append(
        f"The box score finished with {sim_result['away_hits']} hits for Away "
        f"and {sim_result['home_hits']} for Home, while errors were charged as "
        f"Away {sim_result['away_errors']} and Home {sim_result['home_errors']}."
    )
    if sim_result['away_double_plays'] or sim_result['home_double_plays']:
        detail_bits.append(
            f"Double plays were a factor, with Away turning into "
            f"{sim_result['away_double_plays']} and Home into "
            f"{sim_result['home_double_plays']}."
        )
    if sim_result['away_sac_flies'] or sim_result['home_sac_flies']:
        detail_bits.append(
            f"Sacrifice flies totaled {sim_result['away_sac_flies']} for Away "
            f"and {sim_result['home_sac_flies']} for Home."
        )
    if any([
        sim_result['away_stranded_2b'], sim_result['home_stranded_2b'],
        sim_result['away_stranded_3b'], sim_result['home_stranded_3b'],
    ]):
        detail_bits.append(
            f"Scoring chances left on base included runners stranded at second "
            f"(Away {sim_result['away_stranded_2b']}, Home {sim_result['home_stranded_2b']}) "
            f"and at third (Away {sim_result['away_stranded_3b']}, Home {sim_result['home_stranded_3b']})."
        )

    return '\n'.join(opening + body + detail_bits)


def generate_game_recap(sim_result, model='gpt-4o-mini'):
    """Generate an AI-powered recap if OpenAI key is available, else local fallback."""
    if not sim_result or sim_result.get('game') is None:
        return 'No completed simulation result is available for recap generation.'

    fallback_text = build_local_recap(sim_result)
    api_key = os.getenv('OPENAI_API_KEY')
    # Fallback: try Streamlit Cloud secrets directly
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get('OPENAI_API_KEY')
        except Exception:
            pass
    if not api_key:
        return fallback_text
    api_key = api_key.strip().replace('\n', '').replace('\r', '')

    try:
        from openai import OpenAI
    except ImportError:
        return fallback_text

    away_summary = sim_result['away_roster_summary']
    home_summary = sim_result['home_roster_summary']
    log_lines = sim_result['play_log']
    important_lines = [
        line for line in log_lines
        if (
            line.startswith('Top ')
            or line.startswith('Bottom ')
            or 'scores:' in line
            or 'double play' in line.lower()
            or 'tags and scores' in line.lower()
            or 'walks.' in line
            or 'homers.' in line
            or 'doubles.' in line
            or 'singles.' in line
            or line.startswith('End ')
        )
    ]
    trimmed_log = important_lines[:120] if important_lines else log_lines[:120]

    prompt = f"""
Write a beat-writer style baseball game recap in plain English.

Final score: Away {sim_result['away_score']}, Home {sim_result['home_score']}
Termination reason: {sim_result['termination_reason']}
Completed nine innings: {sim_result['completed_nine']}
Away lineup exhausted: {sim_result['away_exhausted']}
Home lineup exhausted: {sim_result['home_exhausted']}
Away batting order: {away_summary['batting_order_text']}
Away bench: {away_summary['bench_text']}
Home batting order: {home_summary['batting_order_text']}
Home bench: {home_summary['bench_text']}
Away hits: {sim_result['away_hits']}
Home hits: {sim_result['home_hits']}
Away errors: {sim_result['away_errors']}
Home errors: {sim_result['home_errors']}
Away stranded at 2B: {sim_result['away_stranded_2b']}
Home stranded at 2B: {sim_result['home_stranded_2b']}
Away stranded at 3B: {sim_result['away_stranded_3b']}
Home stranded at 3B: {sim_result['home_stranded_3b']}
Away sac flies: {sim_result['away_sac_flies']}
Home sac flies: {sim_result['home_sac_flies']}
Away double plays: {sim_result['away_double_plays']}
Home double plays: {sim_result['home_double_plays']}

Use these key log lines:
{chr(10).join(trimmed_log)}

Requirements:
- Write like a short newspaper game story, not a bullet list.
- Recap both teams.
- Explain the key scoring swings and how the final score developed.
- Mention lineup exhaustion only if it mattered.
- Mention if the game did not reach nine innings.
- Keep it readable and under 250 words.
"""

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    'role': 'system',
                    'content': 'You write concise, lively beat-writer baseball recaps from structured game logs.',
                },
                {'role': 'user', 'content': prompt},
            ],
        )
        content = response.choices[0].message.content
        if content:
            return content.strip()
        return fallback_text
    except Exception:
        return fallback_text
