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

SRC_FIELDS = [
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

DB_FIELDS = [
    "Name",
    "URL",
    "Image",
    "Price",
    "Body Size",
    "Top Material",
    "Back/Side Material",
    "Neck Material",
    "Neck Shape",
    "Neck Taper",
    "Fingerboard Material",
    "Scale Length",
    "Fingerboard Width at Nut",
    "Recommended Strings",
    "Electronics",
    "Left Handed Availability",
    "Price Range",
    "Electronics Availability",
    "Product Group",
    "Simplified Body Size",
    "Series List"
]

SELECTOR_FIELDS = [
    "Product Group",
    "Series",
    "Body Size",
    "Price Range",
    "Top Material",
    "Back/Side Material",
    "Fingerboard Material",
    "Scale Length",
    "Fingerboard Width at Nut",
    "Electronics Availability",
    "Left Handed Availability",
]

TABLE_FIELDS = [
    "Body Size",
    "Top Material",
    "Back/Side Material",
    "Neck Material",
    "Neck Shape",
    "Neck Taper",
    "Fingerboard Material",
    "Scale Length",
    "Fingerboard Width at Nut",
    "Recommended Strings",
    "Left Handed Availability",
    "Electronics",
]

SERIES_RENAME = {
    'new-models': 'New',
    'authentic-vintage': 'Authentic',
    'discontinued-guitars': 'Discontinued',
    'performing-artist-series': 'Performing',
    'ukulele': 'Ukulele',
    'retro-series': 'Retro',
    'little-martin': 'Little',
    'fsc-certified': 'FSC',
    'x-series': 'X',
    'road-series': 'Road',
    '16-series': '16',
    'custom-signature-editions': 'Signature',
    '15-series': '15',
    'special-editions': 'Special',
    'backpacker': 'Backpacker',
    '17-series': '17',
    'standard-series': 'Standard',
    'limited-editions': 'Limited',
    'junior': 'Junior',
    'standard-series-reimagined-2018': 'Standard-2018'
}

fieldstat = dict()
for field in (SELECTOR_FIELDS + TABLE_FIELDS):
    fieldstat[field] = set()

RESFOLDER = "../res"
IMAGES_FOLDER = os.path.join(RESFOLDER, 'imgs')
SAVED_GUITARS_DIR = os.path.join("saved", "guitars")

name_to_url = {}
name_to_series_list = {}
name_to_dbline = {}

def deescape(s):
    return s.replace("&amp;", "&").replace("&#39;", "'")

def read_series(subdirname):
    series = re.match(".*/(.*)", subdirname).group(1)
    series = SERIES_RENAME[series]
    assert series is not None
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
        name = deescape(match.group(4))
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
        dbline = '"{}", "{}", "{}", "{}", '.format(name, martinurl, imgfilename, price)

        if name in name_to_url:
            assert martinurl == name_to_url[name]
            name_to_series_list[name].append(series)
        else:
            name_to_url[name] = martinurl
            name_to_series_list[name] = [series]

        back_material = None
        electronics_value = None
        twelve_strings = None
        simplified_body_size = None
        for field in SRC_FIELDS:
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

            if field == "Back Material":
                back_material = value
                continue

            if field == "Side Material":
                assert back_material is not None
                if back_material != value:
                    value = back_material + " / " + value
                field = "Back/Side Material"
                if value == "Honduras Rosewood / Madagascar Rosewood":
                    value = "Honduras/Madagascar Rosewood"
            elif field == "Electronics":
                if value in ['Not Available', 'N/A']:
                    value = 'None'
                electronics_value = value
            elif field == "Recommended Strings":
                value = deescape(value)
                twelve_strings = "12-String" in value
            elif field == "Body Size":
                if value.startswith("0-"):
                    simplified_body_size = "0"
                elif value.startswith("00-"):
                    simplified_body_size = "00"
                elif value.startswith("000-"):
                    simplified_body_size = "000"
                elif value == "Backpacker":
                    simplified_body_size = "Backpacker"
                elif "Ukulele" in value:
                    simplified_body_size = "Ukulele"
                elif value.startswith("D Junior"):
                    simplified_body_size = "D Jr"
                elif value.startswith("D-"):
                    simplified_body_size = "D"
                elif value.startswith("Grand J-"):
                    simplified_body_size = "Grand J"
                elif value.startswith("Grand Performance"):
                    simplified_body_size = "Grand Performance"
                elif value.startswith("J-"):
                    simplified_body_size = "J"
                elif value.startswith("M-"):
                    simplified_body_size = "M (0000)"
                elif value.startswith("Modified"):
                    simplified_body_size = "M (0)"
                else:
                    assert False

            dbline = dbline + '"' + value + '", '
            if field in fieldstat:
                fieldstat[field].add(value)

        field = "Price Range"
        price_value = int(''.join([c for c in price if c.isdigit()]))
        if price_value < 1000:
            price_range = "below $1,000"
        elif price_value >= 5000:
            price_range = "above $5,000"
        else:
            price_range = "$" + str(price_value // 1000) + ",999"

        dbline = dbline + '"' + price_range + '", '
        if field in fieldstat:
            fieldstat[field].add(price_range)

        field = "Electronics Availability"
        assert electronics_value is not None
        if electronics_value in ["None", "Optional"]:
            value = electronics_value
        else:
            value = "Yes"

        dbline = dbline + '"' + value + '", '
        if field in fieldstat:
            fieldstat[field].add(value)

        field = "Series"
        if field in fieldstat:
            fieldstat[field].add(series)

        assert simplified_body_size is not None

        if "Backpacker" in simplified_body_size:
            pg = "Backpacker"
        elif "Ukulele" in simplified_body_size:
            pg = "Ukulele"
        else:
            assert twelve_strings is not None
            if twelve_strings:
                pg = "12-String"
            else:
                pg = "6-String"

        dbline = dbline + '"' + pg + '", '
        field = "Product Group"
        if field in fieldstat:
            fieldstat[field].add(pg)

        dbline = dbline + '"' + simplified_body_size + '", '
        field = "Simplified Body Size"
        if field in fieldstat:
            fieldstat[field].add(simplified_body_size)

        if name in name_to_dbline:
            if name_to_dbline[name] != dbline:
                print("This guitar: {} changed series: {}"
                    .format(name, name_to_series_list[name]))
            assert name_to_dbline[name] == dbline
        else:
            name_to_dbline[name] = dbline

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
        print("# {}: {}\n".format(k, fieldstat[k]))
    with open(os.path.join(RESFOLDER, "guitardb.js"), 'w') as f:
        f.write("const guitarDb = [\n")
        for name in name_to_dbline:
            dbline = name_to_dbline[name]
            series = name_to_series_list[name]
            assert series is not None
            f.write('[{}" {} "],\n'.format(dbline, ' '.join(series)))
        f.write("];\n")
        f.write("const guitarDbFields = [\n")
        for field in DB_FIELDS:
            f.write('"' + field + '", ')
        f.write("];\n")
        f.write("const tableFields = [\n")
        for field in TABLE_FIELDS:
            f.write('"' + field + '", ')
        f.write("];\n")
        f.write("const tableFieldToDbIndices = [\n")
        for field in TABLE_FIELDS:
            f.write(str(DB_FIELDS.index(field)) + ', ')
        f.write("];\n")
    print("- name_to_series_list - ")
    for n in name_to_series_list:
        sl = name_to_series_list[n]
        if len(sl) > 1:
            print("{}: {}".format(n, sl))
if __name__ == "__main__":
    main(sys.argv[1:])
