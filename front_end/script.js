const urlParams = new URLSearchParams(window.location.search);
const gameId = urlParams.get('game_id') || '1';
const playerId = urlParams.get('player_id') || 'player_0';

const ws = new WebSocket(`ws://127.0.0.1:8000/ws/${gameId}/${playerId}`);

const gameStatusElement = document.getElementById("game-status");
const currentTurnElement = document.getElementById("current-turn");
const playersHandsElement = document.getElementById("players-hands");
const deckElement = document.getElementById("deck");
const discardPileElement = document.getElementById("discard-pile");
const drawCardButton = document.getElementById("draw-card-button");
const actionButtonsContainer = document.getElementById("action-buttons-container");

drawCardButton.addEventListener("click", () => {
    const message = {
        type: "draw_card",
        player_id: playerId
    };
    ws.send(JSON.stringify(message));
});

ws.onopen = (event) => {
    console.log("WebSocket connection established!");
};

ws.onmessage = (event) => {
    const gameState = JSON.parse(event.data);

    console.log("Received new game state:", gameState);

    // Update the game status
    gameStatusElement.textContent = gameState.status;
    currentTurnElement.textContent = gameState.current_turn_player_id;

    // Clear previous hands
    playersHandsElement.innerHTML = '';

    // Render each player's hand
    gameState.players.forEach(player => {
        const playerDiv = document.createElement("div");
        playerDiv.innerHTML = `<h3>${player.id} (${player.card_count} cards)</h3>`;

        const handContainer = document.createElement("div");
        handContainer.classList.add("card-container");

        player.hand.forEach(card => {
            const cardDiv = document.createElement("div");
            cardDiv.classList.add("card");
            if (card.is_red) {
                cardDiv.classList.add("red");
            }
            cardDiv.innerHTML = `
                <div class="card-value">${card.value}</div>
                <div>${card.suit}</div>
                <div class="card-value">${card.value}</div>
            `;
            handContainer.appendChild(cardDiv);
        });

        playerDiv.appendChild(handContainer);
        playersHandsElement.appendChild(playerDiv);
    });

    // Render the deck
    deckElement.innerHTML = `Deck (${gameState.deck.length})`;

    // Render the discard pile (top card only)
    if (gameState.discard_pile.length > 0) {
        const topCard = gameState.discard_pile[gameState.discard_pile.length - 1];
        const cardDiv = document.createElement("div");
        cardDiv.classList.add("card");
        if (topCard.is_red) {
            cardDiv.classList.add("red");
        }
        cardDiv.innerHTML = `
            <div class="card-value">${topCard.value}</div>
            <div>${topCard.suit}</div>
            <div class="card-value">${topCard.value}</div>
        `;
        discardPileElement.innerHTML = '';
        discardPileElement.appendChild(cardDiv);
    } else {
        discardPileElement.textContent = "Empty";
    }

    // Handle next actions based on the game state
    if (gameState.next_action && gameState.next_action.player_id === playerId) {
        drawCardButton.style.display = 'none';
        actionButtonsContainer.innerHTML = '';

        const actionCard = gameState.next_action.card;
        const cardDiv = document.createElement("div");
        cardDiv.innerHTML = `<h3>You drew a:</h3>`;

        const cardDisplay = document.createElement("div");
        cardDisplay.classList.add("card");
        if (actionCard.is_red) {
            cardDisplay.classList.add("red");
        }
        cardDisplay.innerHTML = `
            <div class="card-value">${actionCard.value}</div>
            <div>${actionCard.suit}</div>
            <div class="card-value">${actionCard.value}</div>
        `;

        actionButtonsContainer.appendChild(cardDiv);
        actionButtonsContainer.appendChild(cardDisplay);

        const actionsDiv = document.createElement("div");
        actionsDiv.innerHTML = "<h4>What would you like to do?</h4>";

        gameState.next_action.options.forEach(option => {
            const button = document.createElement("button");
            button.textContent = option.replace('_', ' '); // Make button text readable
            button.addEventListener("click", () => {
                const message = {
                    type: "resolve_draw",
                    player_id: playerId,
                    action: option
                };
                if (option === "blind_swap") {
                    const cardIndex = prompt("Enter the index of the card to swap (0-3):");
                    message.card_index = parseInt(cardIndex);
                }
                ws.send(JSON.stringify(message));
            });
            actionsDiv.appendChild(button);
        });

        actionButtonsContainer.appendChild(actionsDiv);
    } else {
        actionButtonsContainer.innerHTML = '';
        if (gameState.current_turn_player_id === playerId) {
            drawCardButton.style.display = 'block';
        } else {
            drawCardButton.style.display = 'none';
        }
    }
};

ws.onclose = (event) => {
    console.log("WebSocket connection closed.");
};

ws.onerror = (error) => {
    console.error("WebSocket error:", error);
};