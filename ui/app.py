"""
Main entry point for the Streamlit web application.
"""

import streamlit as st
from .views import render_player_selection, render_lineup_management, render_game_simulation

def main():
    st.title("Lineups - Fantasy Baseball Reimagined")
    
    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state.page = 'player_selection'
        
    # Navigation
    pages = {
        'Player Selection': 'player_selection',
        'Lineup Management': 'lineup_management',
        'Game Simulation': 'game_simulation'
    }
    
    page = st.sidebar.radio('Navigation', list(pages.keys()))
    st.session_state.page = pages[page]
    
    # Render appropriate view
    if st.session_state.page == 'player_selection':
        render_player_selection()
    elif st.session_state.page == 'lineup_management':
        render_lineup_management()
    elif st.session_state.page == 'game_simulation':
        render_game_simulation()

if __name__ == '__main__':
    main() 