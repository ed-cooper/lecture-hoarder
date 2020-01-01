import time


class Download:
    """A podcast being downloaded.

    Attributes:
        name                The podcast name.
        podcast_link        The URL of the podcast webpage.
        download_path       The URL of the podcast video source.
        status              The current download status.
        error_message       The error message, if an error has occurred.
        progress            The current download progress.
        total_size          The total download size.
        completion_time     The time when the podcast download completed / terminated.
    """

    name: str = None
    podcast_link: str = None
    download_path: str = None
    status: str = "waiting"
    error_message: str = None
    progress: int = 0
    total_size: int = 0
    completion_time: time = None

    def __init__(self, name: str, podcast_link: str, download_path: str):
        self.name = name
        self.podcast_link = podcast_link
        self.download_path = download_path

    def set_complete(self):
        """Marks the podcast download as being completed."""

        self.status = "complete"
        self.completion_time = time.time()

    def set_error(self, message: str):
        """Marks the podcast download as terminated due to an error.

        :param message: The error message.
        """

        self.status = "error"
        self.error_message = message
        self.completion_time = time.time()
