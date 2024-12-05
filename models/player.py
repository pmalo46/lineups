"""
Player model and related functionality.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class Player:
    id: str
    name: str
    position: str
    team: str
    at_bats: List[Dict]
    
    @property
    def has_remaining_at_bats(self) -> bool:
        """Check if player has any remaining at-bats.
        
        Returns:
            bool: True if player has unused at-bats, False otherwise
        """
        return len(self.at_bats) > 0
    
    def get_next_at_bat(self) -> Optional[Dict]:
        """Get the next available at-bat for the player.
        
        Returns:
            Optional[Dict]: Next at-bat data if available, None otherwise
        """
        if self.has_remaining_at_bats:
            return self.at_bats.pop(0)
        return None
    
    def is_eligible_for_position(self, position: str) -> bool:
        """Check if player is eligible for a given position.
        
        Args:
            position (str): Position to check eligibility for
            
        Returns:
            bool: True if eligible, False otherwise
        """
        # Add position eligibility logic here
        pass 