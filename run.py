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
getLoginService = session.get("https://login.manchester.ac.uk/cas/login")

# Check status code valid
if getLoginService.status_code != 200:
    print("Could not get login page: service responded with status code", getLoginService.status_code)
    sys.exit(1)

# Status code valid, parse HTML
getLoginSoup = BeautifulSoup(getLoginService.content, features="html.parser")
param_execution = getLoginSoup.find("input", {"name": "execution"})["value"]
param_lt = getLoginSoup.find("input", {"name": "lt"})["value"]

# Send login request
print("Logging on")
postLoginService = session.post("https://login.manchester.ac.uk/cas/login",
                                {"username": settings.username,
                                 "password": settings.password,
                                 "lt": param_lt,
                                 "execution": param_execution,
                                 "_eventId": "submit",
                                 "submit": "Login"})

# Check status code valid
if postLoginService.status_code != 200:
    print("Could not log in: service responded with status code", postLoginService.status_code)
    sys.exit(2)

# Status code valid, parse HTML
postLoginSoup = BeautifulSoup(postLoginService.content, features="html.parser")
login_result_div = postLoginSoup.find("div", {"id": "msg"})

# Check if login successful
if "errors" in login_result_div["class"]:
    print("Login failed:", login_result_div.string)
    sys.exit(3)

# Login successful

# Get list of courses from video page
print("Getting course list")
getVideoServiceBase = session.get("https://video.manchester.ac.uk/lectures")

# Check status code valid
if getVideoServiceBase.status_code != 200:
    print("Could not get video service: service responded with status code", getVideoServiceBase.status_code)
    sys.exit(4)

# Status code valid, parse HTML
getVideoServiceBaseSoup = BeautifulSoup(getVideoServiceBase.content, features="html.parser")
first = True
for course_li in getVideoServiceBaseSoup.find("nav", {"id": "sidebar-nav"}).ul.contents[3].find_all("li", {
        "class": "series"}):
    # For each course

    if first:
        first = False
        print("Getting podcasts for", course_li.a.string)
        getVideoServiceCourse = session.get("https://video.manchester.ac.uk" + course_li.a["href"])

        # Check status code valid
        if getVideoServiceCourse.status_code != 200:
            print("Could not get podcasts for", course_li.a.string, "- Service responded with status code",
                  getVideoServiceCourse.status_code)
            continue

        # Success code valid, create directory for podcasts
        course_dir = os.path.expanduser(os.path.join(settings.base_dir, "".join(
            c for c in course_li.a.string if c in VALID_FILE_CHARS)))
        os.makedirs(course_dir, exist_ok=True)

        # Parse HTML
        getVideoServiceCourseSoup = BeautifulSoup(getVideoServiceCourse.content, features="html.parser")
        podcasts = getVideoServiceCourseSoup.find("nav", {"id": "sidebar-nav"}).ul.contents[5].find_all("li", {
                "class": "episode"})
        podcastNo = len(podcasts) + 1
        for podcast_li in podcasts:
            # For each podcast
            podcastNo -= 1

            # Check podcast not already downloaded
            downloadPath = os.path.expanduser(os.path.join(course_dir, f"{podcastNo:02d} - " + podcast_li.a.string +
                                                           ".mp4"))
            if os.path.isfile(downloadPath):
                print("Skipping podcast", podcast_li.a.string, "(already exists)")
                continue

            # Podcast not yet downloaded
            print("Getting podcast", podcast_li.a.string)

            # Get podcast webpage
            getVideoServicePodcastPage = session.get("https://video.manchester.ac.uk" + podcast_li.a["href"])

            # Check status code valid
            if getVideoServicePodcastPage.status_code != 200:
                print("Could not get podcast webpage for", podcast_li.a.string, "- Service responded with status code",
                      getVideoServicePodcastPage.status_code)
                continue

            # Status code valid, parse HTML
            getVideoServicePodcastPageSoup = BeautifulSoup(getVideoServicePodcastPage.content, features="html.parser")
            podcast_src = "https://video.manchester.ac.uk" +\
                          getVideoServicePodcastPageSoup.find("video", id="video").source["src"]

            # Get podcast
            getVideoServicePodcast = session.get(podcast_src, stream=True)

            # Check status code valid
            if getVideoServicePodcast.status_code != 200:
                print("Could not get podcast for", podcast_li.a.string, "- Service responded with status code",
                      getVideoServicePodcastPage.status_code)
                continue

            # Write to file
            with open(downloadPath, "wb") as f:
                getVideoServicePodcast.raw.decode_content = True
                shutil.copyfileobj(getVideoServicePodcast.raw, f)
