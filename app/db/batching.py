from collections.abc import Iterable, Sequence


def chunks[T](rows: Sequence[T], size: int) -> Iterable[Sequence[T]]:
    for index in range(0, len(rows), size):
        yield rows[index : index + size]
