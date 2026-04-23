---
description: How to add new phase logs and log types
---

# Logging Workflow

When introducing new log models to the `GameLog` infrastructure, follow this protocol:

1. **Definining the LogType**
   - Open `game/models/game_log.py`
   - Add a new literal enum value to the `LogType` class mapping representing your new phase or action.

2. **Log Serializer & Text Generation**
   - Open `game/serializers/logs/<faction>.py` (or `general.py` for global actions).
   - Create `{Action}LogDetailsSerializer(serializers.Serializer)`.
   - You MUST define `text = serializers.SerializerMethodField('get_text')` returning the formatted, human-readable sentence (using `def get_text(self, obj):`). This keeps the frontend generic.
   - For `Card` objects, map the field using `card = serializers.DictField()`. Avoid `CardSerializer()` directly inside your DetailsSerializer to avoid triggering internal DRF string-validations recursively!
   - Update `game/serializers/logs/main.py` -> `GameLogSerializer.get_details` to mount your new LogType and serializer.

3. **Log Factory Method**
   - Add a `def log_{action}(game: Game, player: Player, ..., parent=None) -> GameLog:` method beneath your serializers.
   - This factory wrapper must instantiate your new DetailsSerializer, inserting the `details=serializer.validated_data`.
   - If passing cards, ensure the generic DRF `CardSerializer(card).data` dictates the property mapped to the dictionary.
   
4. **Invoking from the Transaction**
   - Open the relevant phase file inside `game/transactions/`.
   - Import your log factory securely, and additionally fetch `get_current_phase_log(player.game, player)`.
   - Expose the underlying mapping objects where necessary (e.g., retrieving `card_model = hand_entry.card` *before* the transaction deletes `hand_entry`).
   - Trigger your log injection directly before the final save.
