import concurrent.futures
import getpass
import os
import re
import requests
import string
import sys
import time
import yaml
from bs4 import BeautifulSoup

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
with open(os.path.expanduser(settings_path), "r") as stream:
    settings = yaml.safe_load(stream)

# Get username and password
if settings["auto_login"]:
    username = settings["username"]
    password = settings["password"]
else:
    username = input("Please enter your username: ")
    password = getpass.getpass("Please enter your password: ")

# Create cookie session
session = requests.session()

# First, get login page for hidden params
print("Getting login page")
get_login_service = session.get(settings["login_service_url"])

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
post_login_service = session.post(settings["login_service_url"],
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
get_video_service_base = session.get(settings["video_service_base_url"] + "/lectures")

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
def download_podcast(podcast):
    # Set starting status
    podcast["status"] = "starting"

    # Get podcast webpage
    get_video_service_podcast_page = session.get(settings["video_service_base_url"] + podcast["podcast_link"])

    # Check status code valid
    if get_video_service_podcast_page.status_code != 200:
        podcast["completion_time"] = time.time()
        podcast["error"] = "Could not get podcast webpage for " + podcast["name"] + \
                           " - Service responded with status code" + get_video_service_podcast_page.status_code
        podcast["status"] = "error"
        return

    # Status code valid, parse HTML
    get_video_service_podcast_page_soup = BeautifulSoup(get_video_service_podcast_page.content,
                                                        features="html.parser")
    podcast_src = settings["video_service_base_url"] + \
        get_video_service_podcast_page_soup.find("video", id="video").source["src"]

    # Get podcast
    get_video_service_podcast = session.get(podcast_src, stream=True)

    # Check status code valid
    if get_video_service_podcast.status_code != 200:
        podcast["completion_time"] = time.time()
        podcast["error"] = "Could not get podcast for " + podcast["name"] + " - Service responded with status code" + \
                           get_video_service_podcast.status_code
        podcast["status"] = "error"
        return

    # Get download size
    podcast["status"] = "started"
    podcast["total_size"] = int(get_video_service_podcast.headers['Content-Length'])

    # Write to file with partial extension
    with open(podcast["download_path"] + ".partial", "wb") as f:
        for chunk in get_video_service_podcast:
            f.write(chunk)
            podcast["progress"] += len(chunk)

    # Rename completed file
    os.rename(podcast["download_path"] + ".partial", podcast["download_path"])

    # Mark as complete
    podcast["completion_time"] = time.time()
    podcast["status"] = "complete"


with concurrent.futures.ThreadPoolExecutor(max_workers=settings["concurrent_downloads"]) as executor:
    queue = []    # List of downloads
    futures = []  # List of executable tasks

    # Parse HTML
    get_video_service_base_soup = BeautifulSoup(get_video_service_base.content, features="html.parser")

    for course_li in get_video_service_base_soup.find("nav", {"id": "sidebar-nav"}).ul.contents[3].find_all("li", {
            "class": "series"}):
        # For each course

        # Check if course is ignored
        if settings["exclude"] and re.match(settings["exclude"], course_li.a.string):
            print("-" * (9 + len(course_li.a.string)))
            print("Ignoring", course_li.a.string)
            continue

        print("-" * (21 + len(course_li.a.string)))
        print("Getting podcasts for", course_li.a.string)
        print("-" * (21 + len(course_li.a.string)))
        get_video_service_course = session.get(settings["video_service_base_url"] + course_li.a["href"])

        # Check status code valid
        if get_video_service_course.status_code != 200:
            print("Could not get podcasts for", course_li.a.string, "- Service responded with status code",
                  get_video_service_course.status_code)
            continue

        # Success code valid, create directory for podcasts
        course_dir = os.path.expanduser(os.path.join(settings["base_dir"], filter_path_name(course_li.a.string)))
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
            queue.append({"name": podcast_li.a.string,
                          "podcast_link": podcast_li.a["href"],
                          "download_path": download_path,
                          "status": "waiting",
                          "error": "",
                          "progress": 0,
                          "total_size": 0,
                          "completion_time": 0})

    # Start downloads
    print("--------------------")
    print("Downloading podcasts")
    print("--------------------")

    # Add tasks
    for download in queue:
        futures.append(executor.submit(download_podcast, download))

    # Get terminal size
    terminal_width, terminal_height = os.get_terminal_size(0)

    # Check if we need to truncate the output
    output_length = len(queue)
    truncated = False
    if output_length > terminal_height - 1:
        output_length = terminal_height - 1
        truncated = True

    # Primary output
    for index in range(output_length):
        print(queue[index]["name"] + ": Waiting")

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
            if download["status"] == "complete" and time.time() - download["completion_time"] > 3:
                report_complete.append(download)
                queue.remove(download)
            if download["status"] == "error" and time.time() - download["completion_time"] > 3:
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
            if download["total_size"] > 0:
                percent = round((download["progress"] / download["total_size"]) * settings["progress_bar_size"])

            output += download["name"]
            if download["status"] == "started":
                output += ": Downloading [" + (u"\u2588" * percent) + \
                    (" " * (settings["progress_bar_size"] - percent)) + "] " + \
                    str(format_size(download["progress"])).rjust(6) + " / " + \
                    str(format_size(download["total_size"])) + "\n"
            elif download["status"] == "starting":
                output += ": Starting" + "\n"
            elif download["status"] == "waiting":
                output += ": Waiting" + "\n"
            elif download["status"] == "complete":
                output += ": Complete" + "\n"
            elif download["status"] == "error":
                output += ": Error" + "\n"
            else:
                output += ": " + download["status"] + "\n"

        if truncated:
            output += f"[{len(queue) - output_length} downloads hidden]"

        print(output, end="", flush=True)

        # Wait
        time.sleep(0.3)

    print("\033[" + str(output_length) + "F\033[0J", end="")

    # Add remaining downloads to report
    for download in queue:
        if download["status"] == "complete":
            report_complete.append(download)
        elif download["status"] == "error":
            report_errors.append(download)
        else:
            print("Unexpected", download["status"], download["name"], download["error"])

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
        for error in report_errors:
            print("- " + error["name"] + ": " + error["error"])
