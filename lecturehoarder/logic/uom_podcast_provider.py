from datetime import datetime
from typing import Iterator

import requests
from bs4 import BeautifulSoup

from logic.podcast_provider import PodcastProvider
from logic.podcast_provider_error import PodcastProviderError
from model import Course, Podcast, Profile


class UomPodcastProvider(PodcastProvider):
    """Provides podcasts from the University of Manchester video service.

    Attributes:
        login_service_url           The URL of the login service.
        session                     The current cookie session, used for maintaining state.
        video_service_base_url      The base URL of the video service.
    """

    login_service_url: str = "https://login.manchester.ac.uk/cas/login"
    video_service_base_url: str = "https://video.manchester.ac.uk"

    session: requests.sessions = None

    def __init__(self, settings_profile: Profile):
        """Creates a new instance of the podcast provider.

        :param settings_profile: The current settings profile.
        """

        super().__init__(settings_profile)

        self.session = requests.session()

    def login(self, username: str, password: str) -> bool:
        """Logs the user into the UOM video service.

        :param username: The username for the service.
        :param password: The password for the service.

        :raises PodcastProviderError: If an error occurs logging in.

        :return: True if logged in, False otherwise.
        """

        # Get login page (to extract hidden params)
        get_login_service = self.session.get(self.login_service_url)

        # Check status code valid
        if get_login_service.status_code != 200:
            raise PodcastProviderError(f"Could not get login page - Service responded with status code "
                                       f"{get_login_service.status_code}")

        # Status code valid, extract hidden parameters
        get_login_soup = BeautifulSoup(get_login_service.content, features="html.parser")
        param_execution = get_login_soup.find("input", {"name": "execution"})["value"]
        param_lt = get_login_soup.find("input", {"name": "lt"})["value"]

        # Send login request
        post_login_service = self.session.post(self.login_service_url,
                                               {"username": username,
                                                "password": password,
                                                "lt": param_lt,
                                                "execution": param_execution,
                                                "_eventId": "submit",
                                                "submit": "Login"})

        # Check status code valid
        if post_login_service.status_code != 200:
            raise PodcastProviderError(f"Could not log in - Service responded with status code "
                                       f"{post_login_service.status_code}")

        # Status code valid, parse HTML
        post_login_soup = BeautifulSoup(post_login_service.content, features="html.parser")
        login_result_div = post_login_soup.find("div", {"id": "msg"})

        # Check if login successful
        return "errors" not in login_result_div["class"]

    def get_course_list(self) -> Iterator[Course]:
        """Gets the list of available courses.

        :raises PodcastProviderError: If an error occurs getting the course list.

        :return: A list of URLs for each course podcast home.
        """

        # Get list of courses from video page
        get_video_service_base = self.session.get(self.video_service_base_url + "/lectures")

        # Check status code valid
        if get_video_service_base.status_code != 200:
            raise PodcastProviderError(f"Could not get video service - Service responded with status code "
                                       f"{get_video_service_base.status_code}")

        # Status code valid, extract courses
        get_video_service_base_soup = BeautifulSoup(get_video_service_base.content, features="html.parser")

        course_items_html = get_video_service_base_soup.find("nav", {"id": "sidebar-nav"}).ul.contents[3]\
            .find_all("li", {"class": "series"})

        return map(lambda x: Course(x.a.string, x.a["href"], x.a.string[-7:].replace("/", "-")), course_items_html)

    def get_course_podcasts(self, course: Course) -> Iterator[Podcast]:
        """Gets the list of available podcasts for the specified course.

        :param course: The course to get the podcasts for.

        :raises PodcastProviderError: If an error occurs getting the course podcasts.

        :return: A list of URLs for podcasts in the course.
        """

        get_video_service_course = self.session.get(self.video_service_base_url + course.url)

        # Check status code valid
        if get_video_service_course.status_code != 200:
            raise PodcastProviderError(f"Could not get podcasts for {course.name} - Service responded with status "
                                       f"code {get_video_service_course.status_code}")

        # Success code valid, extract course names
        get_video_service_course_soup = BeautifulSoup(get_video_service_course.content, features="html.parser")

        podcasts_html = get_video_service_course_soup.find("div", class_="list").find_all("a", class_="outspecify")

        return map(lambda x: Podcast(
            x.find("p", class_="title").string,
            datetime.strptime(x.find("p", class_="date").string, "%a %b %d %X %Z %Y"),
            x["href"]), podcasts_html)

    def get_podcast_downloader(self, podcast: Podcast) -> requests.Response:
        """Gets the HTTP response for the specified podcast download.

        :param podcast: The podcast to get the download response for.

        :raises PodcastProviderError: If an error occurs getting the podcast downloader.
        """

        # Get podcast webpage
        get_video_service_podcast_page = self.session.get(self.video_service_base_url + podcast.url)

        # Check status code valid
        if get_video_service_podcast_page.status_code != 200:
            raise PodcastProviderError(f"Could not get podcast webpage for {podcast.name} - Service responded with "
                                       f"status code {get_video_service_podcast_page.status_code}")

        # Status code valid, parse HTML
        get_video_service_podcast_page_soup = BeautifulSoup(get_video_service_podcast_page.content,
                                                            features="html.parser")

        download_button = get_video_service_podcast_page_soup.find("a", id="downloadButton")

        if not download_button or not download_button["href"]:
            raise PodcastProviderError(f"Could not find download link for podcast {podcast.name}")

        podcast_src = self.video_service_base_url + download_button["href"]

        # Get podcast
        get_video_service_podcast = self.session.get(podcast_src, stream=True)

        # Check status code valid
        if get_video_service_podcast.status_code != 200:
            raise PodcastProviderError(f"Could not get podcast for {podcast.name} - Service responded with "
                                       f"status code {get_video_service_podcast.status_code}")

        return get_video_service_podcast
