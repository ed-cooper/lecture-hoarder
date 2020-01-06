# Lecture Hoarder [![Build Status](https://travis-ci.com/ed-cooper/lecture-hoarder.svg?branch=master)](https://travis-ci.com/ed-cooper/lecture-hoarder)

Automated tool to scrape the University of Manchester video portal and download all
available lecture podcasts for your course.

**Note: Requires valid University of Manchester username and password**

## Use at your own risk

Lecture Hoarder relies on an unstable web interface that is liable to change.

This program comes with ABSOLUTELY NO WARRANTY; for details see [the license](LICENSE).
The author accepts no liability for any loss of data caused by this program.
Please remember to back your files up regularly.

## Installation

*Requires Python 3.6+*

1) Clone the repository
```bash
git clone git@github.com:ed-cooper/lecture-hoarder.git
```

2) Go to the install directory
```bash
cd lecture-hoarder
```

3) Install the dependencies
```bash
pip3 install -r requirements.txt
```

# Simple Usage

Inside your installation directory, run:
```bash
python3 lecturehoarder
```

Podcasts are downloaded to `~/Documents/Lectures`.

# Advanced Usage

Lecture Hoarder can be configured by placing a `lecture-hoarder-settings.yaml` file
in your home directory - e.g. `/home/john/lecture-hoarder-settings.yaml` on Linux.

Configuration options include:
* Changing the download directory
* Excluding certain courses from being downloaded
* Pre-specifying a username / password combination
* And more

For information on configuration, please see
[the wiki page](https://github.com/ed-cooper/lecture-hoarder/wiki/Lecture-Hoarder-Configuration).

# Useful Notes
Podcasts take a long time to download, so the first run may take a while to complete.

If you interrupt the program while downloading, you may find ```.partial``` files in
the output directory. They are incomplete downloads and can safely be ignored/deleted.

The program will only download podcasts that you have not already downloaded, meaning
that any subsequent runs (provided you don't change the download directory) will be
much faster.
