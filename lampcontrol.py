# -*- coding: utf-8 -*-
"""
Created on Sat Sep 06 12:08:30 2014

@author: Fons
"""

import urllib2
import threading
import time
import math
import logging
import xml.etree.ElementTree as ET

class TimeClass:
    # g_time_curUT = timegm(time.strptime('2014-09-13','%Y-%m-%d'))
    # for real-time set g_time_incUT to 0
    # for simulation set g_time_incUT to > 0
    # g_time_incUT = 5*60  
    g_time_incUT = 0 
    
    @staticmethod
    def getTime():
        if (TimeClass.g_time_incUT != 0):
            # simulate
            curUT = TimeClass.g_time_curUT
            TimeClass.g_time_curUT = TimeClass.g_time_curUT + TimeClass.g_time_incUT
        else:
            # real time
            curUT = time.time()
        return time.gmtime(curUT)
        
    
def sunRiseSet(curUT,rise,tz,dst):
    # returns the time of sunrise or sunset in hours 
    # times are in UT, curUT is struct_time
    # y = year in gregorian calendar
    # m = month of year 1..12
    # d = day of month
    # lat = latitude in degrees
    # lon = longitude in degrees
    # rise = 1 for sunrise, -1 for sunset
    # tz = time zone (wrt to UT)
    # dst = daylight saving time
    # required altitude, 
    #  -18 astronomical twilight, 
    #  -12 nautical twilight,
    #   -6 civil twilight
    req_alt = 0
    #tz = 0
    #dst = 0
    lat = 51.19 
    lon = 5.71
    y = curUT.tm_year
    m = curUT.tm_mon
    d = curUT.tm_mday
    centuries = (367*y-int(7*(y+int((m+9)/12))/4)+int(275*m/9)+d-730531.5)/36525
    tmp, L = divmod(4.8949504201433+628.331969753199*centuries,6.28318530718)
    tmp, G = divmod(6.2400408+628.3019501*centuries,6.28318530718)
    ec = 0.033423*math.sin(G)+0.00034907*math.sin(2*G)
    lmbd = L + ec
    E = 0.0430398*math.sin(2*lmbd) - 0.00092502*math.sin(4*lmbd) - ec
    obl = 0.409093-0.0002269*centuries
    delta = math.asin(math.sin(lmbd)*math.sin(obl))
    GHA = 3.14159265358979 - 3.14159265358979 + E
    cosc =(math.sin(0.017453293*req_alt) - math.sin(0.017453293*lat)*math.sin(delta))/(math.cos(0.017453293*lat)*math.cos(delta))
    correction = math.acos(cosc)
    utnew = 3.14159265358979 - (GHA+0.017453293*lon + rise*correction)
    eventLT = utnew*57.29577951/15 + tz + dst
    return eventLT
    

   
def st_2_h(st):
    # hours as fractional number from a struct_time type
    return float(st.tm_hour) + float(st.tm_min)/60.0

def str_2_h(s):
    # hours as fractional number from a string "hh:mm"
    return float(s[:2])+float(s[3:])/60.0
    
def before(d_cur,h_cur,d_ref,h_ref):
    # check if current time is before reference time
    # before means: cur is on same day and h_cur < h_ref or
    # cur is day before and h_cur > h_ref
    d_cur_plus1 = (d_cur + 1) % 7    
    if (d_cur == d_ref):
        # cur is on same day
        bf = h_cur < h_ref
    else:
        if (d_cur_plus1 == d_ref):
            # cur is day before
            bf = h_cur > h_ref
        else:
            bf = False
    return bf

def past(d_cur,h_cur,d_ref,h_ref):
    # check if current time is past reference time
    # before means: cur is on same day and h_cur > h_ref or
    # cur is day after and h_cur < h_ref
    d_ref_plus1 = (d_ref + 1) % 7
    if (d_cur == d_ref):
        # cur is on same day
        bf = h_cur > h_ref
    else:
        if (d_cur == d_ref_plus1):
            # cur is day after
            bf = h_cur < h_ref
        else:
            bf = False
    return bf           
    
def time_for_action(d_cur,h_cur,d_act1,d_act2,h_act,h_act_delta):
    # check if current time is in between action time and action time
    # plus delta, action time may have day range from d_act1 to d_act2
    h_end = h_act + h_act_delta
    d_inc = 0
    if (h_end >= 24):
        h_end = h_end - 24
        d_inc = 1
    # h_end and d_inc determine action time plus delta    
    d = d_act1
    done = False
    while (not done and (d <= d_act2)):        
        done = before(d_cur,h_cur,(d + d_inc ) % 7,h_end) and \
        past(d_cur,h_cur,d,h_act)
        d = d + 1
    return done
        
def checkLamp(ticks, h_delta):
    # ticks is current time in ticks
    # h_ variables are fractional hour numbers (0.00-23.98) in local time
    # d_ variables are days of the week from 0 to 6 (0 = Monday) in local time
    tz = 1 # time zone
    # get UT
    UT = time.gmtime(ticks)
    # get LT
    LT = time.localtime(ticks)
    if (LT.tm_isdst >= 0):
        dst = LT.tm_isdst
    else:
        dst = 0   
    # from now, all goes in local time    
    h_rise = sunRiseSet(UT,1,tz,dst)
    h_set = sunRiseSet(UT,-1,tz,dst)
    h_cur = st_2_h(LT)       
    d_cur = LT.tm_wday
    for ev in events:        
        if (ev.attrib['ref'] == 'SunRise'):
            ts = ev.attrib['time']
            h_ev = str_2_h(ts[1:])
            if (ts[0] == '+'):
                h_ev = h_rise + h_ev
            else:
                h_ev = h_rise - h_ev
        if (ev.attrib['ref'] == 'SunSet'):
            ts = ev.attrib['time']
            h_ev = str_2_h(ts[1:])
            if (ts[0] == '+'):
                h_ev = h_set + h_ev
            else:
                h_ev = h_set - h_ev                
        if (ev.attrib['ref'] == 'LT'):
            ts = ev.attrib['time']
            h_ev = str_2_h(ts)
        # h_ev is the event clock time
        assert (h_ev >= 0), "Event on previous day"
        assert (h_ev < 24), "Event on next day"
        dStr = ev.attrib['day']
        d_ev_f = int(dStr[0]) # from-day
        d_ev_t = int(dStr[2]) # to-day
        # now we have: h_cur, d_cur, h_delta, h_ev, de_ev_f, d_ev_t
        if time_for_action(d_cur,h_cur,d_ev_f,d_ev_t,h_ev,h_delta):        
            # when testing:
            # print LT.tm_mday,'-', LT.tm_mon,'   ',  LT.tm_hour,':',LT.tm_min,',  ', ev.attrib['lamp'],ev.attrib['action']           
            logging.debug('%6s, %2s, %s',ev.attrib['lamp'],ev.attrib['action'],'{0:04d}-{1:02d}-{2:02d}, {3:02d}:{4:02d}'.format( \
            LT.tm_year,LT.tm_mon,LT.tm_mday,LT.tm_hour,LT.tm_min))
            #switch(ev.attrib['lamp'],ev.attrib['action'])
            
    

        
def threadCore():
    deltaSecs = 60.0
    while 1:                      
        t = time.time()
        print 'check'
        checkLamp(t,(1.5 * deltaSecs)/3600)        
        time.sleep(deltaSecs)


def switch(naam,action):
    setStr='Set('+str(action)+')'
    cmdClssStr='commandClasses[37]'
    if (naam=='HalBtl'):
        lampStr='devices[2]'
    if (naam=='KmrRv'):
        lampStr='devices[3]'
    if (naam=='KmrLa'):
        lampStr='devices[5]'
    if (naam=='KmrRa'):
        lampStr='devices[6]'
    if (naam=='KmrLv'):
        lampStr='devices[9]'
        cmdClssStr='commandClasses[38]'
    openStr='http://raspberrypi.fritz.box:8083/ZWaveAPI/Run/'+lampStr+'.instances[0].'+cmdClssStr+'.'+setStr
    urllib2.urlopen(openStr).read()
    #print 'http://raspberrypi.fritz.box:8083/ZWaveAPI/Run/'+lampStr+'.instances[0].commandClasses[37].'+setStr
    
#fnm = '/media/USB/test.log' # on RP    
fnm = 'C:/Temp/test.log' # on PC
logging.basicConfig(filename=fnm, format='%(asctime)s  %(message)s', datefmt='%Y-%m-%d %I:%M:%S', level=logging.DEBUG)
tree = ET.parse('G:\OneDrive\Fons\Techniek\Python\Lampcontrol\program.xml') # on PC
# tree = ET.parse('/media/USB/program.xml') # on RP
events = tree.getroot().getchildren()

if (0):
    str_tm = time.strptime("2015-Feb-15, 08:00:00", "%Y-%b-%d, %H:%M:%S")
    print sunRiseSet(time.gmtime(time.mktime(str_tm)),1,1,0)    
    checkLamp(time.mktime(str_tm),0.125) # HalBtl Off
    
if (0):
    str_tm = time.strptime("2015-Feb-08, 17:35:00", "%Y-%b-%d, %H:%M:%S")
    checkLamp(time.mktime(str_tm),0.125) # HalBtl On
    str_tm = time.strptime("2015-Feb-08, 08:15:00", "%Y-%b-%d, %H:%M:%S")
    checkLamp(time.mktime(str_tm),0.125) # HalBtl Off
    str_tm = time.strptime("2015-Feb-08, 17:05:00", "%Y-%b-%d, %H:%M:%S")
    checkLamp(time.mktime(str_tm),0.125) # KmrLa On
    str_tm = time.strptime("2015-Feb-08, 23:05:00", "%Y-%b-%d, %H:%M:%S")
    checkLamp(time.mktime(str_tm),0.125) # KmrLa Off
    str_tm = time.strptime("2015-Feb-08, 05:50:00", "%Y-%b-%d, %H:%M:%S")
    checkLamp(time.mktime(str_tm),0.125) # KmrLa nothing (weekend)
    str_tm = time.strptime("2015-Feb-09, 05:50:00", "%Y-%b-%d, %H:%M:%S")
    checkLamp(time.mktime(str_tm),0.125) # KmrLa on
    str_tm = time.strptime("2015-Feb-09, 06:35:00", "%Y-%b-%d, %H:%M:%S")
    checkLamp(time.mktime(str_tm),0.125) # KmrLa off
    str_tm = time.strptime("2015-Feb-09, 23:35:00", "%Y-%b-%d, %H:%M:%S")
    checkLamp(time.mktime(str_tm),0.125) # KmrRv off

# on RP
#thr = threading.Thread(target=threadCore)
#thr.start()

