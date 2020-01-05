"""Main command line entry point for lecturehoarder."""

import concurrent.futures
import getpass
import os
import re
import string
import sys
import time

from logic import PodcastProvider, PodcastProviderError, UomPodcastProvider
from model import Download, DownloadStatus, Profile

# Check python version
if sys.hexversion < 0x03060000:
    # Python version is less than 3.6
    print("This program requires Python 3.6 or later")
    print("Please update your installation")
    sys.exit(1)

# Enable ANSI codes on Windows
if os.name == "nt":
    import subprocess
    subprocess.call('', shell=True)

# The list of characters that can be used in filenames
VALID_FILE_CHARS = f"-_.() {string.ascii_letters}{string.digits}"

# Get user settings
settings_path = "~/lecture-hoarder-settings.yaml"
if len(sys.argv) > 1:
    settings_path = sys.argv[1]  # User has specified custom settings file location

settings = Profile()
settings.load_from_file(settings_path)

# Get username and password
if settings.auto_login:
    username = settings.username
    password = settings.password
else:
    username = input("Please enter your username: ")
    password = getpass.getpass("Please enter your password: ")

# Initialise podcast provider
try:
    web_provider: PodcastProvider = UomPodcastProvider(settings)
except PodcastProviderError as err:
    # Error whilst logging on
    print(err)
    sys.exit(2)

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
    sys.exit(4)


# Filters all invalid characters from a file path name
def filter_path_name(path):
    return "".join(c for c in path if c in VALID_FILE_CHARS)


# Formats a download size as MB
def format_size(size_in_bytes):
    return str(round(size_in_bytes / (1000 * 1000))) + " MB"


# Downloads a podcast using the href and a target location.
# Logging messages will use the name to identify which podcast download request it is related to.
def download_podcast(download: Download):
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


queue = []    # List of downloads
futures = []  # List of executable tasks

for course in courses:
    # For each course

    # Check if course is ignored
    if settings.exclude and re.match(settings.exclude, course.name):
        print("-" * (9 + len(course.name)))
        print("Ignoring", course.name)
        continue

    # Course not ignored, get podcasts
    print("-" * (21 + len(course.name)))
    print("Getting podcasts for", course.name)
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
        download_path = os.path.expanduser(os.path.join(course_dir, f"{podcast_no:02d} - " +
                                                        filter_path_name(podcast.name) + ".mp4"))
        if os.path.isfile(download_path):
            print("Skipping podcast", podcast.name, "(already exists)")
            continue

        # Podcast not yet downloaded, add to queue
        print("Queuing podcast", podcast.name)
        queue.append(Download(podcast, download_path))

# Start downloads
print("--------------------")
print("Downloading podcasts")
print("--------------------")

# Terminate early if nothing in queue
if len(queue) == 0:
    print("Nothing to do")
    sys.exit(0)

# Add tasks
with concurrent.futures.ThreadPoolExecutor(max_workers=settings.concurrent_downloads) as executor:
    for download in queue:
        futures.append(executor.submit(download_podcast, download))

    # Get terminal size
    if os.name == "nt":
        terminal_width, terminal_height = os.get_terminal_size()  # Windows
    else:
        terminal_width, terminal_height = os.get_terminal_size(0)  # Linux (supports piping)

    # Check if we need to truncate the output
    output_length = len(queue)
    truncated = False
    if output_length > terminal_height - 1:
        output_length = terminal_height - 1
        truncated = True

    # Primary output
    for index in range(output_length):
        print(queue[index].podcast.name + ": Waiting")

    if truncated:
        print(f"[{len(queue) - output_length} downloads hidden]", end="")

    # Loop until all downloads completed
    complete_downloads = 0
    total_downloads = len(queue)
    report_complete = []
    report_errors = []
    while complete_downloads < total_downloads:
        # Check whether there are any remaining downloads
        complete_downloads = 0
        for future in futures:
            if future.done():
                complete_downloads += 1

        # Reset cursor
        output = "\033[" + str(output_length) + "F\033[0J"

        # Remove stale downloads
        for download in queue:
            if download.status == DownloadStatus.COMPLETE and time.time() - download.completion_time > 3:
                report_complete.append(download)
                queue.remove(download)
            if download.status == DownloadStatus.ERROR and time.time() - download.completion_time > 3:
                report_errors.append(download)
                queue.remove(download)

        # Check if we need to truncate downloads
        output_length = len(queue)
        truncated = False
        if output_length > terminal_height - 1:
            output_length = terminal_height - 1
            truncated = True

        # Output downloads
        for index in range(output_length):
            download = queue[index]
            percent = 0
            if download.total_size > 0:
                percent = round((download.progress / download.total_size) * settings.progress_bar_size)

            output += download.podcast.name
            if download.status == DownloadStatus.DOWNLOADING:
                output += ": Downloading [" + (u"\u2588" * percent) + \
                    (" " * (settings.progress_bar_size - percent)) + "] " + \
                    str(format_size(download.progress)).rjust(6) + " / " + \
                    str(format_size(download.total_size)) + "\n"
            else:
                output += ": " + download.status.value + "\n"

        if truncated:
            output += f"[{len(queue) - output_length} downloads hidden]"

        print(output, end="", flush=True)

        # Wait
        time.sleep(0.3)

    print("\033[" + str(output_length) + "F\033[0J", end="")

    # Add remaining downloads to report
    for download in queue:
        if download.status == DownloadStatus.COMPLETE:
            report_complete.append(download)
        elif download.status == DownloadStatus.ERROR:
            report_errors.append(download)
        else:
            print(f"Unexpected status [{download.status.name}] for completed podcast {download.podcast.name}")

    download_string = "downloads"
    if len(report_complete) == 1:
        download_string = "download"

    print(f"{len(report_complete)} {download_string} completed successfully")

    if len(report_errors) == 0:
        print("No errors occurred")
    else:
        error_string = "errors"
        if len(report_errors) == 1:
            error_string = "error"

        print(f"{len(report_errors)} {error_string} occurred:")
        for error_podcast in report_errors:
            print(f"* {error_podcast.podcast.name}: {error_podcast.error_message}")
