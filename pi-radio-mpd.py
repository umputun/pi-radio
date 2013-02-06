#!/usr/bin/python
# -*- coding: utf-8 -*-


 # Copyright 2013 Umputun

 # This file is part of Pi-Radio.

 # Pi-Radio is free software: you can redistribute it and/or modify
 # it under the terms of the GNU General Public License as published by
 # the Free Software Foundation, either version 3 of the License, or
 # (at your option) any later version.

 # Pi-Radio is distributed in the hope that it will be useful,
 # but WITHOUT ANY WARRANTY; without even the implied warranty of
 # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 # GNU General Public License for more details.

 # You should have received a copy of the GNU General Public License
 # along with Pi-Radio.  If not, see http://www.gnu.org/licenses/.


import web, subprocess, json, signal, time, mpd, collections

STATIONS =  {
    "FoxNews" : "http://fnradio-shoutcast-64.ng.akacast.akamaistream.net/7/115/13873/v1/auth.akacast.akamaistream.net/fnradio-shoutcast-64",
    "Classic" : "http://radio02-cn03.akadostream.ru:8100/classic128.mp3",
    u"Высоцкий" : "http://music.myradio.ua:8000/pesni-vysockogo128.mp3",
    u"Наше–Радио": "http://mp3.nashe.ru/nashe-128.mp3",
}


urls = (
    '/', 'index',
    '/apple-touch-icon.png', 'icon',
    '/list', 'list',
    '/play/(.*)', 'play',
    '/volume/(.*)', 'volume',
    '/volume(.*)', 'volume',
    '/stop', 'stop',
    '/status', 'status',
)

app = web.application(urls, globals())
index_page = open('index.html', 'r').read()

class index:
    def GET(self):
	return index_page

class icon:
    def GET(self):
	web.header('Content-Type', 'image/png')
	return open('pi-radio.png', 'r').read()

class list:
    def GET(self):
	print STATIONS
	web.header('Content-Type', 'application/json')
	return (json.dumps({'response' : {'list': collections.OrderedDict(sorted(STATIONS.items()))} }, separators=(',',':') ))

class volume:

    def GET(self, volume_level): #level between 0 and 10

	mpc = mc.get_client()

	level = int(mc.get_client().status()['volume'])
	if volume_level:
	    if int(volume_level) == 0: level = 0
	    else: level = int(volume_level)*10 # 80 + int(volume_level) * 2
	    mpc.setvol(level)
	else:
	    volume_level = level/10 # (level - 80) / 2
	print "volume level=%d, %s" % (level, volume_level)

	mc.release_client()

	web.header('Content-Type', 'application/json')
	return (json.dumps({'response' :  {'level': volume_level} }, separators=(',',':') ))

    def POST(self, volume_level): return self.GET(volume_level)

class play:
    def GET(self, station):
	print "play station="+ station.encode('utf-8')
	client = mc.get_client()
	client.stop()
	found_id = [sid for sid, st_name in mc.ids.items() if st_name == station][0]
	print "play id=%s" % found_id
	client.playid(found_id)
	mc.release_client()
	web.header('Content-Type', 'application/json')
	web.ctx.status = '201 Created'
	return (json.dumps({'response' :  {'station': STATIONS[station]} }, separators=(',',':') ))

    def POST(self, volume_level): return self.GET(volume_level)

class stop:
    def GET(self):
	print "stop"
	client = mc.get_client()
	client.stop()
	mc.release_client()
	web.header('Content-Type', 'application/json')
	return (json.dumps({'response' :  {'result' : 1} }, separators=(',',':') ))

    def POST(self): return self.GET()

class status:
    def GET(self):
	mpd_status = mc.get_client().status()
	print "status = " + str(mpd_status)
	mc.release_client()
#	volume = (int(mpd_status['volume']) - 80) / 2
	volume = int(mpd_status['volume']) / 10
	web.header('Content-Type', 'application/json')
	if mpd_status['state'] == 'play':
	    station_name = mc.ids[mpd_status['songid']]
	    return (json.dumps({'response' :  {'status' : 'play', 'station' : station_name, 'volume' : volume} }, separators=(',',':') ))
	else:
	    return (json.dumps({'response' :  {'status' : 'stop', 'volume' : volume} }, separators=(',',':') ))

class mpd_controller:
    def __init__(self, stations):
	self.client = mpd.MPDClient()

	try:
	    self.client.connect("localhost", 6600)
	except mpd.ConnectionError:
	    print "already connected"

	self.client.clear()
	self.ids = {}
	for (st_name, st_url) in stations.items():
	    self.ids[self.client.addid(st_url)] = st_name
	self.client.disconnect()

    def get_client(self):
	try:
	    self.client.connect("localhost", 6600)
	except mpd.ConnectionError:
	    print "already connected"
	return self.client

    def release_client(self):
	try:
    	    self.client.disconnect()
	except mpd.ConnectionError:
	    print "can't disconnect"


mc = mpd_controller(STATIONS)

if __name__ == "__main__":
    app.run()

