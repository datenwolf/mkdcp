#!/usr/bin/env python
# -*- coding: utf8 -*-

def generate_SMPTE_CPL():

import subprocess, time

try:
	from lxml import etree
	print("running with lxml.etree")
except ImportError:
	try:
		# Python 2.5
		import xml.etree.cElementTree as etree
		print("running with cElementTree on Python 2.5+")
	except ImportError:
		try:
			# Python 2.5
			import xml.etree.ElementTree as etree
			print("running with ElementTree on Python 2.5+")
		except ImportError:
			try:
				# normal cElementTree install
				import cElementTree as etree
				print("running with cElementTree")
			except ImportError:
				try:
					# normal ElementTree install
					import elementtree.ElementTree as etree
					print("running with ElementTree")
				except ImportError:
					print("Failed to import ElementTree from any known place")

CREATOR = 'DraxIT mkdcp 0.1'
ISSUEDATE = time.strftime('%FT%T%z')
ISSUER = ''

def asdcp_genuuid():
	return subprocess.Popen(['asdcp-test', '-u'], stdout=subprocess.PIPE).stdout.read().strip()

def asdcp_digest(filename):
	digest, file = subprocess.Popen(['asdcp-test', '-t', filename], stdout=subprocess.PIPE).stdout.read().strip().split(' ')
	return digest

class Asset:
	def __init__(self):
		self.UUID = asdcp_genuuid()

	def yield_cpl_SMPTE(self, head_element)
		etree.SubElement(_asset, 'Id'                ).text = 'urn:uuid:' + asset.UUID
		etree.SubElement(_asset, 'AnnotationText'    ).text = escape(asset.annotation.encode('ascii', 'xmlcharrefreplace'))
		etree.SubElement(_asset, 'Hash'              ).text = asset.digest
		etree.SubElement(_asset, 'EditRate'          ).text = asset.editrate
		etree.SubElement(_asset, 'EntryPoint'        ).text = asset.entrypoint
		etree.SubElement(_asset, 'IntrinsicDuration' ).text = asset.intrisicduration
		etree.SubElement(_asset, 'Duration'          ).text = asset.duration

class CompositionPlayList(Asset):
	def __init__(self, title, kind, reellist=None, rating=None):
		self.UUID = asdcp_genuuid()
		if reellist:
			self.reellist = reellist
		else:
			self.reellist = []

		self.rating = rating

	def AddReel(self, reel):
		self.reellists.append(reel)

	def yield_SMPTE(reellist):
		from xml.sax.saxutils import escape
		
		title = escape(self.title.encode('ascii', 'xmlcharrefreplace'))

		# CPL head
		cpl = etree.Element('{http://www.smpte-ra.org/schemas/429-7/2006/CPL}CompositionPlaylist')

		etree.SubElement(cpl, 'Id'               ).text = 'urn:uuid:' + self.UUID
		etree.SubElement(cpl, 'IssueDate'        ).text = ISSUEDATE
		etree.SubElement(cpl, 'Issuer'           ).text = ISSUER
		etree.SubElement(cpl, 'Creator'          ).text = CREATOR
		etree.SubElement(cpl, 'ContentTitleText' ).text = title
		etree.SubElement(cpl, 'ContentKind'      ).text = self.kind

		contentversion = etree.SubElement(cpl, 'ContentVersion')
		etree.SubElement(contentversion, 'Id'        ).text = 'urn:uri:' + title.replace(' ','-') + '_' + ISSUEDATE
		etree.SubElement(contentversion, 'LabelText' ).text = title

		etree.SubElement(cpl, 'RatingList')

		# Reels
		_reellist = etree.SubElement(cpl, 'ReelList')

		for reel in reellist:
			_reel = etree.SubElement(_reellist, 'Reel')
			etree.SubElement(_reel, 'Id').text = 'urn:uuid:' + reel.UUID
			_assetlist = etree.SubElement(_reel, 'AssetList')

				for asset in reel.assetlist:
					asset.cpl_SMPTE(_reel)

					if isinstance(asset, PictureTrack):
					if isinstance(asset, StereoscopicPictureTrack):
						_asset = etree.SubElement(_assetlist, '{http://www.smpte-ra.org/schemas/429-10/2008/Main-Stereo-Picture-CPL}MainStereoscopicPicture', nsmap={'msp-cpl': 'http://www.smpte-ra.org/schemas/429-10/2008/Main-Stereo-Picture-CPL'} )
					if isinstance(asset, SoundTrack):
						_asset = etree.SubElement(_assetlist, 'MainSound')
					

		return etree.tostring(cpl, encoding="UTF-8")
		

class PackingList(Asset):
	
class Track(Asset):
	pass

class SoundTrack(Track):
	def yield_cpl_SMPTE(self, head_element):
		_asset = etree.SubElement(head_element, 'MainSound')
		super().yield_cpl_SMPTE(_asset)

class PictureTrack(Track):
	def yield_cpl_SMPTE(self, head_element):
		_asset = etree.SubElement(head_element, 'MainPicture')
		super().yield_cpl_SMPTE(_asset)
		

class Reel:
	def __init__(self):
		self.UUID=asdcp_genuid()

