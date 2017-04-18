import os
import urllib2
from math       import sqrt
from time       import time, sleep
from gmap_utils import *
from PIL        import Image
from threading  import Thread
try:
    from fake_useragent import UserAgent
except:
    pass

class GmapRender:
    def __init__(self):
        self._download_queue       = {} #{ (url,filename):status, ... } #status = 0, or timestamp when failed
        self._download_threads     = [] #[Thread(), ...]
        self._download_threads_out = [] #[None, (stamp,(url,filename),msg), ...]
        self._download_threads_max = 1
        self._download_retry_after = 900 #seconds
        try:    self._download_ua  = UserAgent()
        except: self._download_ua  = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_9; us-at) AppleWebKit/533.23.1 (KHTML, like Gecko) Version/5.0.5 Safari/533.21.3'
        
        self._image_temp        = None
        self._image_temp_center = (0,0) #circumcribed circle of lat-lon center as px
        self._image_out         = None
        self._image_dir         = '.'
        self._image_count       = 0
        self._image_filter      = Image.BICUBIC #for image rotates and compass resize
        self._box_temp          = (0,0,0,0) #bounding crop box
        self._box_out           = (0,0,0,0)
        self._new_setting       = True
        
        self._res           = (800,600)
        self._sphere_radius = EARTH_RADIUS_KM
        self._coords_geo    = []
        self._coords_bound  = [(0,0),(0,0)] #bounding lat-long pair which specifies downloading range
        self._zoom          = 0
                                   #orient image top to this angle in [0,360) degrees
        self._heading_overlay = {} #{'deg':0, 'position_px':(x,y), 'size':(wid,hei)} #top-left-ref
        self._image_overlays  = {}
        self._compass_file    = './compass.png'
    
    def setVals(self,res=None,coords=None,zoom=None,heading_overlay=None,image_overlays=None, image_dir=None, threads_max=None, retry=None, compass_filename=None):
        """
        setVals(res=(1024,768) ,
                coords=[(lat0,lon0), (lat1,lon1)] ,
                zoom=12
                heading_overlay={'deg':0, 'position_px':[50,50], 'size':[50,50]} ,
                image_overlays={ sources:{ '0': {...} }, 'order':['0'] } ,
                image_dir='./images' ,
                threads_max=1 ,
                retry = 900
               )
        setVals(res=(1280,1024)) #specify just what needs to be changed
        """
        if res != None:
            self._res = (int(res[0]),int(res[1]))
            self._new_setting = True
        if (coords != None) and (len(coords) > 0):
            self._coords_geo = coords
            self._new_setting = True
        if (zoom != None):
            self._zoom = int(zoom)
            self._new_setting = True
        if (heading_overlay != None) and (len(heading_overlay) > 0):
            self._heading_overlay = heading_overlay
            self._new_setting = True
        if (image_overlays != None) and (len(image_overlays) > 0):
            self._image_overlays = image_overlays
            self._new_setting = True
        if (image_dir != None):
            self._image_dir = image_dir #images are not auto-moved
        if (threads_max != None):
           self._download_threads_max = int(threads_max)
        if (retry != None):
           self._download_retry_after = int(retry)
        if (compass_filename != None):
           self._compass_file = str(compass_filename)
           try:
               del self._compass_image
           except:
               pass
    
    def update(self):
        """
        Updates output image only if required.
        Returns output image.
        Will queue downloads, but not start them.
        """
        image_count = self._countFiles(self._image_dir)
        if image_count != self._image_count:
            self._image_count      = image_count
            self._new_setting      = True
        if self._new_setting == True:                                      #need to update?
            self._new_setting      = False
            tiles                  = self._findTiles()                     #discover tiles range
            self._zoom  = tiles[2]
            try:
                self._image_overlays['order']
            except:
                self._image_overlays['order'] = list(self._image_overlays['sources'].keys())
            for uid in self._image_overlays['order']: #queue up list of tiles
                #print 'MSG -- Update %s -- %s' % (uid,tiles)
                self._queueTiles(uid, tiles)
            overlays = []
            for uid in self._image_overlays['order']:                                        #merge tiles and layers
                overlays.append( self._mergeTiles( uid, tiles) )
            self._image_temp = self._mergeLayers(  overlays )                                #px size: TILE_SIZE * (tiles_wid,tiles_hei)
            self._image_temp = self._orientTemp(   self._zoom,      self._image_temp      )  #px size: (diameter, diameter)
            self._image_out  = self._orientOutput( self._image_temp                       )  #px size: self._res
            self._image_out  = self._mergeLayers([ self._image_out, self._compassGen()   ])
        return self._image_out
    
    def checkWorkers(self):
        """
        Check workers progress, join/fork if able.
        Returns total number of jobs in progress.
        Spawns up to threads_max, and only retries jobs after timeout.
        Moves failed jobs back into queue for retries later.
        """
        #join workers, pop from threads, if failed push to queue
        for ind in reversed(xrange(len( self._download_threads ))):
            if not( self._download_threads[ind].isAlive() ): #assert job is completed
                self._download_threads[ind].join()           #should not block, because job is complete
                del self._download_threads[ind]              #rm job handle
                if self._download_threads_out[ind] != None:
                    stamp, key, msg = self._download_threads_out[ind]
                    #print 'MSG -- Joining Thread %s' % (str((stamp,key,msg)) )
                    #print msg
                    if stamp > 0:                            #failed, returning job to queue
                        self._download_queue[key] = stamp
                del self._download_threads_out[ind]          #rm job return value
        #spawn workers, pop from queue, push to threads
        ind = len(self._download_queue)-1
        #print 'MSG -- checkWorkers() len() %s' % (str(ind))
        while (len(self._download_threads)<self._download_threads_max) and (ind>=0):
            key = self._download_queue.keys()[ind]
            val = self._download_queue[key]
            #print 'MSG -- checkWorkers() %s' % (str((key,val)) )
            if (time() - val > self._download_retry_after):   #only retry after timeout
                try:    ua_str = self._download_ua.random
                except: ua_str = self._download_ua
                url, filename  = key
                id             = len( self._download_threads )
                self._download_threads_out.append( None )
                t = Thread(target=self._worker, args=(url,ua_str,filename,id,self._download_threads_out) )
                t.start()
                #print 'MSG -- Starting Thread %s' % (str((url,filename)) )
                self._download_threads.append( t )
                del self._download_queue[key]
            ind -= 1
        #print 'MSG -- in(Thread,Queue) %s' % (str((self.inThreads(),self.inQueue())) )
        return self.inThreads()
    
    def inQueue(self):
        """
        Returns number of jobs in queue.
        Not guaranteed to ever be zero after the queue has been populated.
        """
        return len(self._download_queue)
    
    def inThreads(self):
        """
        Returns number of thread handles.
        Actually running threads may be less, but can not exceed threads_max.
        If number of actually running threads is wanted, used threading.enumerate().
        Only guaranteed to be zero after population if retry timeout>thresh.
        (thresh>=0 seconds maybe system dependant)
        """
        return len(self._download_threads)
    
    def px2latlon(self, (x,y)):
        """
        On self._image_out of size: self._res=(width,height)
        Given input (x,y) return (lat,lon) or None on invalid pixel input.
        Valid pixels: int(), [0,size[dim]), dim=[0,1]
          References:
          https://github.com/nst/gmap_tiles
          https://groups.google.com/forum/#!topic/Google-Maps-API/NICY9wcl_JY
        """
        if type(x) != type(int(0)):    return None
        if type(y) != type(int(0)):    return None
        if (x<0) or (x>=self._res[0]): return None
        if (y<0) or (x>=self._res[1]): return None
        c_px     = (self._res[0]/2,self._res[1]/2)
        c_latlon = latlonCenter(self._coords_bound)
        c_abspx  = latlon2abspx(self._zoom, c_latlon[0], c_latlon[1])
        d_abspx  = (c_abspx[0]-c_px[0], c_abspx[1]-c_px[1])
        t_abspx  = (d_abspx[0]+x, d_abspx[1]+y)
        print 'MSG -- Offset delta (x_off,y_off)', (d_abspx)
        print 'MSG -- Center (zoom) (lat,lon) (x,y) (x_abs,y_abs)', (self._zoom),(c_latlon),(c_px),(c_abspx)
        t_latlon = abspx2latlon(self._zoom, t_abspx[0], t_abspx[1])
        print 'MSG -- Target (zoom) (lat,lon) (x,y) (x_abs,y_abs)', (self._zoom),(t_latlon),(x,y),(t_abspx)
        return t_latlon
        
        center_norm_px = (self._res[0]/2,self._res[1]/2)
        center_latlon  = latlonCenter( self._coords_bound )
        center_abs_px  = latlon2abspx(    self._zoom, center_latlon[0], center_latlon[1] )
        #print 'MSG -- pixels (abs, image)', (center_abs_px, center_norm_px)
        abs_px_offset  = (center_abs_px[0]-center_norm_px[0], center_abs_px[1]-center_norm_px[1])
        target_abs_px  = (x+abs_px_offset[0], y+abs_px_offset[1])
        #print 'MSG -- ABS to image pixel offset ', abs_px_offset
        return abspx2latlon(self._zoom, target_abs_px[0], target_abs_px[1])

    def latlon2px(self, (lat,lon)):
        """
        Given (lat,lon) coordinates as type float()
        Return (x,y) if coord is on the image, else Return None
          References:
          https://github.com/nst/gmap_tiles
          https://groups.google.com/forum/#!topic/Google-Maps-API/NICY9wcl_JY
        """
        if type(lat) != type(float(0)): return None
        if type(lat) != type(float(0)): return None
        center_norm_px = (self._res[0]/2,self._res[1]/2)
        center_latlon  = latlonCenter( self._coords_bound )
        center_abs_px  = latlon2abspx(    self._zoom, center_latlon[0], center_latlon[1] )
        target_abs_px  = latlon2abspx(    self._zoom, lat, lon )
        abs_px_offset  = (center_abs_px[0] - center_norm_px[0], center_abs_px[1] - center_norm_px[1])
        target_norm_px = (target_abs_px[0] - abs_px_offset[0], target_abs_px[1] - abs_px_offset[1])
        if (target_norm_px[0]<0) or (target_norm_px[0]>=self._res[0]): return None
        if (target_norm_px[1]<0) or (target_norm_px[1]>=self._res[1]): return None
        return target_norm_px
    
    @staticmethod
    def _countFiles(directory):
        found = os.listdir(directory)
        count = 0
        for name in found:
            if os.path.isfile(os.path.join(directory, name)):
                count += 1
        return count
    
    def _findTiles(self, default_radius=1.0):
        """
        Create bounding box around coords or single coord at radius.
        Maintain excess size for rotation, and format outputs for downloader use.
        Radius is approximate surface km around points center.
        """
        coord_center       = latlonCenter(self._coords_geo)
        self._coord_center = coord_center
        if len(self._coords_geo)>1:
            radius_km      = latlonRadius(coord_center, self._coords_geo, self._sphere_radius)
        else:
            radius_km      = float(default_radius)
        #print 'MSG -- _findtiles() radius_km %s' % (radius_km)
        coord_a, coord_b   = boundingCoordinates(coord_center, radius_km, self._sphere_radius)
        self._coords_bound = [coord_a,coord_b]
        radius_px          = int(math.ceil(math.sqrt( self._res[0]*self._res[0] + self._res[1]*self._res[1] )/2.0))
        #print 'MSG -- _findTiles radius_px ', radius_px
        bound_size         = (int(math.ceil(math.sqrt(8)*radius_px)),int(math.ceil(math.sqrt(8)*radius_px))) #find a square to bound a circle about the required radius_px box (to allow for image rotation)
        #print 'MSG -- _findtiles() bound_size ', bound_size
        self._zoom         = zoomFromCoords(bound_size, coord_a, coord_b, coord_center)
        t_min,t_max,t_all  = tileBounds(self._zoom,coord_a,coord_b)
        x_range            = (t_min[0],t_max[0])
        y_range            = (t_min[1],t_max[1])
        return (x_range,y_range,self._zoom)
    
    @staticmethod
    def _mergeLayers(img_list):
        """
        Assuming image_list containing all the same sizes, merges layers in order.
        """
        if len(img_list) > 0:
            SIZE = img_list[0].size
            SIZE = (int(SIZE[0]),int(SIZE[1]))
            result = Image.new('RGBA',SIZE)
            for i in img_list:
                result = Image.alpha_composite( result, i )
            return result
        return None
    
    @staticmethod
    def _worker(url,useragent,filename,id,out_list):
        """
        Download worker usage:
        (time(),(url,filename), 'ERR -- 404') = _downloadWorker('www.g.g','./g.png')
        (0,(url,filename),'')                 = _downloadWorker('www.google.com/logo.png','./g.png')
        """
        dat  = None
        head = {'User-Agent': useragent}
        stamp,key,msg = (0,(url,filename),'')
        try:
            req = urllib2.Request(url, data=None,headers=head)
            rsp = urllib2.urlopen(req)
            dat = rsp.read()
        except Exception, e:
            stamp = time()
            msg   = 'ERR -- ' + str(e) + ' ' + str(url) + ' -> ' + str(filename)
            out_list[id] = (stamp,key,msg)
            return
        if dat.startswith("<html>"):
            stamp = time()
            msg   = 'ERR -- 403 Forbidden ' + str(url) + ' -> ' + str(filename)
            out_list[id] = (stamp, key,msg)
            return
        with open(filename, 'wb') as f:
            f.write(dat)
        msg = 'MSG -- ' + '200 Completed ' + str(url) + ' -> ' + str(filename)
        out_list[id] = (stamp,key,msg)
        return
    
    def _genUrl(self, layer_uid, (x,y,zoom)):
        source = self._image_overlays['sources'][layer_uid]
        url = ''
        url += source['prefix']
        url += source['x'] + str(x)
        url += source['y'] + str(y)
        url += source['zoom'] + str(zoom)
        url += source['postfix']
        return url
    
    def _genFilename(self, layer_uid, (x,y,zoom)):
        ext = self._image_overlays['sources'][layer_uid]['ext']
        d = self._image_dir
        if len(d)>0:
            if d[len(d)-1] != os.sep:
                d += os.sep
        return d + '_'.join( [str(layer_uid),str(zoom),str(x),str(y)] ) + '.' + str(ext)
    
    def _queueTiles(self, layer_uid, (x_range,y_range,zoom)):
        """
        Add files to work queue.
        Arbitrary ordering.
        """
        for x in xrange(min(x_range),max(x_range)):
            for y in xrange(min(y_range),max(y_range)):
                url      = self._genUrl(     layer_uid, (x,y,zoom))
                filename = self._genFilename(layer_uid, (x,y,zoom))
                try:
                    open(filename,'r').close()
                    #print 'MSG -- Found %s' % (filename)
                except:
                    #print 'MSG -- Queuing %s' % (filename)
                    try:    self._download_queue[ (url,filename) ]
                    except: self._download_queue[ (url,filename) ] = 0
        pass #add files to queue
    
    def _mergeTiles(self, layer, (x_range, y_range, zoom)):
        """
        Attempts to load image files from disk, and returns stitched image.
        """
        x_start, x_stop = min(x_range), max(x_range)
        y_start, y_stop = min(y_range), max(y_range)
        TILE_SIZE = (256,256)
        wid, hei = (x_stop - x_start) * TILE_SIZE[0], (y_stop - y_start) * TILE_SIZE[1]
        result = Image.new('RGBA', (wid, hei))
        for x in xrange(x_start, x_stop):
            for y in xrange(y_start, y_stop):
                filename = self._genFilename(layer, (x,y,zoom))
                if not os.path.exists(filename):
                    #print "ERROR -- Missing ", filename
                    continue
                x_paste = (x - x_start) * TILE_SIZE[0]
                y_paste = hei - (y_stop - y) * TILE_SIZE[1]
                try:
                    img = Image.open(filename)
                except Exception, e:
                    print 'ERROR -- %s, Removing %s' % (e, filename)
                    os.remove(filename)
                result.paste(img, (x_paste, y_paste))
                del img
        return result #result.save('merged_image.png')
    
    def _orientTemp(self, zoom, in_image):
        """
        Given in_image as merged-tiles.
        Return cropped image.size == (diameter,diameter)
        Centers crop around center_coord.
        """
        center_coord     = latlonCenter(self._coords_bound)
        #print 'MSG -- center_coord %s' % (str( center_coord ))
        radius_px        = int(math.ceil(math.sqrt( self._res[0]*self._res[0] + self._res[1]*self._res[1] )/2.0))
        #print 'MSG -- radius_px', radius_px
        center_abspx     = latlon2abspx(zoom, center_coord[0],       center_coord[1]            )
        #print 'MSG -- center_abspx', center_abspx
        min_abspx        = latlon2abspx(zoom, self._coords_bound[0][0], self._coords_bound[0][1])
        #print 'MSG -- min_abspx', min_abspx
        min_off_abspx    = (min_abspx[0] % TILE_SIZE, min_abspx[1] % TILE_SIZE)
        #print 'MSG -- min_off_abspx', min_off_abspx
        #zero_abspx       = (min_abspx[0]-min_off_abspx[0], min_abspx[1]-min_off_abspx[1])
        self._box_temp   = (min_off_abspx[0],
                            min_off_abspx[1],
                            min_off_abspx[0]+2*radius_px,
                            min_off_abspx[1]+2*radius_px )
        #print 'MSG -- self._box_temp', self._box_temp
        return in_image.crop( self._box_temp )
    
    def _orientOutput(self, in_image):
        """
        Given in_image.size == (diameter,diameter)
        Return rotated/cropped image.size == self._res
        """
        try:    angle    = self._heading_overlay['deg']
        except: angle    = 0
        center_coord     = latlonCenter(self._coords_bound)
        radius_px        = int(math.ceil(math.sqrt( self._res[0]*self._res[0] + self._res[1]*self._res[1] )/2.0))
        self._box_out    = (radius_px-(self._res[0]/2),
                            radius_px-(self._res[1]/2),
                            radius_px+(self._res[0]/2),
                            radius_px+(self._res[1]/2) )
        ret = in_image.rotate( angle )
        ret = ret.crop( self._box_out )
        assert( type(ret.size[0]) == type(int(0)) )
        return ret



        try:    angle  = self._heading_overlay['deg']
        except: angle  = 0
        w,h     = self._image_temp_center #circle of points center, not necessarily image center
        wid,hei = self._res               #output image size
        #print 'MSG -- (wid,hei) %s' % (str(self._res))
        box     = ( int(w-(wid/2)),int(h-(hei/2)),int(w+(wid/2)),int(h+(hei/2)) ) #left,upper,right,lower
        #print 'MSG -- box delta %s' %(str((box[2]-box[0],box[3]-box[1])))
        #print 'MSG -- orient box %s  source temp %s' % (str(box),str(self._image_temp.size))
        ret = self._image_temp.rotate( angle, self._image_filter )
        #print 'MSG -- temp.rotate.size %s' % (str(ret.size))
        ret = ret.crop( box )
        #print 'MSG -- temp.rotate.crop.size %s' % (str(ret.size))
        return ret
    
    def _compassGen(self):
        """
        Return a compass overlay, resized and placed on a self._res overlay.
        """
        if len(self._heading_overlay)!=3:
            return Image.new('RGBA',self._res)
        try:    angle = self._heading_overlay['deg']
        except: angle = 0
        try:
            self._compass_image.size
        except:
            self._compass_image = Image.open(self._compass_file)
        assert( type(self._heading_overlay['deg']) == type(0)          )
        assert( type(self._heading_overlay['position_xy']) == type(()) )
        assert( type(self._heading_overlay['size']) == type(())        )
        compass = self._compass_image.copy()
        compass = compass.rotate( angle, self._image_filter )
        compass = compass.resize( self._heading_overlay['size'], self._image_filter )
        result  = Image.new('RGBA', self._res, color=(0,0,0,0))
        result.paste( compass, self._heading_overlay['position_xy'] )
        del compass
        return result

def main():
    """
    Steps:
    * From sources.json, load external sources information.
    * Specify which sources to use.
    * Specify which region to download.
    * Specify the output resolution.
    * Wait for downloads to complete.
    * Merge tiles, overlays, rotate and crop.
    * View output.
    
    Features:
    * Auto-fits lat-lon points to res.
    * Auto-finds zoom-level if points>1.
    * GUI friendly downloader management and status notification.
    * (opt) Compass overlay from image.
    * (opt) Multiple sources as overlays, order may be specified.
    """
    from sources import searchSource, ppjson
    import random
    
    sources      = searchSource('sources.json', search={'type':'sat'})
    sources      = {'sources': sources}
    ppjson(sources)
    coord_list   = [ (36.99,-114.03), (35.64,-111.60) ] # len(coord_list)>=1
    resolution   = (1920,1080)
    val          = int(min(resolution)/8)
    compass      = {'deg':45, 'position_xy':(0,0), 'size':(val,val)}
    px_point     = (resolution[0]/2, resolution[1]/2) #get the location in lat-lon
    latlon_point = (35.77,-112.01)
    
    renderObj = GmapRender()
    renderObj.setVals(res=resolution, coords=coord_list, image_overlays=sources, heading_overlay=compass, compass_filename='./Compass_rose_transparent.png')
    renderObj.update()                 #Queue up download jobs.
    while renderObj.checkWorkers() >0: #Returns total remaining downloads.
        print 'MSG -- in(Thread,Queue) ', ( renderObj.inThreads(), renderObj.inQueue() ) 
        sleep(1 + random.random())     #Launches up to max_threads workers.
    img = renderObj.update()           #Composes output image.
    print 'MSG -- Output Resolution ', img.size
    print 'MSG -- Pixel',        px_point,   'is the lat-lon', renderObj.px2latlon(px_point)
    print 'MSG -- Icon lat-lon', latlon_point, 'is the pixel',   renderObj.latlon2px(latlon_point)
    img.show()

if __name__ == '__main__':
    main()
