from dataclasses import dataclass

@dataclass
class Habit:
    id: int | None
    user_id: int
    name: str
    period: str
