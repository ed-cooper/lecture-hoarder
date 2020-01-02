import requests

from logic.podcast_provider import PodcastProvider
from model import Profile


class UomPodcastProvider(PodcastProvider):
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
        :return: True if logged in, False otherwise.
        """
        pass

    def get_course_list(self):
        """Gets the list of available courses.

        :return: A list of URLs for each course podcast home."""
        pass

    def get_course_podcasts(self, course_id: str):
        """Gets the list of available podcasts for the specified course.

        :param course_id: The identifier for the course to get the podcasts for.
        :return: A list of URLs for podcasts in the course.
        """
        pass

    def get_podcast_stream(self, podcast_id: str):
        """Gets the download stream for the specified podcast.

        :param podcast_id: The URL of the podcast to get the stream for.
        """
        pass
