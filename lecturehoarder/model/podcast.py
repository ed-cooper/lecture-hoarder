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

        academic_year: int = self.date.year
        if self.date.month < 9:
            # If date falls before September, move to previous academic year
            academic_year -= 1

        return f"{academic_year}-{str(academic_year + 1)[2:]}"
