import requests
import settings
import sys
from bs4 import BeautifulSoup

# Create cookie session
session = requests.session()

# First, get login page for hidden params
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
getVideoServiceBase = session.get("https://video.manchester.ac.uk/?login")

# Check status code valid
if getVideoServiceBase.status_code != 200:
    print("Could not get video service: service responded with status code", getVideoServiceBase.status_code)
    sys.exit(4)

# Print result
getVideoServiceBaseSoup = BeautifulSoup(getVideoServiceBase.content, features="html.parser")
print(getVideoServiceBaseSoup.prettify())
