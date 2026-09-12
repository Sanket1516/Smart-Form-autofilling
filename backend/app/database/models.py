from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DatabaseHealth:
    name: str
    available: bool
    detail: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
