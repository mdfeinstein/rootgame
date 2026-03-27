- [x] Charm Offensive:
  - Woodland alliance: used charm offensive. still showing up in get action. trying to use again yields error: Charm Offensive cannot be used right now. It must be at the start of your Evening.
  - Fix: check_charm_offensive now uses can_use_card to ensure it doesn't launch multiple events for a used card. Added safer event filtering in use/skip logic.

- [x] Turns in log. players next turn is created and logged when their turn ends, which jumbles the logs. should reconfigrue the turn logic to create the next turn when the previous player ends turn and calls next_turn

- [x] League of Adventurous Mice: Crafted but no items in users supply to use with it. when clicking the action in the usable crafted cards box, no prompt is displayed, and i cant see the network rerquest firing.
- [x] Raid plot destroyed by revolt didn't place corvid warriors in adjacent clearings
- [x] log: units removed in revolt reported in revolt log, but then also separately reported with no parent log. should only be reported in the revolt log.
