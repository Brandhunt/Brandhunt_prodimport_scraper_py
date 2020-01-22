'''from collections import namedtuple
import datetime as dt
from functools import reduce
import itertools as it
import re
import sqlite3
from urllib.parse import parse_qs, urljoin, urlparse, quote as urlquote

from selenium.common.exceptions import WebDriverException
from splinter import Browser'''

import logging
import scraperwiki
import sqlite3
import time
import urllib2
import lxml.html
from splinter import Browser
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options

# This is a template for a Python scraper on morph.io (https://morph.io)
# including some code snippets below that you should find helpful

# import scraperwiki
# import lxml.html
#
# # Read in a page
# html = scraperwiki.scrape("http://foo.com")
#
# # Find something on the page using css selectors
# root = lxml.html.fromstring(html)
# root.cssselect("div[align='left']")
#
# # Write out to the sqlite database using scraperwiki library
# scraperwiki.sqlite.save(unique_keys=['name'], data={"name": "susan", "occupation": "software developer"})
#
# # An arbitrary query against the database
# scraperwiki.sql.select("* from data where 'name'='peter'")

# You don't have to do things with the ScraperWiki and lxml libraries.
# You can use whatever libraries you want: https://morph.io/documentation/python
# All that matters is that your final data is written to an SQLite database
# called "data.sqlite" in the current working directory which has at least a table
# called "data".

#import warnings
#warnings.filterwarnings("ignore")

options = Options()
options.add_argument('--disable-extensions')
options.add_argument('--no-sandbox')

hend = 'CHANGE'
print('HEPP')
#browser = Browser("phantomjs")
with Browser('chrome', headless=True, options=options) as browser:
    browser.driver.set_window_size(1920, 1080)
    try:
        browser.visit('https://morph.io')
        hend = browser.html
        #text = browser.find_by_css('button.btn-primary')
        #hend = text
        #for t in text:
            #print(t)
            #print(t.text)
            #print(t.html)
            #hend = t['href']
        except:
            print('HAPP')
print('HUPP')
print(hend)
