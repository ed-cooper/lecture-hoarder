class Course:
    """Represents a course that has lectures.

    Attributes:
        name        The display name of the course.
        url         The URL for the course podcast home page.
    """

    name: str = None
    url: str = None
    series: str = None

    def __init__(self, name: str, url: str, series: str):
        self.name = name
        self.url = url
        self.series = series
