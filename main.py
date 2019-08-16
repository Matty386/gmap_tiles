from sources        import *
from download_tiles import *
from merge_tiles    import *
import webbrowser #just for opening the results of this test

def main():
    print('Loading Region Information')
    zoom = 10
    lat_start, lon_start = 36.99, -114.03  #Grand Canyon USA (top left corner)
    lat_stop, lon_stop   = 35.64, -111.60  #(bottom right corner)
    coord = (lat_start, lat_stop, lon_start, lon_stop) #Will error if wrong corners specified
    fname         = 'sources.json'
    source_type   = {'type':'sat'}
    found_sources = searchSource(fname, source_type)
    ppjson(found_sources)
    key           = list(found_sources.keys())[0] #Just try first
    source        = {key: found_sources[key]}
    ext           = source[key]
    print('Downloading Tiles')
    downloadTiles(source, zoom, coord, max_threads=1)
    print('Merging Tiles')
    img_name = mergeTiles(source, zoom, coord)
    print('Done')
    webbrowser.open(img_name)

if __name__ == '__main__':
    main()
