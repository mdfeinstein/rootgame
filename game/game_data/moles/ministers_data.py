import json
import os
from typing import TypedDict

# Load minister data from JSON
_data_file = os.path.join(os.path.dirname(__file__), "ministers.json")
with open(_data_file, "r") as f:
    _data = json.load(f)

# Type definitions
class MinisterInfo(TypedDict):
    name: str
    enum_name: str
    crown_type: str
    required_cards: int
    description: str
    action_description: str

class CrownInfo(TypedDict):
    display_name: str
    required_cards: int

# Accessible dicts with proper typing
MINISTERS: dict[str, MinisterInfo] = {
    m["enum_name"]: m for m in _data["ministers"]
}
CROWN_TYPES: dict[str, CrownInfo] = _data["crown_types"]
