from datetime import datetime


class Podcast:
    """Represents a podcast than can be downloaded.

    Attributes:
        date        The date of the podcast.
        name        The name of the podcast.
        url         The URL for the podcast.
    """

    date: datetime = None
    name: str = None
    url: str = None

    def __init__(self, name: str, date: datetime, url: str):
        self.name = name
        self.date = date
        self.url = url

    def get_academic_year(self) -> str:
        """Returns the name of the academic year for the podcast."""

        return str(self.date.year)
