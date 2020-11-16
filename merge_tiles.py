from PIL import Image
import sys, os
from gmap_utils import *


def mergeTiles(source, zoom, coord_yyxx, method):
    (y_lat_start, y_lat_stop, x_lon_start, x_lon_stop) = coord_yyxx
    if len(source) != 1:
        print("-- unknown external source")
        return
    key = list(source.keys())[0]
    ext = source[key]
    TYPE = ext["type"]
    EXT = ext["ext"]
    tile_size = 256
    #tile_size = 254 # rare maps overlap

    if "coord" in method: 
        x_start, y_start = latlon2xy(zoom, y_lat_start, x_lon_start)
        x_stop, y_stop = latlon2xy(zoom, y_lat_stop, x_lon_stop)
    else:
        print("zxy_path")
        # zoom = 6 x=1-62  y=1-56
        x_start = x_lon_start
        x_stop = x_lon_stop

        y_start = y_lat_start
        y_stop = y_lat_stop



    print("x range", x_start, x_stop)
    print("y range", y_start, y_stop)
    w = (x_stop - x_start) * tile_size
    h = (y_stop - y_start) * tile_size
    print("width:", w)
    print("height:", h)
    result = Image.new("RGB", (w, h))
    for x in range(x_start, x_stop):
        for y in range(y_start, y_stop):
            filename = "export/%s/%s_%s_%d_%d_%d.%s" % (key, key, TYPE, zoom, x, y, EXT)
            if not os.path.exists(filename):
                print("-- missing", filename)
                continue
            x_paste = (x - x_start) * tile_size
            y_paste = h - (y_stop - y) * tile_size
            try:
                i = Image.open(filename)
            except Exception as e:
                print("-- %s, removing %s" % (e, filename))
                # trash_dst = os.path.expanduser("~/.Trash/%s" % filename)
                # os.rename(filename, trash_dst)
                os.remove(filename)
                continue
            result.paste(i, (x_paste, y_paste))
            del i
    output_filename = "map_%s_%s_%d.%s" % (key, TYPE, zoom, EXT)
    result.save(output_filename)
    return output_filename


def main():
    from sources import searchSource

    found_sources = searchSource("sources.json", search={"type": "sat"})
    key = list(found_sources.keys())[0]
    source = {key: found_sources[key]}
    zoom = 10
    lat_start, lon_start = 36.99, -114.03
    lat_stop, lon_stop = 35.64, -111.60
    method = "zxy_query"
    mergeTiles(source, zoom, (lat_start, lat_stop, lon_start, lon_stop), method)


if __name__ == "__main__":
    main()
