from typing import Type
from django.db.models import TextChoices


def next_choice(
    choice_class: Type[TextChoices], current_value: str, wrap: bool = False
) -> str:
    """returns the next choice in the list of choices
    if wrap is True, wraps around to the first choice
    if wrap is False, returns the last choice
    """
    choices = list(choice_class)
    for i, choice in enumerate(choices):
        if choice.value == current_value:
            if i + 1 == len(choices):
                return choices[0].value if wrap else choices[-1].value
            else:
                return choices[i + 1].value
            # return choices[(i + 1) % len(choices)].value  # wrap around
    raise ValueError(
        f"{current_value!r} is not a valid choice for {choice_class.__name__}"
    )


def get_choice_value_by_label_or_value(
    choice_class: Type[TextChoices], label_or_value: str
) -> str:
    """
    returns the value of the choice with the given label, or validates that the value is valid
    """
    for choice in choice_class.choices:
        if choice[0] == label_or_value:
            return choice[0]
        if choice[1] == label_or_value:
            return choice[0]
    raise ValueError(
        f"{label_or_value!r} is not a valid choice for {choice_class.__name__}"
    )
