class UnavailableActionError(Exception):
    """Action attempted at wrong timing, out-of-turn, or by wrong player."""


class IllegalActionError(Exception):
    """Action is correctly timed but violates game rules."""
