from abc import ABC, abstractmethod
from typing import Iterator

import requests

from model import Course, Podcast, Profile


class PodcastProvider(ABC):
    """Provides methods to interact with a generic podcast source.

    Attributes:
        settings_profile    The current settings profile.
    """

    settings_profile: Profile = None

    def __init__(self, settings_profile: Profile):
        """Creates a new instance of the podcast provider.

        :param settings_profile: The current settings profile.
        """
        self.settings_profile = settings_profile

    @abstractmethod
    def login(self, username: str, password: str) -> bool:
        """Logs the user into the provider.

        :param username: The username for the provider.
        :param password: The password for the provider.
        :return: True if logged in, False otherwise.
        """
        pass

    @abstractmethod
    def get_course_list(self) -> Iterator[Course]:
        """Gets the list of available courses.

        :return: A list of course IDs."""
        pass

    @abstractmethod
    def get_course_podcasts(self, course: Course) -> Iterator[Podcast]:
        """Gets the list of available podcasts for the specified course.

        :param course: The course to get the podcasts for.
        :return: A list of podcast IDs.
        """
        pass

    @abstractmethod
    def get_podcast_stream(self, podcast: Podcast) -> requests.Response:
        """Gets the HTTP response for the specified podcast download.

        :param podcast: The podcast to get the download response for.
        """
        pass
