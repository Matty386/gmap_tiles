# Usage

Edit `main.py` to specify the area and the zoom level you want.

    zoom = 10
    ...
    lat_start, lon_start = 36.99, -114.03  #Grand Canyon USA (top left corner)
    lat_stop, lon_stop   = 35.64, -111.60  #(bottom right corner)
    ...
    source_type = {'type':'sat'} # Search for a satellite image source in sources.json

You can easily find coordinates with [http://itouchmap.com/latlong.html](http://itouchmap.com/latlong.html).

Then, run `$ python main.py` to fetch, merge and display tiles:

    Loading Region Information
    {
        "5271016846446686592": {
            "ext": "jpg", 
            "name": "Google Satellite", 
            "notes": "Google will blacklist overuse for 24H, v=708 is the API version number which will sometimes be updated and must be correct, and normally discourages direct access like this. The http or https links work equally.", 
            "postfix": "", 
            "prefix": "https://khm2.google.com/kh/v=708&s=Gal", 
            "type": "satellite", 
            "x": "&x=", 
            "y": "&y=", 
            "zoom": "&z="
        }
    }
    Downloading Tiles
    x range 187 194
    y range 398 403
    Total Tiles:  35
    ...................................
    Merging Tiles
    x range 187 194
    y range 398 403
    width: 1792
    height: 1280
    Don


## Select Tile Source

Methods from `sources.py` select, add, or remove information from `sources.json`.
Example usage/tests can be run by `$ python sources.py`.
Note: A source 'uid' is the hash of the source fields, so updating a source may cause methods to ignore already fetched tiles.


## Download Map Tiles

Methods from `download_tiles.py` convert zoom and cordinates via `gmap_utils.py` into urls to download into the current directory.
Example usage/tests can be run by `$ python download_tiles.py`.


## Merge Map Tiles
Methods from `merge_tiles.py` use a known image source and coordinate bounds to generate a single stitched image.
Example usage/tests can be run by `$ python merge_tiles.py` after the tiles have been downloaded.


### References

Packages used:
    PIL - For merging images (`merge_tiles.py`)
    json - For loading tile sources (`sources.py`)
    urllib2 - For downloading http(s) data (`download_tiles.py`)
    threading - For multiple http(s) workers
    fake_useragent - For generating useragent strings

Original repository:
    ![Google Maps Tiles](https://raw.github.com/nst/gmap_tiles/master/gmap.png)
