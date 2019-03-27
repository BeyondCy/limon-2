#!/usr/bin/env python3

# <limon.py> is a simple script for batch-updating MP3 files using
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
import getopt
import requests
import sys

# external libraries
from PIL import Image
import acoustid
import eyed3

# API settings
LASTFM_URL = 'http://ws.audioscrobbler.com/2.0/?method='
LASTFM_API_KEY = "bf58f74243bf1ebedd90642338a7023f"
AID_API_KEY = 'XN07NN3TxX'

# print limon usage
def usage():
	print("usage: limon.py [-F] -d/f <directory>/<file>")
	print()
	print("-F: Full cleaning of previous tags prior to tagging")
	print("-R: Automagically repair selected MP3 files with a given title and artist")
	print()
	sys.exit(2)

# loading dots
def loading(status=0):
	if status == 1:
		print("X")
	elif status == 2:
		print("OK")
	else:
		print(".", end="")

# manual recovery
def recover(sarray):
	print()
	print("Error in processsing: %s" % sarray)
	if ("album" in sarray) and ("album_artist" in sarray):
		print("Select track entry from search list, manually enter Artist and Album Artist, or continue? (S/M/n):", end=" ")
		option = input()

		# parse vars from array
		title = sarray[2]

		# search
		if option == "S":
			# check title in case error was on AcoustID
			print("Is this track title correct: %s (y/N): " % title, end="")
			toption = input()
			if toption == "N":
				title = input("Enter new track title: ")

			# URL safe strings
			urltitle = urllib.parse.quote_plus(title)
			urlalbum_artist = urllib.parse.quote_plus(album)

			page = 1
			quit = False
			while quit == False:
				# URL generated for page
				surl = LASTFM_URL + "track.search&track=%s&artist=%s&page=%i&limit=1&api_key=%s&format=json" % (urltitle, urlalbum_artist, page, LASTFM_API_KEY)

				try:
					# load json
					sresponse = urlopen(surl)
					sresponsestring = sresponse.read().decode('utf-8')
					sjsonobj = json.loads(sresponsestring)

					print(surl)
					return 1
				except:
					print("error: error in opening URL. returning to recover menu...")
					recover(sarray)
		# manual
		elif option == "M":
			print()

			# intermediate vars for retain support
			ititle = input("Track Title (%s): " % title)
			if ititle == "":
				ititle = title

			album = input("Album: ")

			album_artist = input("Album Artist: ")
			print()

			return [album, album_artist, ititle]

		else:
			return False

# load mp3 file and update available tags
def mp3set(item, tagdict, full_flag):
	mp3 = eyed3.load(item)
	if full_flag:
		mp3.initTag()
	for i in tagdict:
		if i == 'image':
			# tag.images has a special setter
			mp3.tag.images.set(3, tagdict[5], "image/png", u"")
		else:
			mp3.tag.i = tagdict[i]

	mp3.tag.save()

# open image binary from URL
def imageget(jsonobj2):
	image = jsonobj2['album']['image'][3]['#text']
	try:
		return urlopen(image).read()
	except:
		suggest("error in image URL")
		return False

def main():
	# getopt arguments
	try:
		opts, args = getopt.getopt(sys.argv[1:], "Fd:f:", ["no-recurse"])
	except getopt.GetoptError as err:
		usage()

	# argument handling
	full_flag = False
	recovery_flag = False
	recurse_flag = True
	for o, a in opts:
		if o == "-F":
			full_flag = True
		elif o == "-d":
			# '/' at end of dir
			dirmode = True
			if a.endswith("/"):
				directory = a
			else:
				directory = a + "/"
		elif o == "-f":
			dirmode = False
			file = a
		elif o == "--no-recurse":
			recurse_flag = False
			print("recurse off")
	try:
		if dirmode:
			try:
				files = glob.glob(directory + '**/*.mp3', recursive=recurse_flag)
				os.listdir(directory)

				print("Root Directory: %s" % directory)
				print()
			except:
				print("error: no such directory exists")
				return 1
		elif dirmode == False:
			try:
				try:
					files = [file]
					open(files[0], mode='rb')

					print("Selected File: \"%s\"" % file)
					print()
				except:
					print("error: no such file exists")
					return 1
			except:
				# if neither, error
				print("error: no directory/file specified")
				usage()
	except:
		print("error: missing required arguments")
		usage()

	# rate limiting settings
	count = 0
	prevCycle = time.time()

	# main file loop
	for item in files:
		# AcoustID rate limiting
		if count >= 3:
			if (time.time() - prevCycle) < 1.05:
				time.sleep(1)
			count = 0
			prevCycle = time.time()

		# shorten to filename
		lastslash = item.rfind('/')
		filename = item[(lastslash + 1):len(item)]

		# LOADING
		print("(%s)" % ((filename[:55] + '...') if len(filename) > 55 else filename), end=" ")

		# create tag dict
		tagdict = {}

		# get title, artist
		try:
			result = next(acoustid.match(AID_API_KEY, item))
		except:
			loading(1)
			if recover(["result"]) == False:
				continue

		# LOADING .
		loading()

		# set title, artist
		title = result[2]
		tagdict['title'] = title
		artist = result[3]
		tagdict['artist'] = artist

		# URL safe strings
		urltitle = urllib.parse.quote_plus(title)
		urlartist = urllib.parse.quote_plus(artist)
		
		# URL for album, album artist
		url = LASTFM_URL + "track.getInfo&track=%s&artist=%s&api_key=%s&format=json" % (urltitle, urlartist, LASTFM_API_KEY)

		# load json
		try:
			response = urlopen(url)
			responsestring = response.read().decode('utf-8')
			jsonobj = json.loads(responsestring)
		except:
			loading(1)
			if recover(["response", "responsestring", "jsonobj"]) == False:
				continue

		# LOADING ..
		loading()

		# parse from json
		try:
			album = jsonobj['track']['album']['title']
			album_artist = jsonobj['track']['album']['artist']
		except:
			loading(1)
			albumarray = recover(["album", "album_artist", title])
			if albumarray == False:
				continue
			else:
				album = albumarray[0]
				album_artist = albumarray[1]
				title = albumarray[2]

				# recalculate filename
				lastslash = item.rfind('/')
				filename = item[(lastslash + 1):len(item)]

				# RESUME ..
				print("(%s)" % ((filename[:55] + '...') if len(filename) > 55 else filename), end=" ")
				loading()
				loading()

		# set album, album artist
		tagdict['album'] = album
		tagdict['album_artist'] = album_artist

		# URL safe strings
		urlalbum = urllib.parse.quote_plus(album)
		urlalbum_artist = urllib.parse.quote_plus(album_artist)

		# LOADING ...
		loading()

		# URL for genre, image
		url2 = LASTFM_URL + "album.getInfo&album=%s&artist=%s&api_key=%s&format=json" % (urlalbum, urlalbum_artist, LASTFM_API_KEY)

		# load json2
		try:
			response2 = urlopen(url2)
			responsestring2 = response2.read().decode('utf-8')
			jsonobj2 = json.loads(responsestring2)
		except:
			loading(1)
			if recover(["response2", "responsestring2", "jsonobj2"]) == False:
				continue

		# LOADING ....
		loading()

		genreobj = jsonobj2['album']['tags']['tag']

		# parse from json2
		try:
			genre = genreobj2[0]['name'].title()
		except:
			genre = ""
		
		# get image data
		image = imageget(jsonobj2)
		if image == False:
			loading(1)
			if recover(["image"]) == False:
				continue

		# LOADING .....
		loading()

		mp3set(item, tagdict, full_flag)
		os.rename(item, (directory + artist + ' - ' + title + '.mp3')) # Artist - Title

		# LOADING .....OK!
		loading(2)
		
		count += 1 # rate limit
	print()

# exec main
if __name__ == "__main__":
	main()