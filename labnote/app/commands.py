from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


CommandCallback = Callable[[], None]


@dataclass(slots=True)
class Command:
    id: str
    description: str
    callback: CommandCallback
    shortcut: str = ""
    category: str = "General"


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def clear(self) -> None:
        self._commands.clear()

    def register(self, command: Command) -> None:
        self._commands[command.id] = command

    def all(self) -> list[Command]:
        return list(self._commands.values())

    def execute(self, command_id: str) -> bool:
        command = self._commands.get(command_id)
        if not command:
            return False
        command.callback()
        return True

    def search(self, query: str) -> list[Command]:
        normalized = query.strip().casefold()
        commands = self.all()
        if not normalized:
            return sorted(commands, key=lambda item: (item.category, item.description))
        return sorted(
            [
                item
                for item in commands
                if normalized in item.description.casefold()
                or normalized in item.id.casefold()
                or normalized in item.shortcut.casefold()
            ],
            key=lambda item: (item.category, item.description),
        )
