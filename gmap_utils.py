import math
EARTH_RADIUS_KM  = 6371.03                     #approximate km
TILE_SIZE        = 256                         #square side in pixels
MIN_LAT, MAX_LAT = (-math.pi/2.0, math.pi/2.0) #radians
MIN_LON, MAX_LON = (-math.pi, math.pi)         #radians
"""
Test case values, len() == number of tests
"""
TESTS = { #Chicago IL
    "COORDS": [(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999),(41.85,-87.649999)],
    "ABS_PX": [(65,95),(131,190),(262,380),(525,761),(1050,1522),(2101,3045),(4202,6091),(8405,12182),(16811,24364),(33623,48729),(67247,97459),(134494,194918) ],
    "TILE":   [(0,0),(0,0),(1,1),(2,2),(4,5),(8,11),(16,23),(32,47),(65,95),(131,190),(262,380),(525,761) ],
    "ZOOM":   [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]
}

def deg2rad(val):
    return (val * math.pi) / 180.0

def rad2deg(val):
    return (val * 180.0) / math.pi

def abspx2latlon(zoom,x,y):
    """
    Converts zoom + absolute pixels (x,y) to lat,lon
        Reference:
        https://groups.google.com/forum/#!topic/Google-Maps-API/NICY9wcl_JY
    """
    x_val = x
    y_val = y
    while x_val < 0: x_val += TILE_SIZE * 2**(zoom) #globe-wrap protection
    while y_val < 0: y_val += TILE_SIZE * 2**(zoom)
    #if (x_val != x)or(y_val != y): print 'MSG -- Globe-wrapped (new, old) ', (x_val,y_val), (x,y)
    lon = ((x_val*360.0) / (TILE_SIZE * (2**zoom))) - 180.0
    while (lon >  180.0): lon -= 360.0
    while (lon < -180.0): lon += 360.0
    
    expo = ( (y_val-(TILE_SIZE*(2**(zoom-1)))) / float((-TILE_SIZE*(2**zoom))/(2.0*math.pi)) )
    lat  = ( ((2.0*math.atan(math.exp(expo)))-(math.pi/2.0)) /float(math.pi/180.0) )
    if (lat < -90.0): lat = -90.0
    if (lat >  90.0): lat =  90.0
    return (lat,lon)

def xy2latlon(zoom,x,y):
    """
    Converts zoom + tile (x,y) to lat,lon
        Reference:
        https://groups.google.com/forum/#!topic/Google-Maps-API/NICY9wcl_JY
    """
    return abspx2latlon(zoom,x*TILE_SIZE,y*TILE_SIZE)

def abspx2latlonErrMargin(zoom,x,y,px_off=1):
    """
    Returns positive maximum lat-lon variance within a pixel difference.
    Ignores errors created by poles, and a 360/180/90 delta may sliently be returned as 0.
    Assumes input, and input+1 pixels are valid.
    Assumes input+1 is max difference on an approximate sphere shape.
    """
    val     = abspx2latlon(zoom,x,y)
    val_x   = abspx2latlon(zoom,x+px_off,y)
    val_y   = abspx2latlon(zoom,x,y+px_off)
    lat = max(abs(val[0]-val_x[0]),abs(val[0]-val_y[0]))
    lon = max(abs(val[1]-val_x[1]),abs(val[1]-val_y[1]))
    return (lat,lon)

def xy2latlonErrMargin(zoom,x,y):
    """
    Returns positive maximum lat-lon variance within a tile difference.
    Ignores errors created by poles, and a 360/180/90 delta may sliently be returned as 0.
    Assumes input, and input+1 pixels are valid.
    Assumes input+1 is max difference on an approximate sphere shape.
    """
    return abspx2latlonErrMargin(zoom,x*TILE_SIZE,y*TILE_SIZE,px_off=TILE_SIZE)


def latlon2abspx(z,lat,lon):
    """
    Converts zoom,latitude,longitude to absolute pixels (x,y).
        References:
        https://github.com/nst/gmap_tiles
        https://groups.google.com/forum/#!topic/Google-Maps-API/NICY9wcl_JY
    Note: Assumes properly formatted lat-long inputs.
    """
    x = TILE_SIZE*(2**z)*(lon+180.0)/360.0
    y = -(.5*math.log((1+math.sin(math.radians(lat)))/(1-math.sin(math.radians(lat))))/math.pi-1)*TILE_SIZE*2**(z-1)
    max_px = TILE_SIZE * 2**z
    assert(x>=0) #the math should not allow these
    assert(y>=0)
    assert(x<max_px)
    assert(y<max_px)
    return int(x),int(y)

def latlon2xy(z,lat,lon):
    """
    Converts zoom, latitude, longitude to tile indexes (x,y).
        References:
        https://github.com/nst/gmap_tiles
        https://groups.google.com/forum/#!topic/Google-Maps-API/NICY9wcl_JY
    """
    x,y = latlon2abspx(z,lat,lon)
    return (int(x/TILE_SIZE), int(y/TILE_SIZE))

def latlon2xyz(xxx_todo_changeme):
    """
    Approximate spherical to cartesian conversion
    """
    (lat,lon) = xxx_todo_changeme
    rad_lat, rad_lon = (deg2rad(lat),deg2rad(lon))
    x = math.cos(rad_lat) * math.cos(rad_lon)
    y = math.cos(rad_lat) * math.sin(rad_lon)
    z = math.sin(rad_lat)
    return (x,y,z)

def xyz2latlon(x,y,z):
    """
    Approximate cartesian to spherical conversion
    """
    rad_lon = math.atan2(y,x)
    hyp     = math.sqrt(x*x + y*y)
    rad_lat = math.atan2(z,hyp)
    lat,lon = rad2deg(rad_lat), rad2deg(rad_lon)
    return (lat,lon)

def latlonCenter(latlon_points):
    """
    Based on averaging points on a sphere.
    Reference: http://stackoverflow.com/questions/6671183/calculate-the-center-point-of-multiple-latitude-longitude-coordinate-pairs
    """
    avg = [0,0,0] #x,y,z
    for coord in latlon_points:
        avg[0],avg[1],avg[2] = latlon2xyz( coord )
    for i in range(len( avg )):
        avg[i] = float(avg[i]) / float(len(latlon_points))
    return xyz2latlon( avg[0],avg[1],avg[2] )

def latlonRadius(center_coord, points, sphere_radius):
    """
    Given a known center of a list of points, brute force the radius.
    """
    dist = 0
    for i in range(len( points )):
        val = distanceTo( center_coord, points[i], sphere_radius )
        if val > dist:
            dist = val
    return dist

def distanceTo(xxx_todo_changeme1, xxx_todo_changeme2,sphere_radius):
    """
    Source: http://janmatuschek.de/LatitudeLongitudeBoundingCoordinates
    """
    (lat0,lon0) = xxx_todo_changeme1
    (lat1,lon1) = xxx_todo_changeme2
    rad_lat0, rad_lon0 = deg2rad(lat0), deg2rad(lon0)
    rad_lat1, rad_lon1 = deg2rad(lat1), deg2rad(lon1)
    val  = math.sin(rad_lat0) * math.sin(rad_lat1)
    val += math.cos(rad_lat0) * math.cos(rad_lat1) * math.cos(rad_lon0 - rad_lon1)
    return math.acos( val ) * sphere_radius

def boundingCoordinates(xxx_todo_changeme3,dist,sphere_radius):
    """
    Source: http://janmatuschek.de/LatitudeLongitudeBoundingCoordinates
    """
    (lat,lon) = xxx_todo_changeme3
    assert(dist >=0)
    assert(sphere_radius >=0)
    rad_lat, rad_lon = deg2rad(lat), deg2rad(lon)
    rad_dist         = float(dist) / float(sphere_radius)
    a_lat            = rad_lat - rad_dist
    b_lat            = rad_lat + rad_dist
    if (a_lat > MIN_LAT) and (b_lat < MAX_LAT):
        delta_lon = math.asin( math.sin(rad_dist) / math.cos(rad_lat) )
        a_lon     = rad_lon - delta_lon
        if (a_lon < MIN_LON):
            a_lon += 2.0 * math.pi
        b_lon = rad_lon + delta_lon
        if (b_lon > MAX_LON):
            b_lon -= 2.0 * math.pi
    else:
        #pole within distance
        a_lat = max(a_lat, MIN_LAT)
        b_lat = min(b_lat, MAX_LAT)
        a_lon = MIN_LON
        b_lon = MAX_LON
    a_deg = (rad2deg(a_lat),  rad2deg(a_lon))
    b_deg = (rad2deg(b_lat),  rad2deg(b_lon))
    return (a_deg, b_deg)

def tileBounds(zoom,coord0,coord1):
    """
    Returns (tile_start=(x,y), tile_stop=(x,y), tile_count=(wide,high))
    Where start/stop are absolute units, and count is the (coord0,coord1) bound size.
    """
    tile_a     = latlon2xy(zoom,coord0[0], coord0[1])
    tile_b     = latlon2xy(zoom,coord1[0], coord1[1])
    tile_start = (min(tile_a[0],tile_b[0]), min(tile_a[1],tile_b[1]))
    tile_stop  = (max(tile_a[0],tile_b[0]), max(tile_a[1],tile_b[1]))
    tile_count = (abs(tile_stop[0]-tile_start[0])+1, abs(tile_stop[1]-tile_start[1])+1) #inclusive difference range
    #print (tile_start,tile_stop,tile_count)
    return (tile_start,tile_stop,tile_count)

def resBounds(zoom,coord0,coord1):
    """
    Returns (res_start=(x,y), res_stop=(x,y), res_count=(wide,high))
    Where start/stop are absolute units, and count is the (coord0,coord1) bound size.
    """
    res_start = latlon2abspx(zoom,coord0[0], coord0[1])
    res_stop  = latlon2abspx(zoom,coord1[0], coord1[1])
    res_start = (min(res_start[0],res_stop[0]), min(res_start[1],res_stop[1]))
    res_stop  = (max(res_start[0],res_stop[0]), max(res_start[1],res_stop[1]))
    res_count = (abs(res_stop[0]-res_start[0]), abs(res_stop[1]-res_start[1]))
    return (res_start,res_stop,res_count)

def zoomFromCoords(res_box, coord0, coord1, coord_center, max_zoom=20):
    """
    Find a zoom level for a: res_box=(px_wid,px_hei)
    with res_box centered at: coord_center=(lat,long)
    and image tiles spanning: coord0,coord1 = (lat0,lon0),(lat1,lon1)
    Returns (zoom,res_center)
    Note: This does not account for allowing rotation, increase res_box size larger if required.
    """
    assert(res_box[0]>0)
    assert(res_box[1]>0)
    zoom       = 0
    size_px    = (0,0)
    fits       = False
    while (size_px[0]<res_box[0]) or (size_px[1]<res_box[1]) or (fits != True): #while output size not big enough, and not fit
        tile_min,tile_max,tiles  = tileBounds(zoom,coord0,coord1)               #size in tiles
        res_min,res_max,res_size = resBounds(zoom,coord0,coord1)                #size in px
        size_px                  = (tiles[0]*TILE_SIZE, tiles[1]*TILE_SIZE)     #size in px
        center_px = latlon2abspx(zoom, coord_center[0], coord_center[1])           #absolute px coordinates
        center_px = (center_px[0]-res_min[0], center_px[1]-res_min[1])          #offset into self._image_temp px coordinates
        offset_px = (center_px[0]-(res_box[0]/2),center_px[1]-(res_box[1]/2))   #differences between self._image_temp and res_box (0,0)
        max_px    = (center_px[0]+offset_px[0], center_px[1]+offset_px[1])      #max needed pixel to test vs size_px
        #print 'MSG -- (fits, zoom, tiles, size_px, res_box, max_px) -- ', (fits, zoom,tiles,size_px, res_box,max_px)
        if (size_px[0]>max_px[0]) and (size_px[1]>max_px[1]):
            fits = True                                                         #res_box fits inside tiles px size
        if zoom >= 20:
            break
        zoom += 1
    return zoom -1

def main():
    """
    Run math tests on:
    TESTS = {
        "COORDS": [(lat,lon), ... ],
        "ABS_PX": [(x,y), ...],
        "TILE":   [(x,y), ...],
        "ZOOM":   [0, ...]
    }
    """
    tests_len = 0
    for k in list(TESTS.keys()):
        v = len(TESTS[k])
        if tests_len <=0:
            tests_len = v
        else:
            tests_len = min(tests_len,v)
    
    for i in range(tests_len):
        coord    = TESTS["COORDS"][i]
        px       = TESTS["ABS_PX"][i]
        tile     = TESTS["TILE"][i]
        zoom     = TESTS["ZOOM"][i]
        px_err   = abspx2latlonErrMargin(zoom,px[0],px[1])
        tile_err = xy2latlonErrMargin(zoom,tile[0],tile[1])
        print('MSG -- ', i)
        print('MSG -- Testing Inputs: (zoom, coord, px, tile)', (zoom, coord, px, tile))
        print('MSG -- Max Error of (px, tile) in lat-lon', (px_err, tile_err))
        val = latlon2abspx(zoom,coord[0],coord[1]); print('MSG -- Lat-lon to pixel: val, expected ',val,px)
        assert( val   == px   )
        val = latlon2xy(zoom,coord[0],coord[1]); print('MSG -- Lat-lon to tile: val, expected ',val,tile)
        assert( val   == tile )
        val = abspx2latlon(zoom,px[0],px[1]); delta=((val[0]-coord[0]),(val[1]-coord[1])); print('MSG -- Pixel to lat-lon: val, expected ', val, coord)
        assert( (delta[0]<px_err[0])and(delta[1]<px_err[1]) )
        val = xy2latlon(zoom,tile[0],tile[1]); delta=((val[0]-coord[0]),(val[1]-coord[1])); print('MSG -- Tile to lat-lon: val, expected ', val, coord)
        assert( (delta[0]<tile_err[0])and(delta[1]<tile_err[1]) )
        val = (px[0]/TILE_SIZE,px[1]/TILE_SIZE); print('MSG -- Absolute pixels to tile index: val, expected',val,tile)
        assert( val   == tile )
    print('')
    print('MSG -- Tests Completed Successfully')

if __name__ == '__main__':
    main()
