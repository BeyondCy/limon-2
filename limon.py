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

# API settings
LASTFM_URL = "http://ws.audioscrobbler.com/2.0/?method="
LASTFM_API_KEY = "bf58f74243bf1ebedd90642338a7023f"
AID_API_KEY = "XN07NN3TxX"

# print limon usage
def usage():
	print("Usage: limon.py <directory/file>")
	sys.exit(2)

# make sure all dirs have no slash
def dirformat(directory):
	if directory.endswith('/'):
		directory = directory - '/'

	return directory

def loading():
	sys.stdout.write('.')
	sys.stdout.flush()

# URL safe strings
def gurl(string):
	return urllib.parse.quote_plus(string)

def search(url):
	response = urlopen(url)
	responsestring = response.read().decode('utf-8')
	jsonobj = json.loads(responsestring)

	return jsonobj

# fancy menu for errors
def menu(optarray):
	for opt in optarray:
		print("[%i]: %s" % ((optarray.index(opt) + 1), opt))

	print()
	try:
		choice = int(input("[?]: "))
	except:
		print("ERROR: Choice must be of type 'int'")
		print()
		return menu(optarray)

	if (choice > (optarray.index(opt)) + 1) or (choice < 1):
		print("ERROR: Choice out of range")
		print()
		return menu(optarray)

	return choice

# pick and choose track from search list
def tracksearch(title, artist):
	print()
	print("<--TRACK SEARCH-->")

	# manual title?
	trackopt = input("Track title is \"%s\", correct? (y/N): " % title)
	if trackopt == "N":
		title = input("Enter new track title: ")

	# manual artist?
	artistopt = input("Artist is \"%s\", correct? (y/N): " % artist)
	if artistopt == "N":
		artist = input("Enter new artist: ")

	page = 0
	select = False
	while select == False:
		aurl = LASTFM_URL + "track.search&track=%s&artist=%s&page=%i&limit=1&api_key=%s&format=json" % (gurl(title), gurl(artist), page, LASTFM_API_KEY)
		ajsonobj = search(aurl)

		atitle = ajsonobj['results']['trackmatches']['track'][0]['name']
		aartist = ajsonobj['results']['trackmatches']['track'][0]['artist']

		narray = malbum(title, artist, False)
		aalbum = narray[1]
		aalbum_artist = narray[2]

		print()
		print("  Title: %s" % atitle)
		print("  Artist: %s" % aartist)
		print()
		print("  Album: %s" % aalbum)
		print("  Album Artist: %s" % aalbum_artist)
		#print("  Genre: %s" % agenre)
		#print("  Image: %s" % aimg)
		print()
		aopt = input("Is this information correct? (Y/n): ")

		if aopt == "Y":
			title = atitle
			artist = aartist
			select = True;
		else:
			copt = input("Enter manual search (or continue)? (Y/n): ")
			if copt == "Y":
				return manual(title, artist)

		page += 1

	print("<---------------->")
	print()

	return [title, artist]

def manual(title, artist):
	print()
	print("<-----MANUAL----->")

	title = input("Track title (%s): " % title)
	artist = input("Artist (%s): " % artist)

	# album suggestion
	zarray = malbum(title, artist, False)
	zalbum = zarray[1]

	album = input("Album (%s): " % zalbum)

	if album == zalbum:
		album_artist = input("Album Artist (%s): " % zalbum_artist)
	else:
		album_artist = input("Album Artist: ")

	print("<---------------->")
	print()

	return [title, album, album_artist]

# load mp3 file and update available tags
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
def imageget(jsonobj2):
	base = jsonobj2['album']['image']
	try:
		nimage = base[len(base.keys()) - 1]['#text']
	except:
		sys.stdout.write('NoIMG')
		sys.stdout.flush()
		return ""

	try:
		image = urlopen(nimage).read()
	except:
		sys.stdout.write('NoIMG')
		sys.stdout.flush()
		return ""

	return image

# album, album artist
def malbum(title, artist, error=True):
	url = LASTFM_URL + "track.getInfo&track=%s&artist=%s&api_key=%s&format=json" % (gurl(title), gurl(artist), LASTFM_API_KEY)
	jsonobj = search(url)

	album = ""
	album_artist = ""

	try:
		album = jsonobj['track']['album']['title']
		album_artist = jsonobj['track']['album']['artist']
	except:
		if error:
			print("\nERROR: The selected track's album could not be found.")
			opt = menu(["Search track entries", "Manually enter details to resume processing", "Skip this file"])
			
			# search
			if opt == 1:
				tarray = tracksearch(title, artist)
				title = tarray[0]
				artist = tarray[1]

				return malbum(title, artist)

			#manual
			elif opt == 2:
				varray = manual(track, artist)
				title = varray[0]
				album = varray[1]
				album_artist = varray[2]

			#skip
			else:
				return False

	return [title, album, album_artist]

def main():
	# directory/file arg
	try:
		inp = sys.argv[1]
		files = []
	except:
		sys.stdout.write("ERROR: No input file/directory specified.")
		usage()

	# directory or file?
	if os.path.isfile(inp):
		files = [inp]
	else:
		inp = dirformat(inp)
		files = glob.iglob("%s/**/*.mp3" % inp, recursive=True)

	# rate limiting settings
	count = 0
	prevcycle = time.time()

	# main file loop
	for item in files:
		# AcoustID rate limiting
		if count >= 3:
			if (time.time() - prevcycle) < 1.05:
				time.sleep(1)
			count = 0
			prevcycle = time.time()

		# LOADING
		print("(%s) " % ((item[:55] + '...') if len(item) > 55 else item), end='')

		# create tag dict
		tagdict = {}

		# get title, artist
		try:
			result = next(acoustid.match(AID_API_KEY, item))
		except: 
			loading()
			if recover(["result"]) == False:
				continue

		loading()

		# set title, artist
		title = result[2]
		artist = result[3]

		# add title, artist to tags
		tagdict['artist'] = artist

		# get album, album artist
		aarray = malbum(title, artist)
		if aarray == False:
			continue

		title = aarray[0]
		album = aarray[1]
		album_artist = aarray[2]

		# add album, album artist to tags
		tagdict['title'] = title
		tagdict['album'] = album
		tagdict['album_artist'] = album_artist

		loading()

		# URL for genre, image
		url2 = LASTFM_URL + "album.getInfo&album=%s&artist=%s&api_key=%s&format=json" % (gurl(album), gurl(album_artist), LASTFM_API_KEY)

		# load json2
		try:
			jsonobj2 = search(url2)
		except:
			loading()
			#if recover(["response2", "responsestring2", "jsonobj2"]) == False:
				#continue

		genreobj = jsonobj2['album']['tags']['tag']

		# parse from json2
		try:
			genre = genreobj2[0]['name'].title()
		except:
			genre = ""

		tagdict['genre'] = genre
		
		# get image data
		image = imageget(jsonobj2)
		if image == False:
			loading()
			#if recover(["image"]) == False:
				#continue

		loading()

		# apply tags
		mp3set(item, tagdict)

		# get correct slash character ( Windows >:( )
		if os.name == "nt":
			slash = "\\"
		else:
			slash = "/"

		# rename
		directory = item.rsplit(slash)[0] + slash
		try:
			os.rename(item, (directory + artist + ' - ' + title + '.mp3')) # Artist - Title
		except:
			print("\nWARNING: Restart with root permissions to rename.")
		
		count += 1 # rate limit
	print()

# exec main
if __name__ == "__main__":
	main()