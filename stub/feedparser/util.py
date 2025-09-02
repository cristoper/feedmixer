from typing import Any, Dict, List, Optional, Tuple


class FeedParserDict(dict):
    # This is a simplification. The actual object allows attribute access for keys.
    # mypy doesn't easily support this without plugins, but we can list common keys.
    entries: List["FeedParserDict"]
    feed: "FeedParserDict"
    link: str
    title: str
    author_detail: "FeedParserDict"
    bozo: int
    bozo_exception: Exception
    href: str
    length: str
    type: str
    published_parsed: Optional[Tuple[int, int, int, int, int, int, int, int, int]]
    updated_parsed: Optional[Tuple[int, int, int, int, int, int, int, int, int]]
