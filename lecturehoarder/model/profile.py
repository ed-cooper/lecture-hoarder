import yaml
import os


class Profile:
    """A settings profile for lecture-hoarder.

    Attributes:
        auto_login                  If true, use the username and password from the settings profile.
        username                    The auto-login username.
        password                    The auto-login password.
        base_dir                    The base directory to save podcasts to.
        concurrent_downloads        The number of podcasts to download simultaneously.
        progress_bar_size           The display length of download progress bars.
        exclude                     A case-sensitive regex expression describing which course names to exclude.
    """

    auto_login: bool = False
    username: str = None
    password: str = None
    base_dir: str = "~/Documents/Lectures"
    concurrent_downloads: int = 4
    progress_bar_size: int = 30
    exclude: str = ""

    def load_from_file(self, file_path: str):
        """Loads a settings profile from the specified YAML file.

        Does not handle file load errors.

        :param file_path: The path to the YAML file.
        """

        # Open file stream
        with open(os.path.expanduser(file_path), "r") as stream:
            # Load and parse yaml
            settings_dict = yaml.safe_load(stream)

            # Import settings
            self.load_from_dict(settings_dict)

    def load_from_dict(self, settings_dict: dict):
        """Loads a settings profile from the supplied dictionary.

        :param settings_dict: The dictionary containing the settings values to load.
        """

        self.load_setting(settings_dict, "auto_login", bool)
        self.load_setting(settings_dict, "username", str)
        self.load_setting(settings_dict, "password", str)
        self.load_setting(settings_dict, "base_dir", str)
        self.load_setting(settings_dict, "concurrent_downloads", int)
        self.load_setting(settings_dict, "progress_bar_size", int)
        self.load_setting(settings_dict, "exclude", str)

    def load_setting(self, settings_dict: dict, setting_name: str, expected_type: type) -> bool:
        """Loads a single setting from a dictionary, if it exists.

        :param settings_dict:   The input dictionary.
        :param setting_name:    The name of the setting to load, matching the dictionary key and attribute name.
        :param expected_type:   The expected type for the setting.
        :return:                True on success, False if setting not found, TypeError if type validation fails.
        """

        # Check key exists
        if setting_name not in settings_dict:
            return False

        # Validate type
        if not isinstance(settings_dict[setting_name], expected_type):
            raise TypeError(f"Setting {setting_name} must be of type {expected_type}")

        # Perform assignment
        setattr(self, setting_name, settings_dict[setting_name])
        return True
