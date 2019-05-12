# Lecture Hoarder [![Build Status](https://travis-ci.com/ed-cooper/lecture-hoarder.svg?branch=master)](https://travis-ci.com/ed-cooper/lecture-hoarder)

Automated tool to scrape the University of Manchester video portal and download all
available lecture podcasts for your course.

**Note: Requires valid University of Manchester username and password**

## Use at your own risk

Lecture Hoarder relies on an unstable web interface that is liable to change.

This program comes with ABSOLUTELY NO WARRANTY; for details see [the license](LICENSE).
The author accepts no liability for any loss of data caused by this program.
Please remember to back your files up regularly.

## Usage

First, copy the file `settings-template.py` to `settings.py`

Then, open it in your editor of your choice, and set the following 4 variables:
```python
username = "Your username"        # The username you would usually use for My Manchester
password = "Your password"        # The accompanying password
base_dir = "~/Documents/Lectures" # Where to download files to
concurrent_downloads = 4          # How many podcasts to download at the same time (Increases speed)
```

Then, install the packages listed in [requirements.txt](requirements.txt).

Finally, execute the file called [run.py](run.py) *(requires Python 3.6+)*.

Podcasts take a long time to download, so expect the first run to take over an hour
to complete.

If you interrupt the program while downloading, you may find ```.partial``` files in
the output directory. They are incomplete downloads and can safely be ignored/deleted.

The program will only download podcasts that you have not already downloaded, meaning
that any subsequent runs (provided you don't change the download directory) will be
much faster.