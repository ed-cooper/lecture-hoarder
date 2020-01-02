"""Main command line entry point for lecturehoarder."""

import concurrent.futures
import getpass
import os
import re
import string
import sys
import time

import requests
from bs4 import BeautifulSoup

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

# Create cookie session
session = requests.session()

# First, get login page for hidden params
print("Getting login page")
get_login_service = session.get(settings.login_service_url)

# Check status code valid
if get_login_service.status_code != 200:
    print("Could not get login page: service responded with status code", get_login_service.status_code)
    sys.exit(1)

# Status code valid, parse HTML
get_login_soup = BeautifulSoup(get_login_service.content, features="html.parser")
param_execution = get_login_soup.find("input", {"name": "execution"})["value"]
param_lt = get_login_soup.find("input", {"name": "lt"})["value"]

# Send login request
print("Logging on")
post_login_service = session.post(settings.login_service_url,
                                  {"username": username,
                                   "password": password,
                                   "lt": param_lt,
                                   "execution": param_execution,
                                   "_eventId": "submit",
                                   "submit": "Login"})

# Check status code valid
if post_login_service.status_code != 200:
    print("Could not log in: service responded with status code", post_login_service.status_code)
    sys.exit(2)

# Status code valid, parse HTML
post_login_soup = BeautifulSoup(post_login_service.content, features="html.parser")
login_result_div = post_login_soup.find("div", {"id": "msg"})

# Check if login successful
if "errors" in login_result_div["class"]:
    print("Login failed:", login_result_div.string)
    sys.exit(3)

# Login successful

# Get list of courses from video page
print("Getting course list")
get_video_service_base = session.get(settings.video_service_base_url + "/lectures")

# Check status code valid
if get_video_service_base.status_code != 200:
    print("Could not get video service: service responded with status code", get_video_service_base.status_code)
    sys.exit(4)

# Status code valid


# Filters all invalid characters from a file path name
def filter_path_name(path):
    return "".join(c for c in path if c in VALID_FILE_CHARS)


# Formats a download size as MB
def format_size(size_in_bytes):
    return str(round(size_in_bytes / (1000 * 1000))) + " MB"


# Downloads a podcast using the href and a target location.
# Logging messages will use the name to identify which podcast download request it is related to.
def download_podcast(podcast: Download):
    # Set starting status
    podcast.status = DownloadStatus.STARTING

    # Get podcast webpage
    get_video_service_podcast_page = session.get(settings.video_service_base_url + podcast.podcast_link)

    # Check status code valid
    if get_video_service_podcast_page.status_code != 200:
        podcast.set_error(f"Could not get podcast webpage for {podcast.name}"
                          f" - Service responded with status code {get_video_service_podcast_page.status_code}")
        return

    # Status code valid, parse HTML
    get_video_service_podcast_page_soup = BeautifulSoup(get_video_service_podcast_page.content,
                                                        features="html.parser")

    download_button = get_video_service_podcast_page_soup.find("a", id="downloadButton")

    if not download_button or not download_button["href"]:
        podcast.set_error(f"Could not find download link for podcast {podcast.name}")
        return

    podcast_src = settings.video_service_base_url + download_button["href"]

    # Get podcast
    get_video_service_podcast = session.get(podcast_src, stream=True)

    # Check status code valid
    if get_video_service_podcast.status_code != 200:
        podcast.set_error(f"Could not get podcast for {podcast.name} - Service responded with status code "
                          f"{get_video_service_podcast.status_code}")
        return

    # Get download size
    podcast.status = DownloadStatus.DOWNLOADING
    podcast.total_size = int(get_video_service_podcast.headers['Content-Length'])

    # Write to file with partial extension
    with open(podcast.download_path + ".partial", "wb") as f:
        for chunk in get_video_service_podcast:
            f.write(chunk)
            podcast.progress += len(chunk)

    # Rename completed file
    os.rename(podcast.download_path + ".partial", podcast.download_path)

    # Mark as complete
    podcast.set_complete()


queue = []    # List of downloads
futures = []  # List of executable tasks

# Parse HTML
get_video_service_base_soup = BeautifulSoup(get_video_service_base.content, features="html.parser")

for course_li in get_video_service_base_soup.find("nav", {"id": "sidebar-nav"}).ul.contents[3].find_all("li", {
        "class": "series"}):
    # For each course

    # Check if course is ignored
    if settings.exclude and re.match(settings.exclude, course_li.a.string):
        print("-" * (9 + len(course_li.a.string)))
        print("Ignoring", course_li.a.string)
        continue

    print("-" * (21 + len(course_li.a.string)))
    print("Getting podcasts for", course_li.a.string)
    print("-" * (21 + len(course_li.a.string)))
    get_video_service_course = session.get(settings.video_service_base_url + course_li.a["href"])

    # Check status code valid
    if get_video_service_course.status_code != 200:
        print("Could not get podcasts for", course_li.a.string, "- Service responded with status code",
              get_video_service_course.status_code)
        continue

    # Success code valid, create directory for podcasts
    course_dir = os.path.expanduser(os.path.join(settings.base_dir, filter_path_name(course_li.a.string)))
    os.makedirs(course_dir, exist_ok=True)

    # Parse HTML
    get_video_service_course_soup = BeautifulSoup(get_video_service_course.content, features="html.parser")
    podcasts = get_video_service_course_soup.find("nav", {"id": "sidebar-nav"}).ul.contents[5].find_all("li", {
        "class": "episode"})
    podcast_no = len(podcasts) + 1
    for podcast_li in podcasts:
        # For each podcast
        podcast_no -= 1

        # Check podcast not already downloaded
        download_path = os.path.expanduser(os.path.join(course_dir, f"{podcast_no:02d} - " +
                                                        filter_path_name(podcast_li.a.string) + ".mp4"))
        if os.path.isfile(download_path):
            print("Skipping podcast", podcast_li.a.string, "(already exists)")
            continue

        # Podcast not yet downloaded
        print("Queuing podcast", podcast_li.a.string)

        # Queue podcast for downloading
        queue.append(Download(
            name=podcast_li.a.string,
            podcast_link=podcast_li.a["href"],
            download_path=download_path
        ))

# Start downloads
print("--------------------")
print("Downloading podcasts")
print("--------------------")

# Terminate early if nothing in queue
if len(queue) == 0:
    print("Nothing to do")
    sys.exit(1)

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
        print(queue[index].name + ": Waiting")

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

            output += download.name
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
            print(f"Unexpected status [{download.status.name}] for completed podcast {download.name}")

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
            print("* " + error_podcast.name + ": " + error_podcast.error_message)
