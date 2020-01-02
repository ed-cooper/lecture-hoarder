from enum import Enum, unique


@unique
class DownloadStatus(Enum):
    """Represents the possible status values for a podcast download.

    Values:
        WAITING         The download has been queued but not yet started.
        STARTING        The download is initialising.
        DOWNLOADING     The download is currently in progress.
        COMPLETE        The download has completed successfully.
        ERROR           An error has occurred and the download has terminated.
    """

    WAITING = "Waiting"
    STARTING = "Starting"
    DOWNLOADING = "Downloading"
    COMPLETE = "Complete"
    ERROR = "Error"
