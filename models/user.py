from dataclasses import dataclass

@dataclass
class User:
    user_id: int
    username: str | None
    first_name: str | None
