import time

from model.download_status import DownloadStatus
from model.podcast import Podcast


class Download:
    """A podcast being downloaded.

    Attributes:
        podcast             The podcast being downloaded.
        download_path       The file path where the podcast will be saved.
        status              The current download status.
        error_message       The error message, if an error has occurred.
        progress            The current download progress.
        total_size          The total download size.
        completion_time     The time when the podcast download completed / terminated.
    """

    podcast: Podcast = None
    download_path: str = None
    status: DownloadStatus = DownloadStatus.WAITING
    error_message: str = None
    progress: int = 0
    total_size: int = 0
    completion_time: time = None

    def __init__(self, podcast: Podcast, download_path: str):
        """Creates a new instance of a podcast download.

        :param podcast:         The podcast being downloaded.
        :param download_path:   The path to download the podcast to.
        """

        self.podcast = podcast
        self.download_path = download_path

    def set_complete(self):
        """Marks the podcast download as being completed."""

        self.status = DownloadStatus.COMPLETE
        self.completion_time = time.time()

    def set_error(self, message: str):
        """Marks the podcast download as terminated due to an error.

        :param message: The error message.
        """

        self.status = DownloadStatus.ERROR
        self.error_message = message
        self.completion_time = time.time()
