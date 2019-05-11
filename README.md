# Lecture Hoarder

Automated tool to scrape the Univeristy of Manchester video portal and download all
available lecture podcasts for your course.

**Note: Requires valid University of Manchester username and password**

## Usage

First, copy the file `settings-template.py` to `settings.py`

Then, open it in your editor of your choice, and set the following 3 variables:
```python
username = "Your username"        # The username you would usually use for My Manchester
password = "Your password"        # The accompanying password
base_dir = "~/Documents/Lectures" # Where to download files to
```

Then, install the packages listed in [requirements.txt](requirements.txt).

Finally, execute the file called [run.py](run.py) *(requires Python 3.6+)*.

Podcasts take a long time to download, so expect the first run to take over an hour
to complete.

Please do not interrupt the program during downloads, as this will result in
corrupted files which will have to be manually removed.

The program will only download podcasts that you have not already downloaded, meaning
that any subsequent runs (provided you don't change the download directory) will be
much faster.