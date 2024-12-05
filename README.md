# Lineups - Fantasy Baseball Reimagined

## Overview
Lineups is a unique fantasy baseball game that brings a new dimension to the fantasy sports experience. Unlike traditional fantasy baseball where points are awarded for accumulated stats, Lineups lets you play actual simulated baseball games using your players' real-life performances. As a manager, you'll draft players and set strategic lineups to manufacture runs and win games.

## How It Works

### Data Source
- Real-time MLB data powered by the Tank01 MLB API
- Live player stats, game data, and play-by-play information
- Continuous updates during active MLB games

### Core Game Mechanics

#### 1. Team Building
- Draft a complete lineup including:
  - Starting position players (C, 1B, 2B, 3B, SS, OF x3, DH)
  - Bench players for pinch-hitting situations
- Players are only available if their MLB team has a game scheduled

#### 2. Lineup Strategy
- Set your batting order (1-9)
- Arrange bench players in preferred pinch-hitting order
- Strategic decisions impact run production and game outcomes

#### 3. Game Simulation
The game engine simulates a full 9-inning baseball game using:
- Actual player performances from their real MLB games
- True-to-baseball rules and situations:
  - Runners advance realistically based on hit types
  - Force plays and double plays
  - Sacrifice situations
  - Pinch-hitting substitutions when players run out of at-bats

### Game Engine Details

#### At-Bat Resolution
- Each at-bat outcome is pulled directly from the player's real game
- Outcomes include:
  - Hits (singles, doubles, triples, home runs)
  - Walks and strikeouts
  - Various types of outs (groundouts, flyouts, etc.)

#### Baserunning Rules
- Singles: Runners advance two bases if already on second
- Doubles: All runners score from second or third
- Triples/Home Runs: All runners score
- Sacrifice flies: Runners on third score

#### Substitution System
- Players can only use actual at-bats from their real game
- When a player runs out of at-bats, the next available pinch-hitter is automatically substituted
- Game ends if no eligible batters remain

## Technical Architecture

### Frontend (Streamlit)
- Clean, intuitive user interface
- Real-time game updates
- Interactive lineup management
- Live scoring display

### Backend
- Python-based game engine
- Tank01 MLB API integration
- Efficient data processing and caching
- Stateless game simulation

### Data Flow
1. Live MLB data fetched from Tank01 API
2. Player data processed and cached
3. User selections captured through UI
4. Game engine simulates based on real outcomes
5. Results displayed in real-time

## Future Enhancements
- League play with head-to-head matchups
- Season-long competitions
- Historical game modes
- Advanced statistics and analysis
- Mobile app development

## Getting Started
(Development in progress - Setup instructions to be added after Tank01 API integration)

## Contributing
We welcome contributions! Please see our contributing guidelines for details.

## License
[License details to be added]