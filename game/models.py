from pydantic import BaseModel
from typing import Dict, List, Optional


# Card properties
class Card(BaseModel):
    value: int
    suit: str
    is_red: bool
    is_special: bool
    point_value: int


class ActionOption(BaseModel):
    action_type: str
    card_index: Optional[int] = None


# Player properties
class Player(BaseModel):
    id: str  # Unique ID for the player
    hand: List[Card]
    is_active: bool = False  # Is it their turn?
    card_count: int = 4  # Start with 4 cards


# Game State
class GameState(BaseModel):
    players: List[Player] = []
    deck: List[Card]  # The deck of cards
    discard_pile: List[Card] = []
    current_turn_player_id: Optional[str] = None
    turn_end_time: Optional[float] = None  # Unix timestamp
    discard_opportunity_end_time: Optional[float] = None  # Unix timestamp
    status: str = "Lobby"  # 'Lobby', 'Playing', 'GameOver'
    winning_player_id: Optional[str] = None
    next_action: Optional[Dict] = None  # To store details about the next action required
