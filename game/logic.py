import random
from typing import List
from .models import Card, Player, GameState


def create_deck() -> List[Card]:
    suits = ["Hearts", "Diamonds", "Clubs", "Spades"]
    deck = []
    for suit in suits:
        for value in range(1, 14):  # A=1, K=13
            is_red = suit in ["Hearts", "Diamonds"]
            is_special = value in [7, 8, 9, 10]
            point_value = 10 if value > 10 else value
            if is_red and value == 13:  # Red King
                point_value = -1

            deck.append(
                Card(
                    value=value,
                    suit=suit,
                    is_red=is_red,
                    is_special=is_special,
                    point_value=point_value,
                )
            )
    return deck


def shuffle_deck(deck: List[Card]):
    random.shuffle(deck)


def deal_initial_hands(deck: List[Card], num_players: int) -> List[Player]:
    players = []
    for i in range(num_players):
        hand = [deck.pop() for _ in range(4)]
        players.append(Player(id=f"player_{i}", hand=hand))
    return players


def create_initial_game_state(num_players: int) -> GameState:
    deck = create_deck()
    shuffle_deck(deck)
    players = deal_initial_hands(deck, num_players)
    return GameState(players=players, deck=deck)


def get_player_cards_to_peek(player_id: str, game_state: GameState):
    player = next((p for p in game_state.players if p.id == player_id), None)
    if player:
        return [player.hand[0], player.hand[1]]
    return None

