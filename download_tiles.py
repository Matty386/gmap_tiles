#!/usr/bin/python

import urllib.request, urllib.error, urllib.parse
import os, sys
from gmap_utils import *

import threading

try:
    from fake_useragent import UserAgent  # https://github.com/hellysmile/fake-useragent
    print("Using random user agents.")
except:
    print("Using default user agent.")
    pass

import time
import random
from tqdm import tqdm
import numpy as np


def downloadTiles(source, zoom, xxx_todo_changeme, max_threads=1, DEBUG=True, ERR=True):
    (lat_start, lat_stop, lon_start, lon_stop) = xxx_todo_changeme
    try:
        ua = UserAgent()
    except:
        pass
    spawn_count = 0
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
    user_agent = "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_9; us-at) AppleWebKit/533.23.1 (KHTML, like Gecko) Version/5.0.5 Safari/533.21.3"
    headers = {"User-Agent": user_agent}

    x_range = range(start_x, stop_x)
    y_range = range(start_y, stop_y)
    xy_range = np.array(np.meshgrid(x_range, y_range)).T.reshape(-1, 2)

    for x, y in tqdm(xy_range):
        filename = "%s_%s_%d_%d_%d.%s" % (key, ext["type"], zoom, x, y, ext["ext"])
        url = ""
        url += str(ext["prefix"])
        url += str(ext["x"]) + str(x)
        url += str(ext["y"]) + str(y)
        url += str(ext["zoom"]) + str(zoom)
        url += str(ext["postfix"])
        if not os.path.exists(filename):
            try:
                user_agent = ua.random
            except UnboundLocalError:
                pass
            if max_threads > 1:
                threads = []
                for i in range(max_threads):
                    try:
                        user_agent = ua.random
                        headers = {"User-Agent": user_agent}
                    except UnboundLocalError:
                        pass
                    t = threading.Thread(
                        target=worker, args=(url, filename, user_agent, headers)
                    )
                    threads.append(t)
                    t.start()
                    spawn_count += 1
                    time.sleep(random.random() / max_threads)
                if DEBUG:
                    x_percent = float((start_x - x)) / float(start_x - stop_x)
                    y_percent = float((start_y - y)) / float(start_y - stop_y)
                for i in range(len(threads)):
                    threads[i].join()
            else:
                worker(url, filename, user_agent, headers)
            time.sleep(1 + random.random())


def worker(url, filename, user_agent, headers, DEBUG=False, ERR=True):
    if os.path.isfile(filename):
        return  # is already downloaded
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
