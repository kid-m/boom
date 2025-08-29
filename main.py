import json
import time
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from typing import Dict, List, Optional
from game.models import GameState, Player, Card

app = FastAPI()

# Mount the 'front_end' directory to serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="front_end"), name="static")

# In-memory storage for game states. In a real-world app, this would be a database.
games: Dict[str, GameState] = {}


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, game_id: str, websocket: WebSocket):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = []
        self.active_connections[game_id].append(websocket)

    def disconnect(self, game_id: str, websocket: WebSocket):
        self.active_connections[game_id].remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, game_id: str, message: str):
        if game_id in self.active_connections:
            for connection in self.active_connections[game_id]:
                await connection.send_text(message)


manager = ConnectionManager()


def create_initial_game_state(num_players: int) -> GameState:
    # Create a full 52-card deck
    suits = ["Spades", "Hearts", "Clubs", "Diamonds"]
    deck = []
    for suit in suits:
        for value in range(1, 14):
            is_red = suit in ["Hearts", "Diamonds"]
            is_special = True
            point_value = value
            deck.append(
                Card(
                    value=value,
                    suit=suit,
                    is_red=is_red,
                    is_special=is_special,
                    point_value=point_value,
                )
            )

    import random

    random.shuffle(deck)

    players = []
    for i in range(num_players):
        hand = [deck.pop() for _ in range(4)]
        players.append(Player(id=f"player_{i}", hand=hand))

    return GameState(
        players=players,
        deck=deck,
        discard_pile=[],
        current_turn_player_id=None,
        turn_end_time=None,
        discard_opportunity_end_time=None,
        status="Lobby",
        winning_player_id=None,
    )


@app.post("/game/create")
def create_game(num_players: int = 2):
    game_id = str(len(games) + 1)
    games[game_id] = create_initial_game_state(num_players)
    games[game_id].status = "Lobby"
    return {"game_id": game_id, "status": "Lobby"}


@app.post("/game/{game_id}/start")
def start_game(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[game_id]
    if game.status != "Lobby":
        raise HTTPException(status_code=400, detail="Game has already started")

    game.status = "Playing"
    game.current_turn_player_id = game.players[0].id
    game.players[0].is_active = True

    return game


@app.websocket("/ws/{game_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, player_id: str):
    await manager.connect(game_id, websocket)
    try:
        initial_state = games.get(game_id)
        if initial_state:
            await manager.send_personal_message(
                json.dumps(initial_state.dict()), websocket
            )

        while True:
            message_str = await websocket.receive_text()
            message = json.loads(message_str)

            if (
                message.get("type") == "draw_card"
                and message.get("player_id") == player_id
            ):
                draw_card(game_id, player_id)
                await manager.broadcast(game_id, json.dumps(games[game_id].dict()))
            elif (
                message.get("type") == "resolve_draw"
                and message.get("player_id") == player_id
            ):
                action_type = message.get("action")
                if action_type == "activate_effect":
                    resolve_activate_effect(game_id, player_id)
                elif action_type == "discard":
                    resolve_discard(game_id, player_id)
                    end_turn(game_id, player_id)
                elif action_type == "blind_swap":
                    card_index = message.get("card_index")
                    resolve_blind_swap(game_id, player_id, card_index)
                    end_turn(game_id, player_id)

                await manager.broadcast(game_id, json.dumps(games[game_id].dict()))

    except json.JSONDecodeError:
        await manager.send_personal_message("Invalid JSON", websocket)
    except WebSocketDisconnect:
        manager.disconnect(game_id, websocket)
        await manager.broadcast(game_id, f"Player {player_id} left the game.")


def draw_card(game_id: str, player_id: str):
    game = games.get(game_id)
    if not game:
        return {"success": False, "message": "Game not found"}

    player = next((p for p in game.players if p.id == player_id), None)
    if not player:
        return {"success": False, "message": "Player not found"}

    if game.current_turn_player_id != player_id:
        game.status = f"It's not your turn, {player_id}."
        return {"success": False, "message": "It's not your turn."}

    if not game.deck:
        return {"success": False, "message": "Deck is empty"}

    drawn_card = game.deck.pop(0)

    game.next_action = {
        "player_id": player_id,
        "card": drawn_card.dict(),
        "options": ["activate_effect", "discard", "blind_swap"],
    }

    game.status = f"{player_id} drew a card. Waiting for action."
    return {"success": True, "message": "Card drawn successfully"}


def resolve_activate_effect(game_id: str, player_id: str):
    game = games.get(game_id)
    if not game or not game.next_action or game.next_action["player_id"] != player_id:
        return {"success": False, "message": "Invalid action or turn"}

    drawn_card = Card(**game.next_action["card"])
    game.discard_pile.append(drawn_card)

    game.status = f"Effect of {drawn_card.value} {drawn_card.suit} activated!"
    game.next_action = None
    return {"success": True, "message": "Effect activated"}


def resolve_discard(game_id: str, player_id: str):
    game = games.get(game_id)
    if not game or not game.next_action or game.next_action["player_id"] != player_id:
        return {"success": False, "message": "Invalid action or turn"}

    drawn_card = Card(**game.next_action["card"])
    game.discard_pile.append(drawn_card)

    game.status = f"Player {player_id} discarded the drawn card."
    game.next_action = None
    return {"success": True, "message": "Card discarded"}


def resolve_blind_swap(game_id: str, player_id: str, card_index: int):
    game = games.get(game_id)
    if not game or not game.next_action or game.next_action["player_id"] != player_id:
        return {"success": False, "message": "Invalid action or turn"}

    player = next((p for p in game.players if p.id == player_id), None)
    if not player or card_index >= len(player.hand):
        game.status = f"Invalid card index for blind swap."
        game.next_action = None
        return {"success": False, "message": "Invalid card index"}

    drawn_card = Card(**game.next_action["card"])
    swapped_card = player.hand.pop(card_index)
    player.hand.append(drawn_card)
    game.discard_pile.append(swapped_card)

    game.status = f"Player {player_id} blind swapped a card."
    game.next_action = None
    return {"success": True, "message": "Blind swap successful"}


def end_turn(game_id: str, player_id: str):
    game = games.get(game_id)
    if not game:
        return {"success": False, "message": "Game not found"}

    current_player_index = next(
        (i for i, p in enumerate(game.players) if p.id == player_id), None
    )
    if current_player_index is None:
        return {"success": False, "message": "Player not found"}

    game.players[current_player_index].is_active = False

    next_player_index = (current_player_index + 1) % len(game.players)
    next_player = game.players[next_player_index]

    next_player.is_active = True
    game.current_turn_player_id = next_player.id

    game.status = f"Player {next_player.id}'s turn"

    return {"success": True, "message": "Turn ended successfully"}
