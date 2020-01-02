class Podcast:
    """Represents a podcast than can be downloaded.

    Attributes:
        name        The name of the podcast.
        url         The URL for the podcast.
    """

    name: str = None
    url: str = None

    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url
