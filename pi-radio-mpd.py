#!/usr/bin/env python
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


import web, subprocess, json, signal, time, mpd, collections, threading


DEFAULT_STATIONS =  { #internal list of stations. used if no stattions.list file found
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
        print mc.get_stations()
        web.header('Content-Type', 'application/json')
        return (json.dumps({'response' : {'list': collections.OrderedDict(sorted(mc.get_stations().items()))} }, separators=(',',':') ))

class volume:

    def GET(self, volume_level): #level between 0 and 10

        try:
            client = mc.acquire_client()

            if volume_level:
                client.setvol(int(volume_level)*10)
            else:
                volume_level = int(client.status().get('volume', '50'))/10
            print "volume level=%s" % volume_level

            web.header('Content-Type', 'application/json')
            return (json.dumps({'response' :  {'level': volume_level} }, separators=(',',':') ))
        finally:
            mc.release_client()

    def POST(self, volume_level): return self.GET(volume_level)

class play:
    def GET(self, station):
        try:
            print "play station="+ station.encode('utf-8')
            client = mc.acquire_client()
            client.stop()
            found_id = [sid for sid, st_name in mc.ids.items() if st_name == station][0]
            print "play id=%s" % found_id
            client.playid(found_id)
            web.header('Content-Type', 'application/json')
            web.ctx.status = '201 Created'
            return (json.dumps({'response' :  {'station':  mc.get_stations()[station]} }, separators=(',',':') ))
        finally:
            mc.release_client()

    def POST(self, station): return self.GET(station)

class stop:
    def GET(self):
        try:
            print "stop"
            client = mc.acquire_client()
            client.stop()
            web.header('Content-Type', 'application/json')
            return (json.dumps({'response' :  {'result' : 1} }, separators=(',',':') ))
        finally:
            mc.release_client()

    def POST(self): return self.GET()

class status:
    def GET(self):
        try:
            client = mc.acquire_client()
            mpd_status = client.status()
            volume = int(mpd_status.get('volume', '50')) / 10
            web.header('Content-Type', 'application/json')
            if mpd_status['state'] == 'play':
                station_name = mc.ids[mpd_status['songid']]
                current_song = client.currentsong().get('title', '')
                return (json.dumps({'response' :  {'status' : 'play', 'station' : station_name,
                    'volume' : volume, "currentsong" : current_song} }, separators=(',',':') ))
            else:
                return (json.dumps({'response' :  {'status' : 'stop', 'volume' : volume} },
                    separators=(',',':') ))
        finally:
            mc.release_client()


class mpd_controller:
    def __init__(self, stations):
        self.client = mpd.MPDClient()
        self.stations = stations
        self.lock = threading.Lock()

        try:
            self.client.connect("localhost", 6600)
        except mpd.ConnectionError:
            print "already connected"

        self.client.clear()
        self.ids = {}
        for (st_name, st_url) in stations.items():
            self.ids[self.client.addid(st_url)] = st_name
        self.client.disconnect()

    def acquire_client(self):
        try:
            self.lock.acquire()
            self.client.connect("localhost", 6600)
        except mpd.ConnectionError:
            print "already connected"

        return self.client

    def release_client(self):
        try:
            self.client.disconnect()
        except mpd.ConnectionError:
            print "can't disconnect"
        finally:
            self.lock.release()

    def get_stations(self):
        return self.stations

def load_stations():
    try:
        result = dict( (st_name.strip().decode('utf-8'), st_url.strip())
            for st_name,st_url in (a.split(',') for a in open("stations.list").read().splitlines() ) )
        print "total %d stations loaded" % len(result)
        return result
    except IOError as e:
        print "stations.list not found, internal list loaded"
        return DEFAULT_STATIONS

mc = mpd_controller(load_stations())

if __name__ == "__main__":
    web.config.debug = False
    app.run()

