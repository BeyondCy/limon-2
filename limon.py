#!/usr/bin/env python3

# <limon.py> is a Python script for batch-updating MP3 files using
# information gathered from the Internet.

# All credits go to Pillow, AcoustID, eyeD3, and the Python Software
# Foundation.

# internal libraries
from io import BytesIO
from urllib.request import urlopen
import urllib.parse
import time
import glob
import json
import os
import requests
import sys

# external libraries
from PIL import Image
import acoustid
import eyed3

# limon version
version = "0.1"

# API settings
LASTFM_URL = "http://ws.audioscrobbler.com/2.0/?method="
LASTFM_API_KEY = "bf58f74243bf1ebedd90642338a7023f"
AID_API_KEY = "XN07NN3TxX"

# get correct slash character - Windows >:(
if os.name == "nt":
	slash = "\\"
else:
	slash = "/"

# general mp3 attrib class
class MP3:
	def __init__(self):
		self.title = ""
		self.artist = ""
		self.album = ""
		self.album_artist
		self.genre = ""
		self.trackid = ""
		self.image = ""

# (abc.mp3) ... class
class Listing(MP3):
	def __init__(self, item):
		self.title = "(%s)" % item
		self.loading = 0
		self.errqueue = []

	def print(self):
		print("%s " % self.title, end="")
		for i in range(0, self.loading):
			sys.stdout.write('.')
		sys.stdout.flush()

	def print_err(self):
		for err in self.errqueue:
			sys.stdout.write(" >> %s" % err)
		sys.stdout.flush()
		print()

	def add_err(self, err):
		self.errqueue.append(err)

	def load(self):
		self.loading += 1
		sys.stdout.write('.')
		sys.stdout.flush()

	def quit(self):
		print('X')
		self.print_err()

# print limon usage
def usage():
	print("Usage: limon.py <directory/file>")
	sys.exit(2)

# make sure all dirs have no slash
def dirformat(directory):
	if directory.endswith(slash):
		directory = directory - slash

	return directory

# URL safe strings
def safeurl(string):
	return urllib.parse.quote_plus(string.encode('utf-8'))

def search2json(url):
	response = urlopen(url)
	responsestring = response.read().decode('utf-8')
	jsonobj = json.loads(responsestring)

	return jsonobj

# check for tags before applying them
def mp3(item, tagdict):
	mp3 = eyed3.load(item)
	mp3.initTag()

	# check stuff to-do

	mp3set(item, tagdict)

# load mp3 file and apply available tags
def mp3set(item, tagdict):
	mp3 = eyed3.load(item)
	mp3.initTag()
	for tag in tagdict:
		if tag == 'image':
			# tag.images has a special setter
			mp3.tag.images.set(3, tagdict[5], "image/png", u"")
		else:
			setattr(mp3.tag, tag, tagdict[tag])

	mp3.tag.save()

# open image binary from URL
def getimage(jsonobj2):
	base = jsonobj2['album']['image']
	try:
		nimage = base[len(base) - 1]['#text']
		try:
			image = urlopen(nimage).read()
		except:
			sys.stdout.write('NoIMG')
			sys.stdout.flush()
			return ""
	except:
		sys.stdout.write('NoIMG')
		sys.stdout.flush()
		return ""

	return image

# album, album artist
def getalbum(title, artist):
	url = LASTFM_URL + "track.getInfo&track=%s&artist=%s&api_key=%s&format=json" % (safeurl(title), safeurl(artist), LASTFM_API_KEY)
	jsonobj = search2json(url)

	album = ""
	album_artist = ""

	try:
		album = jsonobj['track']['album']['title']
		album_artist = jsonobj['track']['album']['artist']
	except:
		return False

	return [title, album, album_artist]

def main():
	# directory/file arg
	try:
		inp = sys.argv[1]
		files = []
	except:
		print("ERROR: No input file/directory specified.")
		usage()

	# directory or file?
	if os.path.isfile(inp):
		files = [inp]
	elif os.path.isdir(inp):
		inp = dirformat(inp)
		files = glob.iglob("%s/**/*.mp3" % inp, recursive=True)
	else: # not a file or dir, must not exist
		print("ERROR: File does not exist.")
		sys.exit(1)

	# rate limiting settings
	count = 0
	prevcycle = time.time()

	# main file loop
	print("<<< Limon v%s >>>\n" % version)
	for item in files:
		# AcoustID rate limiting
		if count >= 3:
			if (time.time() - prevcycle) < 1.05:
				time.sleep(1)
			count = 0
			prevcycle = time.time()

		# LOADING
		listing = Listing(item)
		listing.print()
		listing.load()

		# list of tags to be applied
		tagdict = {}

		# get title, artist
		try:
			result = next(acoustid.match(AID_API_KEY, item))
		except: 
			listing.add_err("ERROR: File not found in database.")
			listing.quit()
			continue

		# set title, artist
		firsttitle = result[2] # temporary title
		listing.artist = result[3]

		if firsttitle == None or listing.artist == None:
			listing.add_err("ERROR: Database returned unexpected result.")
			listing.quit()
			continue

		# add artist to tags
		# tagdict['title'] = title (title is verified from album)
		tagdict['artist'] = listing.artist

		# get album, album artist
		aarray = getalbum(firsttitle, listing.artist)
		if aarray == False:
			listing.add_err("ERROR: Album not found.")
			listing.quit()
			continue

		listing.title = aarray[0]
		listing.album = aarray[1]
		listing.album_artist = aarray[2]

		# add title, album, album artist to tags
		tagdict['title'] = listing.title
		tagdict['album'] = listing.album
		tagdict['album_artist'] = listing.album_artist

		listing.load()

		# URL for genre, image
		url2 = LASTFM_URL + "album.getInfo&album=%s&artist=%s&api_key=%s&format=json" % (safeurl(listing.album), safeurl(listing.album_artist), LASTFM_API_KEY)

		# load json2
		try:
			jsonobj2 = search2json(url2)
		except:
			listing.add_err("ERROR: Can't retrieve album information.")
			listing.quit()
			continue

		genreobj = jsonobj2['album']['tags']['tag']

		# parse from json2
		try:
			listing.genre = genreobj2[0]['name'].title()
			tagdict['genre'] = listing.genre
		except:
			listing.add_err("WARNING: Genre not found.")
		
		# get image data
		listing.image = getimage(jsonobj2)
		if listing.image == False:
			listing.add_err("WARNING: Album art not found.")

		listing.load()

		# check for and apply tags
		mp3(item, tagdict)

		# rename
		directory = item.rsplit(slash)[0] + slash
		try:
			os.rename(item, (directory + listing.artist + ' - ' + listing.title + '.mp3')) # Artist - Title
		except:
			listing.add_err("WARNING: Restart with root permissions to rename.")
		
		# DONE
		print("OK!")

		listing.print_err()
		del listing # remove from memory

		count += 1 # rate limit
	print()

# exec main
if __name__ == "__main__":
	main()

input("Press ENTER to continue...")