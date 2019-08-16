#!/usr/bin/python

import urllib.request, urllib.error, urllib.parse
import os, sys
from gmap_utils import *

try:
    from fake_useragent import UserAgent  # https://github.com/hellysmile/fake-useragent
    print("Using random user agents.")
except ImportError:
    print("Using default user agent.")

import time
import random
from tqdm import tqdm
import numpy as np
from multiprocessing.pool import ThreadPool


def downloadTiles(source, zoom, xxx_todo_changeme, max_threads=1, DEBUG=True, ERR=True):
    (lat_start, lat_stop, lon_start, lon_stop) = xxx_todo_changeme
    if len(source) != 1:
        if ERR:
            print("-- unknown data source")
        return
    key = list(source.keys())[0]
    ext = source[key]
    start_x, start_y = latlon2xy(zoom, lat_start, lon_start)
    stop_x, stop_y = latlon2xy(zoom, lat_stop, lon_stop)
    if DEBUG:
        print("x range", start_x, stop_x)
    if DEBUG:
        print("y range", start_y, stop_y)
    if DEBUG:
        print("Total Tiles: ", (stop_x - start_x) * (stop_y - start_y))

    x_range = range(start_x, stop_x)
    y_range = range(start_y, stop_y)
    xy_range = np.array(np.meshgrid(x_range, y_range)).T.reshape(-1, 2)

    filenames = list()
    urls = list()
    for x, y in xy_range:
        filename = "%s_%s_%d_%d_%d.%s" % (key, ext["type"], zoom, x, y, ext["ext"])
        url = ""
        url += str(ext["prefix"])
        url += str(ext["x"]) + str(x)
        url += str(ext["y"]) + str(y)
        url += str(ext["zoom"]) + str(zoom)
        url += str(ext["postfix"])
        filenames.append(filename)
        urls.append(url)

    with ThreadPool(max_threads) as pool:
        data = zip(urls, filenames)
        list(tqdm(pool.imap(worker_wait_unpack, data), total=len(urls)))


def get_user_agent():
    try:
        ua = UserAgent()
        user_agent = ua.random
    except NameError:  # UserAgent not defined
        user_agent = "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_9; us-at) AppleWebKit/533.23.1 (KHTML, like Gecko) Version/5.0.5 Safari/533.21.3"
    return user_agent


def worker(url, filename, DEBUG=False, ERR=True):
    user_agent = get_user_agent()
    headers = {"User-Agent": user_agent}
    try:
        req = urllib.request.Request(url, data=None, headers=headers)
        response = urllib.request.urlopen(req)
        received_bytes = response.read()
    except Exception as e:
        if ERR:
            print("--", filename, "->", e)
        sys.exit(1)
    if received_bytes.startswith(b"<html>"):
        if ERR:
            print("-- Forbidden", filename)
        sys.exit(1)
    if DEBUG:
        print("-- Saving", filename)
    f = open(filename, "wb")
    f.write(received_bytes)
    f.close()


def worker_wait_unpack(data):
    url, filename = data
    if not os.path.exists(filename):
        worker(url, filename)
        time.sleep(1 + random.random())


def main():
    from sources import searchSource, ppjson

    found_sources = searchSource("sources.json", search={"type": "sat"})
    key = list(found_sources.keys())[0]
    source = {key: found_sources[key]}
    ppjson(source)
    zoom = 10
    lat_start, lon_start = 36.99, -114.03
    lat_stop, lon_stop = 35.64, -111.60
    downloadTiles(source, zoom, (lat_start, lat_stop, lon_start, lon_stop))


if __name__ == "__main__":
    main()
