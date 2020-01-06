"""Main command line entry point for lecture-hoarder."""

import concurrent.futures
import getpass
import os
import re
import signal
import string
import sys
import time
from typing import List

from yaml import YAMLError

from logic import PodcastProvider, PodcastProviderError, UomPodcastProvider
from model import Download, DownloadStatus, Profile

# The list of characters that can be used in filenames
VALID_FILE_CHARS = f"-_.() {string.ascii_letters}{string.digits}"

def filter_path_name(path: str) -> str:
    """Filters all invalid characters from a file path name.

    :param path:    The file path to filter.
    :return:        The filtered string.
    """

    return "".join(c for c in path if c in VALID_FILE_CHARS)


def format_size(size_in_bytes: int) -> str:
    """Formats a file size as MB.

    :param size_in_bytes: The file size in bytes.
    :return:              The string formatted size, as MB.
    """

    return str(round(size_in_bytes / (1000 * 1000))) + " MB"


def handle_sigint(signal, frame) -> None:
    """Gracefully exit after sigint (Ctrl-C) signal."""

    print("Terminated by user")
    exit(0)


# Downloads a podcast using the href and a target location.
# Logging messages will use the name to identify which podcast download request it is related to.
def download_podcast(download: Download, web_provider: PodcastProvider) -> None:
    """Executes a queued download operation.

    :param download:        The download operation to perform.
    :param web_provider:    The podcast provider.
    """

    # Set starting status
    download.status = DownloadStatus.STARTING

    # Get download response
    try:
        http_download_response = web_provider.get_podcast_downloader(download.podcast)
    except PodcastProviderError as err:
        # Error whilst logging on
        download.set_error(str(err))
        return

    # Get download size
    download.status = DownloadStatus.DOWNLOADING
    download.total_size = int(http_download_response.headers['Content-Length'])

    # Write to file with partial extension
    with open(download.download_path + ".partial", "wb") as f:
        for chunk in http_download_response:
            f.write(chunk)
            download.progress += len(chunk)

    # Rename completed file
    os.rename(download.download_path + ".partial", download.download_path)

    # Mark as complete
    download.set_complete()


def check_python() -> None:
    """Checks the Python version is compatible and exits if not."""

    if sys.hexversion < 0x03060000:
        # Python version is less than 3.6
        print("This program requires Python 3.6 or later")
        print("Please update your installation")
        sys.exit(1)


def setup_tui() -> None:
    """Sets up the console for output."""

    # Enable ANSI codes on Windows
    if os.name == "nt":
        import subprocess
        subprocess.call('', shell=True)

    # Handle sigint
    signal.signal(signal.SIGINT, handle_sigint)


def get_settings() -> Profile:
    """Gets the user settings profile for the application, or exits on failure.

    :return: The user settings profile.
    """

    settings_path: str = "~/lecture-hoarder-settings.yaml"
    if len(sys.argv) > 1:
        settings_path = sys.argv[1]  # User has specified custom settings file location

    settings: Profile = Profile()
    try:
        settings.load_from_file(settings_path)
    except IOError:
        # Could not open settings file, use default values
        print("Using default settings")
    except YAMLError as err:
        # Parser error occurred
        if hasattr(err, "context_mark") and hasattr(err, "problem"):
            print(f"Could not parse settings file - bad syntax at line {err.context_mark.line + 1} char "
                  f"{err.context_mark.column + 1}: {err.problem}")
        else:
            print("Could not parse settings file")
        sys.exit(2)
    except TypeError as err:
        # Syntax fine, bad param type
        print(f"Could not load settings file - {err}")
        sys.exit(2)

    return settings


def print_download_queue(queue: List[Download], settings: Profile) -> int:
    """Prints the current download queue to the terminal.

    :param queue:       The current download queue.
    :param settings:    The program settings profile.
    :return:            The output length, for resetting the cursor afterwards.
    """

    # Get terminal size
    if os.name == "nt":
        terminal_width, terminal_height = os.get_terminal_size()  # Windows
    else:
        terminal_width, terminal_height = os.get_terminal_size(0)  # Linux (supports piping)

    # Calculate max length for podcast names
    max_name_length = terminal_width - settings.progress_bar_size - 35

    # Check if we need to truncate the output
    output_length = len(queue)
    truncated = False
    if output_length > terminal_height - 1:
        output_length = terminal_height - 1
        truncated = True

    # Output downloads
    output = ""
    for index in range(output_length):
        download = queue[index]

        output += download.podcast.name[:max_name_length]

        if len(download.podcast.name) > max_name_length:
            output += "..."

        if download.status == DownloadStatus.DOWNLOADING:
            percent = 0
            if download.total_size > 0:
                percent = round((download.progress / download.total_size) * settings.progress_bar_size)

            output += ": Downloading [" + (u"\u2588" * percent) + \
                      (" " * (settings.progress_bar_size - percent)) + "] " + \
                      str(format_size(download.progress)).rjust(6) + " / " + \
                      str(format_size(download.total_size)) + "\n"
        else:
            output += ": " + download.status.value + "\n"

    if truncated:
        output += f"[{len(queue) - output_length} downloads hidden]"

    # Print final output
    print(output, end="", flush=True)

    # Used for resetting the cursor
    return output_length


def print_report(report_complete: List[Download], report_errors: List[Download]) -> None:
    """Prints a report for the completed downloads."""

    download_string = "downloads" if len(report_complete) != 1 else "download"
    print(f"{len(report_complete)} {download_string} completed successfully")

    if len(report_errors) == 0:
        print("No errors occurred")
    else:
        error_string = "errors" if len(report_errors) != 1 else "error"
        print(f"{len(report_errors)} {error_string} occurred:")

        for error_podcast in report_errors:
            print(f"* {error_podcast.podcast.name}: {error_podcast.error_message}")


def main() -> None:
    """The main lecture-hoarder sub-routine."""

    # Check python version
    check_python()

    # Setup command line interface
    setup_tui()

    # Get user settings profile
    settings: Profile = get_settings()

    # Initialise podcast provider
    try:
        web_provider: PodcastProvider = UomPodcastProvider(settings)
    except PodcastProviderError as err:
        # Error initialising provider
        print(err)
        sys.exit(3)

    # Get username and password
    if settings.auto_login:
        username = settings.username
        password = settings.password
    else:
        username = input("Please enter your username: ")
        password = getpass.getpass("Please enter your password: ")

    # Attempt log in
    print("Logging on")

    try:
        if not web_provider.login(username, password):
            # Login unsuccessful
            print("Login incorrect")
            sys.exit(1)
    except PodcastProviderError as err:
        # Error whilst logging on
        print(err)
        sys.exit(3)

    # Login successful

    # Get list of courses from video page
    print("Getting course list")

    try:
        courses = web_provider.get_course_list()
    except PodcastProviderError as err:
        # Error whilst getting course list
        print(err)
        sys.exit(3)

    queue: List[Download] = []  # List of downloads
    futures = []  # List of executable tasks

    for course in courses:
        # For each course

        # Check if course is ignored
        if settings.exclude and re.match(settings.exclude, course.name):
            print("-" * (9 + len(course.name)))
            print(f"Ignoring {course.name}")
            continue

        # Course not ignored, get podcasts
        print("-" * (21 + len(course.name)))
        print(f"Getting podcasts for {course.name}")
        print("-" * (21 + len(course.name)))

        course_dir = os.path.expanduser(os.path.join(settings.base_dir, filter_path_name(course.name)))
        os.makedirs(course_dir, exist_ok=True)

        try:
            podcasts = list(web_provider.get_course_podcasts(course))
        except PodcastProviderError as err:
            # Error whilst getting course podcast list
            print(err)
            continue

        podcast_no = len(podcasts) + 1
        for podcast in podcasts:
            # For each podcast

            podcast_no -= 1

            # Check podcast not already downloaded
            download_path = os.path.expanduser(os.path.join(course_dir,
                                                            f"{podcast_no:02d} - {filter_path_name(podcast.name)}.mp4"))
            if os.path.isfile(download_path):
                print(f"Skipping podcast {podcast.name} (already exists)")
                continue

            # Podcast not yet downloaded, add to queue
            print(f"Queuing podcast {podcast.name}")
            queue.append(Download(podcast, download_path))

    # Start downloads
    print("--------------------")
    print("Downloading podcasts")
    print("--------------------")

    # Terminate early if nothing in queue
    if len(queue) == 0:
        print("Nothing to do")
        sys.exit(0)

    # Print all downloads
    output_length: int = print_download_queue(queue, settings)

    # Add tasks
    with concurrent.futures.ThreadPoolExecutor(max_workers=settings.concurrent_downloads) as executor:
        for download in queue:
            futures.append(executor.submit(download_podcast, download, web_provider))

        # Loop until all downloads completed
        complete_downloads = 0
        total_downloads = len(queue)
        report_complete: List[Download] = []
        report_errors: List[Download] = []
        while complete_downloads < total_downloads:
            # Check whether there are any remaining downloads
            complete_downloads = 0
            for future in futures:
                if future.done():
                    complete_downloads += 1

            # Reset cursor
            print(f"\033[{output_length}F\033[0J", end="")

            # Remove stale downloads
            for download in queue:
                if download.status == DownloadStatus.COMPLETE and time.time() - download.completion_time > 3:
                    report_complete.append(download)
                    queue.remove(download)
                if download.status == DownloadStatus.ERROR and time.time() - download.completion_time > 3:
                    report_errors.append(download)
                    queue.remove(download)

            # Print all downloads
            output_length = print_download_queue(queue, settings)

            # Wait
            time.sleep(0.3)

    # Reset cursor
    print(f"\033[{output_length}F\033[0J", end="")

    # Add remaining downloads to report
    for download in queue:
        if download.status == DownloadStatus.COMPLETE:
            report_complete.append(download)
        elif download.status == DownloadStatus.ERROR:
            report_errors.append(download)
        else:
            print(f"Unexpected status [{download.status.name}] for completed podcast {download.podcast.name}")

    # Print report
    print_report(report_complete, report_errors)


# Run program if started from the command line
if __name__ == "__main__":
    main()
