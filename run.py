import concurrent.futures
import os
import requests
import settings
import shutil
import string
import sys
from bs4 import BeautifulSoup

# The list of characters that can be used in filenames
VALID_FILE_CHARS = "-_.() %s%s" % (string.ascii_letters, string.digits)

# Create cookie session
session = requests.session()

# First, get login page for hidden params
print("Getting login page")
get_login_service = session.get("https://login.manchester.ac.uk/cas/login")

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
post_login_service = session.post("https://login.manchester.ac.uk/cas/login",
                                  {"username": settings.username,
                                   "password": settings.password,
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
get_video_service_base = session.get("https://video.manchester.ac.uk/lectures")

# Check status code valid
if get_video_service_base.status_code != 200:
    print("Could not get video service: service responded with status code", get_video_service_base.status_code)
    sys.exit(4)

# Status code valid


# Filters all invalid characters from a file path name
def filter_path_name(path):
    return "".join(c for c in path if c in VALID_FILE_CHARS)


# Downloads a podcast using the href and a target location.
# Logging messages will use the name to identify which podcast download request it is related to.
def download_podcast(name, podcast_link, download_path):
    print("Downloading podcast", name)

    # Get podcast webpage
    get_video_service_podcast_page = session.get("https://video.manchester.ac.uk" + podcast_link)

    # Check status code valid
    if get_video_service_podcast_page.status_code != 200:
        print("Could not get podcast webpage for", name, "- Service responded with status code",
              get_video_service_podcast_page.status_code)
        return

    # Status code valid, parse HTML
    get_video_service_podcast_page_soup = BeautifulSoup(get_video_service_podcast_page.content,
                                                        features="html.parser")
    podcast_src = "https://video.manchester.ac.uk" + \
                  get_video_service_podcast_page_soup.find("video", id="video").source["src"]

    # Get podcast
    get_video_service_podcast = session.get(podcast_src, stream=True)

    # Check status code valid
    if get_video_service_podcast.status_code != 200:
        print("Could not get podcast for", name, "- Service responded with status code",
              get_video_service_podcast.status_code)
        return

    # Write to file with partial extension
    with open(download_path + ".partial", "wb") as f:
        get_video_service_podcast.raw.decode_content = True
        shutil.copyfileobj(get_video_service_podcast.raw, f)

    # Rename completed file
    os.rename(download_path + ".partial", download_path)

    print("Downloaded podcast", name)


with concurrent.futures.ThreadPoolExecutor(max_workers=settings.concurrent_downloads) as executor:
    futures = []

    # Parse HTML
    get_video_service_base_soup = BeautifulSoup(get_video_service_base.content, features="html.parser")

    for course_li in get_video_service_base_soup.find("nav", {"id": "sidebar-nav"}).ul.contents[3].find_all("li", {
            "class": "series"}):
        # For each course
        print("-" * (21 + len(course_li.a.string)))
        print("Getting podcasts for", course_li.a.string)
        print("-" * (21 + len(course_li.a.string)))
        get_video_service_course = session.get("https://video.manchester.ac.uk" + course_li.a["href"])

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
            futures.append(executor.submit(download_podcast, podcast_li.a.string, podcast_li.a["href"], download_path))

    # Wait for all queued podcasts to download
    for idx, future in enumerate(concurrent.futures.as_completed(futures)):
        res = future.result()  # This will also raise any exceptions
