#!/usr/bin/env python

from __future__ import print_function
from shutil import copyfile
import os, sys, re
import shutil
import urllib, urllib2
import unicodedata
import string

validFilenameChars = "-_.() %s%s" % (string.ascii_letters, string.digits)

def normalizeToFilename(filename):
    cleanedFilename = unicodedata.normalize('NFKD', filename.decode('utf-8')).encode('ASCII', 'ignore')
    return ''.join(c for c in cleanedFilename if c in validFilenameChars)

FIELDS = ["Construction",
    "Body Size",
    "Top Material",
    "Back Material",
    "Side Material",
    "Neck Material",
    "Neck Shape",
    "Neck Taper",
    "Fingerboard Material",
    "Scale Length",
    "Fingerboard Width at Nut",
    "Recommended Strings",
    "Electronics",
    "Left Handed Availability",
]

SELECTOR_FIELDS = [
    "Body Size",
    "Top Material",
    "Back Material",
    "Side Material",
    "Neck Material",
    "Fingerboard Material",
    "Scale Length",
    "Fingerboard Width at Nut",
    "Electronics",
    "Left Handed Availability",
]

fieldstat = dict()
for field in FIELDS:
    fieldstat[field] = set()

dblines = []

RESFOLDER = "../res"
IMAGES_FOLDER = os.path.join(RESFOLDER, 'imgs')
SAVED_GUITARS_DIR = os.path.join("saved", "guitars")

def read_series(subdirname):
    series = re.match(".*/(.*)", subdirname).group(1)
    print("Reading directory {}.".format(subdirname))
    # There should be a directory and a file in this dir.
    files = os.listdir(subdirname)
    the_html_file = None
    the_resource_dir = None
    for name in files:
        filepath = os.path.join(subdirname, name)
        if os.path.isdir(filepath):
            assert the_resource_dir is None
            the_resource_dir = filepath
        elif os.path.isfile(filepath):
            assert the_html_file is None
            the_html_file = filepath
        else:
            assert False, "Nor dir, neither file"

    # Read the html file.
    with open(the_html_file, 'r') as f:
        html_content = f.read()
    matches = re.finditer('<a ng-href="([^"]*)" href="([^"]*)".*?ng-src="([^"]*)".*?class="ng-binding">([^<]*)<.*?class="ng-binding">([^<]*)<', html_content, re.DOTALL)
    for match in matches:
        martinurl = match.group(2)
        imgfilename = re.match(".*/(.*)", match.group(3)).group(1)
        name = match.group(4)
        nname = normalizeToFilename(name)
        print("- " + name)
        price = match.group(5)
        if price.endswith(".00"):
            price = price[:-3]
        # Copy image file to res folder
        imagepath = os.path.join(the_resource_dir, imgfilename)
        copyfile(imagepath, os.path.join(IMAGES_FOLDER, imgfilename))
        # Download guitar page
        saved_guitar_filename = os.path.join(SAVED_GUITARS_DIR, nname);
        if os.path.exists(saved_guitar_filename):
            with open(saved_guitar_filename, 'r') as f:
                html = f.read()
        else:
            response = urllib2.urlopen(martinurl)
            html = response.read()
            with open(saved_guitar_filename, 'w') as f:
                f.write(html)
        dbline = '"{}", "{}", "{}", "{}", "{}", '.format(name, series, martinurl, imgfilename, price)
        for field in FIELDS:
            if field == "Recommended Strings":
                regex = '<strong>{}:</strong>.*?href="#">(.*?)</a>'.format(field)
            else:
                regex = "<strong>{}:</strong>.*?<p>(.*?)</p>".format(field)
            m = re.search(regex, html, re.DOTALL)
            if not m:
                value = "None"
            else:
                value = m.group(1).strip()
            # Normalize value.
            value = value.replace('"', "''").replace("<sup>", "").replace("</sup>", "")
            dbline = dbline + '"' + value + '", '
            fieldstat[field].add(value)
        dblines.append(dbline)

def main(argv):
    if os.path.exists(RESFOLDER):
        shutil.rmtree(RESFOLDER)
    os.mkdir(RESFOLDER)
    os.mkdir(IMAGES_FOLDER)
    if not os.path.exists(SAVED_GUITARS_DIR):
        os.mkdir(SAVED_GUITARS_DIR)
    if len(argv) == 0:
        SERIES_DIR = "saved/series"
        files = os.listdir(SERIES_DIR)
        for name in files:
            dirpath = os.path.join(SERIES_DIR, name)
            read_series(dirpath)
    elif len(argv) == 1:
        read_series(argv[0])
    else:
        assert False, "2 or more args"
    for k in fieldstat:
        print("{}: {}".format(k, fieldstat[k]))
    with open(os.path.join(RESFOLDER, "guitardb.js"), 'w') as f:
        f.write("const guitarDb = [\n")
        for dbline in dblines:
            f.write("[" + dbline + "],\n")
        f.write("];\n")
if __name__ == "__main__":
    main(sys.argv[1:])
