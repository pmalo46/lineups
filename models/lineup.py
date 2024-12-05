"""
Lineup model and related functionality.
"""

from typing import Dict, List, Optional
from .player import Player

class Lineup:
    def __init__(self):
        """Initialize a lineup."""
        self.batting_order: List[Player] = []
        self.bench: List[Player] = []
        self.current_spot = 0
        
    def add_starter(self, player: Player, position: int) -> bool:
        """Add a starter to the lineup at a specific position.
        
        Args:
            player (Player): Player to add
            position (int): Batting order position (1-9)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if 1 <= position <= 9 and len(self.batting_order) < 9:
            self.batting_order.insert(position - 1, player)
            return True
        return False
    
    def add_bench_player(self, player: Player) -> bool:
        """Add a player to the bench.
        
        Args:
            player (Player): Player to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        if player not in self.bench:
            self.bench.append(player)
            return True
        return False
    
    def get_next_batter(self) -> Optional[Player]:
        """Get the next batter in the lineup.
        
        Returns:
            Optional[Player]: Next batter if available, None otherwise
        """
        if not self.has_available_batters():
            return None
            
        current_batter = self.batting_order[self.current_spot]
        while not current_batter.has_remaining_at_bats:
            # Try to substitute a bench player
            if self.bench:
                substitute = self.bench.pop(0)
                self.batting_order[self.current_spot] = substitute
                current_batter = substitute
            else:
                return None
                
        self.current_spot = (self.current_spot + 1) % 9
        return current_batter
    
    def has_available_batters(self) -> bool:
        """Check if there are any available batters.
        
        Returns:
            bool: True if there are available batters, False otherwise
        """
        return any(player.has_remaining_at_bats for player in self.batting_order) or \
               any(player.has_remaining_at_bats for player in self.bench) 