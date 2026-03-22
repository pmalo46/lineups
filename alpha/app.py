"""
app.py
Lineups — Fantasy Baseball Reimagined (Streamlit Beta)

Run with:  streamlit run app.py
"""

import os
import streamlit as st

# Load .env locally if available; on Streamlit Cloud, secrets are injected automatically
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Make Streamlit Cloud secrets available as env vars
if hasattr(st, 'secrets'):
    for key, val in st.secrets.items():
        os.environ.setdefault(key, val)

from streamlit_sortables import sort_items
from data_loader import load_data
from engine import (
    empty_team_template,
    get_selected_ids,
    run_two_team_simulation,
)
from recap import build_local_recap, generate_game_recap

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Lineups ⚾", page_icon="⚾", layout="wide", initial_sidebar_state="expanded")

# ---------------------------------------------------------------------------
# Cached data loading
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Loading player data…")
def cached_load_data():
    return load_data()


players, plays_df = cached_load_data()

# Build lookup helpers
PLAYER_LOOKUP = {p['longName']: str(p['playerID']) for p in players}
PLAYERS_BY_POS = {}
for pos in ['C', '1B', '2B', '3B', 'SS', 'OF']:
    PLAYERS_BY_POS[pos] = sorted(p['longName'] for p in players if p['pos'] == pos)
NON_PITCHERS = sorted(p['longName'] for p in players if p['pos'] != 'P')

STARTER_POSITIONS = ['C', '1B', '2B', '3B', 'SS', 'OF', 'OF', 'OF', 'DH']

# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------

def init_state():
    for key in ['away_roster', 'home_roster']:
        if key not in st.session_state:
            st.session_state[key] = empty_team_template()
    for key in ['away_locked', 'home_locked']:
        if key not in st.session_state:
            st.session_state[key] = False
    if 'sim_result' not in st.session_state:
        st.session_state['sim_result'] = None
    if 'splash_dismissed' not in st.session_state:
        st.session_state['splash_dismissed'] = False

init_state()

# ---------------------------------------------------------------------------
# Splash screen (first visit only)
# ---------------------------------------------------------------------------

if not st.session_state['splash_dismissed']:
    st.markdown("""
    <style>
    .splash-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 60vh;
        text-align: center;
        padding: 2rem;
    }
    .splash-title {
        font-size: 4rem;
        margin-bottom: 0.5rem;
    }
    .splash-line {
        font-size: 1.3rem;
        font-style: italic;
        color: #aaa;
        margin: 0.3rem 0;
    }
    .splash-bold {
        font-size: 1.3rem;
        font-style: italic;
        color: #fff;
        margin: 0.3rem 0;
    }
    .splash-spacer {
        height: 2rem;
    }
    </style>
    <div class="splash-container">
        <div class="splash-title">⚾ Lineups</div>
        <div class="splash-spacer"></div>
        <div class="splash-line">Forget collecting stats in your fantasy league.</div>
        <div class="splash-spacer"></div>
        <div class="splash-line">No points. No multipliers. Just real baseball. </div>
        <div class="splash-spacer"></div>
        <div class="splash-bold">You're a manager. It's game day.</div>
        <div class="splash-bold">Draft your roster. Fill out your lineup card. Play ball.</div>
        <div class="splash-spacer"></div>
        <div class="splash-line">Every at-bat is real. Every run is earned.</div>
        <div class="splash-spacer"></div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("Let's Go", type="primary", use_container_width=True):
            st.session_state['splash_dismissed'] = True
            st.rerun()

    st.stop()

# ---------------------------------------------------------------------------
# Helper: build a team selection + lineup panel
# ---------------------------------------------------------------------------

def render_team_panel(label, roster_key, lock_key, other_roster_key):
    """Draw all controls for one team (roster picks + batting order)."""

    is_locked = st.session_state[lock_key]
    roster = st.session_state[roster_key]
    other_ids = get_selected_ids(st.session_state[other_roster_key])

    st.subheader(f"{'🔵' if label == 'Away' else '🔴'} {label} Team")

    # ---- Starter selection (diamond layout) ---------------------------------
    st.markdown("**Starters**")
    starter_picks = {}

    def _pos_select(display_label, pos, of_idx=None):
        """Render a selectbox for one position and record the pick."""
        options = NON_PITCHERS if pos == 'DH' else PLAYERS_BY_POS.get(pos, NON_PITCHERS)
        current = None
        if pos == 'OF' and of_idx is not None:
            current = roster['OF'][of_idx].get('name') or None
        elif pos in roster and isinstance(roster[pos], dict):
            current = roster[pos].get('name') or None
        full_opts = ['— Select —'] + list(options)
        idx = full_opts.index(current) if current and current in full_opts else 0
        pick = st.selectbox(
            display_label, full_opts, index=idx,
            key=f"{label}_{display_label}", disabled=is_locked,
        )
        starter_picks[display_label] = pick

    # Row 1: Outfield (LF / CF / RF)
    of1, of2, of3 = st.columns(3)
    with of1:
        _pos_select("OF 1", "OF", of_idx=0)
    with of2:
        _pos_select("OF 2", "OF", of_idx=1)
    with of3:
        _pos_select("OF 3", "OF", of_idx=2)

    # Row 2: SS / 2B
    _, ss_col, _, tb_col, _ = st.columns([1, 2, 1, 2, 1])
    with ss_col:
        _pos_select("SS", "SS")
    with tb_col:
        _pos_select("2B", "2B")

    # Row 3: 3B / 1B
    tb3_col, _, fb_col = st.columns([2, 3, 2])
    with tb3_col:
        _pos_select("3B", "3B")
    with fb_col:
        _pos_select("1B", "1B")

    # Row 4: Catcher
    _, c_col, _ = st.columns([2, 3, 2])
    with c_col:
        _pos_select("C", "C")

    # Row 5: DH
    _, dh_col, _ = st.columns([2, 3, 2])
    with dh_col:
        _pos_select("DH", "DH")

    # ---- Bench selection --------------------------------------------------
    st.markdown("**Bench (PH1–PH6)**")
    bench_picks = []
    for i in range(1, 7):
        key = f"{label}_PH{i}"
        current = roster['PH'][i - 1].get('name') or None
        full_opts = ['— Select —'] + NON_PITCHERS
        idx = full_opts.index(current) if current and current in full_opts else 0
        pick = st.selectbox(
            f"PH{i}", full_opts, index=idx,
            key=key, disabled=is_locked,
        )
        bench_picks.append(pick)

    # ---- Batting order (only after lock) ----------------------------------
    if is_locked:
        st.markdown("---")
        st.markdown("**Batting Order (drag to reorder)**")
        starter_names = _get_starter_names(roster)

        # Build initial order: respect existing slot assignments, fallback to roster order
        existing = [None] * 9
        unassigned = []
        for name in starter_names:
            slot = None
            for p in _all_starters(roster):
                if p.get('name') == name and p.get('lineup_slot'):
                    slot = p['lineup_slot']
                    break
            if slot and 1 <= slot <= 9:
                existing[slot - 1] = name
            else:
                unassigned.append(name)
        # Fill empty slots with unassigned players
        for i in range(9):
            if existing[i] is None and unassigned:
                existing[i] = unassigned.pop(0)
        initial_order = [n for n in existing if n is not None]

        team_color = "#1e3a5f" if label == "Away" else "#5f1e1e"
        team_border = "#3b82f6" if label == "Away" else "#ef4444"
        team_hover = "#2b5a8f" if label == "Away" else "#8f2b2b"
        sortable_style = f"""
            .sortable-item {{
                background-color: {team_color};
                color: white;
                padding: 8px 12px;
                margin: 4px 0;
                border-radius: 6px;
                border-left: 4px solid {team_border};
                cursor: grab;
            }}
            .sortable-item:hover {{
                background-color: {team_hover};
                border-left-color: {team_border};
            }}
        """

        sorted_order = sort_items(
            initial_order,
            direction="vertical",
            key=f"{label}_batting_order",
            custom_style=sortable_style,
        )

        # Show numbered order for clarity
        for i, name in enumerate(sorted_order, 1):
            st.caption(f"#{i}  {name}")

        if st.button(f"✅ Lock {label} Batting Order", key=f"lock_order_{label}"):
            if len(sorted_order) != 9:
                st.error("All 9 starters must be in the batting order.")
            else:
                _apply_batting_order(roster, sorted_order)
                st.success(f"{label} batting order locked!")
                st.rerun()

    # ---- Lock / Unlock roster button --------------------------------------
    if not is_locked:
        if st.button(f"🔒 Lock {label} Roster", key=f"lock_{label}"):
            all_names = list(starter_picks.values()) + bench_picks
            ok, msg = _validate_and_save_roster(
                label, roster, starter_picks, bench_picks, other_ids
            )
            if ok:
                st.session_state[lock_key] = True
                st.success(f"{label} roster locked!")
                st.rerun()
            else:
                st.error(msg)
    else:
        if st.button(f"🔓 Unlock {label} Roster", key=f"unlock_{label}"):
            st.session_state[lock_key] = False
            st.session_state['sim_result'] = None
            st.rerun()


def _get_starter_names(roster):
    names = []
    for pos in ['C', '1B', '2B', '3B', 'SS']:
        if roster[pos].get('name'):
            names.append(roster[pos]['name'])
    for p in roster['OF']:
        if p.get('name'):
            names.append(p['name'])
    if roster['DH'].get('name'):
        names.append(roster['DH']['name'])
    return names


def _all_starters(roster):
    out = []
    for pos in ['C', '1B', '2B', '3B', 'SS', 'DH']:
        out.append(roster[pos])
    out.extend(roster['OF'])
    return out


def _apply_batting_order(roster, order_picks):
    """Write lineup_slot into roster based on ordered name list."""
    for pos in ['C', '1B', '2B', '3B', 'SS', 'DH']:
        roster[pos]['lineup_slot'] = ''
    for p in roster['OF']:
        p['lineup_slot'] = ''

    for slot, name in enumerate(order_picks, start=1):
        for pos in ['C', '1B', '2B', '3B', 'SS', 'DH']:
            if roster[pos].get('name') == name:
                roster[pos]['lineup_slot'] = slot
        for p in roster['OF']:
            if p.get('name') == name:
                p['lineup_slot'] = slot


def _validate_and_save_roster(label, roster, starter_picks, bench_picks, other_ids):
    """Validate picks, write into roster dict. Returns (ok, message)."""
    all_names = list(starter_picks.values()) + bench_picks
    if '— Select —' in all_names:
        return False, 'Fill every starter and bench slot before locking.'

    if len(all_names) != len(set(all_names)):
        return False, 'Duplicate player selected within the same team.'

    selected_ids = {PLAYER_LOOKUP[n] for n in all_names if n in PLAYER_LOOKUP}
    overlap = selected_ids.intersection(other_ids)
    if overlap:
        return False, 'One or more players are already on the other team.'

    # Write starters
    of_idx = 0
    for display_label, name in starter_picks.items():
        pid = PLAYER_LOOKUP.get(name, '')
        if display_label.startswith('OF'):
            roster['OF'][of_idx].update({'id': pid, 'name': name, 'lineup_slot': ''})
            of_idx += 1
        elif display_label == 'DH':
            roster['DH'].update({'id': pid, 'name': name, 'lineup_slot': ''})
        else:
            roster[display_label].update({'id': pid, 'name': name, 'lineup_slot': ''})

    # Write bench
    for i, name in enumerate(bench_picks):
        pid = PLAYER_LOOKUP.get(name, '')
        roster['PH'][i].update({
            'id': pid,
            'name': name,
            'lineup_slot': '',
            'bench_order': i + 1,
            'position': 'PH',
        })

    return True, 'OK'


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

st.title("⚾ Lineups — Fantasy Baseball Reimagined")
st.caption("*You draft the talent. You set the lineup. Fantasy Teams, Real Baseball.*")

# ---------------------------------------------------------------------------
# Manager's Notebook (sidebar)
# ---------------------------------------------------------------------------

away_locked = st.session_state['away_locked']
home_locked = st.session_state['home_locked']
away_has_order = all(
    _all_starters(st.session_state['away_roster'])[i].get('lineup_slot')
    for i in range(9)
)
home_has_order = all(
    _all_starters(st.session_state['home_roster'])[i].get('lineup_slot')
    for i in range(9)
)
has_result = st.session_state.get('sim_result') is not None

# Determine game phase (transitions on first team to complete each step)
if has_result:
    _phase = 'results'
elif (away_locked and away_has_order) and (home_locked and home_has_order):
    _phase = 'ready'
elif away_locked or home_locked:
    _phase = 'ordering'
else:
    _phase = 'drafting'

# Track phase changes to auto-expand on new content
if 'notebook_phase' not in st.session_state:
    st.session_state['notebook_phase'] = _phase
    st.session_state['notebook_expanded'] = True

if st.session_state['notebook_phase'] != _phase:
    st.session_state['notebook_phase'] = _phase
    st.session_state['notebook_expanded'] = True

NOTEBOOK_CONTENT = {
    'drafting': (
        "📋 Building Your Roster",
        "You're building a 15-man roster — 9 starters and 6 on the bench. "
        "Every player's results are drawn from their real MLB game today. "
        "If your guy went 3-for-4 with a double in "
        "that game, that's exactly what he brings to your lineup.\n\n"
        "Your bench matters. When a starter's real-life game runs out of "
        "at-bats, a pinch hitter steps in. If your bench runs dry too, the "
        "lineup is exhausted — and outs start piling up. Stock your bench "
        "with players who see a lot of plate appearances."
        "The order you draft your bench is the order they will be subbed into the game."
    ),
    'ordering': (
        "📝 Setting Your Lineup Card",
        "This is your lineup card. The simulation walks through your order "
        "sequentially, just like a real game — top of the first, your #1 "
        "hitter leads off, and the order cycles from there.\n\n"
        "But here's the catch: each player only has as many at-bats as they "
        "had in their real game. A starter who goes 2-for-3 can only come to "
        "the plate 3 times before a pinch hitter replaces him. A guy who goes "
        "1-for-5 gives you five trips to the plate.\n\n"
        "Think about durability, not just talent. A leadoff hitter with only "
        "2 plate appearances will burn through fast and force your bench into "
        "action early."
    ),
    'ready': (
        "⚾ Play Ball",
        "Both managers have submitted their cards. The simulation plays through "
        "a full 9-inning game, at-bat by at-bat. Every outcome — singles, "
        "groundouts, double plays, sac flies — is pulled directly from real "
        "MLB play-by-play data.\n\n"
        "**How baserunning works:**\n\n"
        "Runners advance realistically. On a **single**, a runner on second "
        "scores and others move up one base. On a **double**, a runner on first "
        "scores. **Triples and home runs** clear the bases.\n\n"
        "**Walks** force advancement — bases loaded with a walk pushes a run "
        "home. **Sac flies** score a runner from third if there is a flyout with fewer than "
        "two outs. **Double plays** can kill a rally — with a runner on first "
        "and fewer than two outs, a ground ball turns two.\n\n"
        "**Errors** put the batter on base like a single, and runners advance "
        "accordingly. At the end of each half-inning, any runners stranded on "
        "second or third are tracked — those are the scoring chances your "
        "lineup left on the table.\n\n"
        "No stat collecting. No point multipliers. Runs score the way they score in "
        "baseball: string together hits, move runners over, bring them home. "
        "Or don't — and strand them at second and third like every manager's "
        "nightmare."
    ),
    'results': (
        "📰 Game Over",
        "The game is in the books. The box score, play-by-play log, and recap "
        "are all below.\n\n"
        "Every run was manufactured from real at-bat outcomes. If a runner was "
        "stranded at third, it's because the next batter in your order grounded "
        "out in his real game too. The lineup you set and the players you chose "
        "determined the result — not an algorithm."
    ),
}

with st.sidebar:
    st.header("📓 Manager's Notebook")
    title, body = NOTEBOOK_CONTENT[_phase]
    st.subheader(title)
    st.markdown(body)

st.markdown("---")

col_away, col_spacer, col_home = st.columns([5, 1, 5])

with col_away:
    render_team_panel("Away", "away_roster", "away_locked", "home_roster")

with col_home:
    render_team_panel("Home", "home_roster", "home_locked", "away_roster")

# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

st.markdown("---")

both_locked = away_locked and home_locked
ready = both_locked and away_has_order and home_has_order

if not both_locked:
    st.info("🔒 Lock both rosters and set batting orders to enable simulation.")
elif not (away_has_order and home_has_order):
    st.info("📋 Set the batting order for both teams to enable simulation.")
else:
    if st.button("⚾ Play Ball!", type="primary", use_container_width=True):
        with st.spinner("Simulating game…"):
            result = run_two_team_simulation(
                st.session_state['away_roster'],
                st.session_state['home_roster'],
                plays_df,
                verbose=False,
            )
            st.session_state['sim_result'] = result
        st.rerun()

# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------

result = st.session_state.get('sim_result')
if result and result.get('game') is not None:
    st.markdown("---")
    st.header("📊 Game Results")

    # Scoreboard
    col1, col2, col3 = st.columns(3)
    col1.metric("Away", result['away_score'])
    col2.metric("Home", result['home_score'])
    winner = (
        "Away wins!" if result['away_score'] > result['home_score']
        else "Home wins!" if result['home_score'] > result['away_score']
        else "Tie game!"
    )
    col3.metric("Result", winner)

    # Box score stats
    st.subheader("Box Score")
    box_data = {
        "": ["Away", "Home"],
        "Runs": [result['away_score'], result['home_score']],
        "Hits": [result['away_hits'], result['home_hits']],
        "Errors": [result['away_errors'], result['home_errors']],
        "Double Plays": [result['away_double_plays'], result['home_double_plays']],
        "Sac Flies": [result['away_sac_flies'], result['home_sac_flies']],
        "Stranded 2B": [result['away_stranded_2b'], result['home_stranded_2b']],
        "Stranded 3B": [result['away_stranded_3b'], result['home_stranded_3b']],
    }
    st.dataframe(box_data, use_container_width=True, hide_index=True)

    # Game status
    if result['completed_nine']:
        st.success("Game completed — full 9 innings.")
    else:
        st.warning(f"Game ended early: {result['termination_reason']}")

    if result['away_exhausted']:
        st.info("Away lineup was exhausted during the game.")
    if result['home_exhausted']:
        st.info("Home lineup was exhausted during the game.")

    # Recap
    st.subheader("Game Recap")
    recap_text = generate_game_recap(result)
    st.write(recap_text)

    # Play-by-play log
    with st.expander("📜 Full Play-by-Play Log"):
        for line in result['play_log']:
            if line.startswith('Top ') or line.startswith('Bottom '):
                st.markdown(f"**{line}**")
            elif 'scores:' in line:
                st.markdown(f"🏃 {line}")
            elif 'homers' in line:
                st.markdown(f"💣 {line}")
            else:
                st.text(line)

elif result and result.get('validation_message'):
    st.error(f"Setup error: {result['validation_message']}")
