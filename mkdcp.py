#!/usr/bin/env python
# -*- coding: utf8 -*-

import subprocess, time, os, os.path
from xml.sax.saxutils import escape

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

def dcp_digest(string):
	import hashlib, base64
	sha1 = hashlib.sha1()
	sha1.update(string)
	return base64.b64encode(sha1.digest())

def asdcp_readheader(filename):
	asdcp = subprocess.Popen(['asdcp-test', '-H', '-i', filename], stdout=subprocess.PIPE)
	asdcp_output = asdcp.stdout.readlines()
	asdcp.wait()

	if asdcp.returncode != 0: # asdcp-test failed - maybe MXF Interop stereoscopic picture
		asdcp = subprocess.Popen(['asdcp-test', '-3', '-H', '-i', filename], stdout=subprocess.PIPE)
		asdcp_output = asdcp.stdout.readlines()
		asdcp.wait()

		if asdcp.returncode != 0: # asdcp-test failed again
			return None
	
	attr_dict = dict()
	for field in [attr.strip().split(': ') for attr in asdcp_output if True in [ 
		e in attr for e in [
			'StoredWidth:', 
			'StoredHeight:', 
			'EditRate:', 
			'SampleRate:', 
			'AudioSamplingRate:',
			'AspectRatio:', 
			'Duration:', 
			'AssetUUID:',
			'Label Set Type:',
			'audio', 
			'pictures' ]
		] 
	]:
		if len(field) == 2:
			attr_dict[field[0]] = field[1]
		else:
			attr_dict['type'] = field[0]
	
	UUID = attr_dict['AssetUUID']

	if 'audio' in attr_dict['type']:
		asset = SoundTrack()
		asset.targetfilename = UUID + '_pcm.mxf'
	
	if 'pictures' in attr_dict['type']:
		asset = PictureTrack(stereoscopic = 'stereoscopic' in attr_dict['type'])
		asset.targetfilename = UUID + '_j2c.mxf'
		asset.framerate = tuple(map(int,attr_dict['SampleRate'].split('/')))
		asset.width = int(attr_dict['StoredWidth'])
		asset.height = int(attr_dict['StoredHeight'])
		asset.aspectratio = tuple(map(int, attr_dict['AspectRatio'].split('/')))

	asset.UUID       = UUID 
	asset.editrate   = tuple(map(int,attr_dict['EditRate'].split('/')))
	asset.duration   = int(attr_dict['ContainerDuration']) ; asset.intrinsicduration = asset.duration
	asset.annotation = "Source file: '" + os.path.basename(filename) + "'"
	asset.originalfilename = filename
	asset.size = os.stat(filename).st_size

	asset.digest = asdcp_digest(filename)

	return asset


class Asset(object):
	def __init__(self):
		self.UUID = asdcp_genuuid()
		self.digest = ''
		self.size = 0
	
	def yield_pkl_SMPTE(self, head_element):
		etree.SubElement(head_element, 'Id'                ).text = 'urn:uuid:' + self.UUID
		etree.SubElement(head_element, 'AnnotationText'    ).text = escape(self.annotation.encode('ascii', 'xmlcharrefreplace'))
		etree.SubElement(head_element, 'Hash'              ).text = self.digest
		etree.SubElement(head_element, 'Size'              ).text = '%d' % (self.size,)
		etree.SubElement(head_element, 'OriginalFilename'  ).text = self.targetfilename # the PKL original filename is our target filename!
	
	def yield_pkl_Interop(self, head_element):
		etree.SubElement(head_element, 'Id'                ).text = 'urn:uuid:' + self.UUID
		etree.SubElement(head_element, 'AnnotationText'    ).text = escape(self.annotation.encode('ascii', 'xmlcharrefreplace'))
		etree.SubElement(head_element, 'Hash'              ).text = self.digest
		etree.SubElement(head_element, 'Size'              ).text = '%d' % (self.size,)
		etree.SubElement(head_element, 'OriginalFilename'  ).text = self.targetfilename # the PKL original filename is our target filename!
	
	def yield_am_SMPTE(self, head_element):
		_asset = etree.SubElement(head_element, 'Asset')
		etree.SubElement(_asset, 'Id').text = 'urn:uuid:' + self.UUID
		yield_ChunkList_SMPTE(_asset)

	def yield_ChunkList_SMPTE(self, head_element):
		_chunklist = etree.SubElement(head_element, 'ChunkList')
		_chunk = etree.SubElement(_chunklist, 'Chunk')
		etree.SubElement(_chunk, 'Path').text = self.targetfilename
		etree.SubElement(_chunk, 'VolumeIndex').text = '1'
		etree.SubElement(_chunk, 'Offset').text = '0'
		etree.SubElement(_chunk, 'Length').text = '%d' % (self.size,)
		
	def yield_am_Interop(self, head_element):
		_asset = etree.SubElement(head_element, 'Asset')
		etree.SubElement(_asset, 'Id').text = 'urn:uuid:' + self.UUID
		yield_ChunkList_Interop(_asset)

	def yield_ChunkList_Interop(self, head_element):
		_chunklist = etree.SubElement(head_element, 'ChunkList')
		_chunk = etree.SubElement(_chunklist, 'Chunk')
		etree.SubElement(_chunk, 'Path').text = self.targetfilename
		
class Track(Asset):
	def __init__(self):
		super(Track, self).__init__()
		self.entrypoint = 0

	def yield_cpl_SMPTE(self, head_element):
		etree.SubElement(head_element, 'Id'                ).text = 'urn:uuid:' + self.UUID
		etree.SubElement(head_element, 'AnnotationText'    ).text = escape(self.annotation.encode('ascii', 'xmlcharrefreplace'))
		etree.SubElement(head_element, 'Hash'              ).text = self.digest
		etree.SubElement(head_element, 'EditRate'          ).text = '%d %d' % self.editrate
		etree.SubElement(head_element, 'EntryPoint'        ).text = '%d' % (self.entrypoint,)
		etree.SubElement(head_element, 'IntrinsicDuration' ).text = '%d' % (self.intrinsicduration,)
		etree.SubElement(head_element, 'Duration'          ).text = '%d' % (self.duration,)
	
	def yield_cpl_Interop(self, head_element):
		etree.SubElement(head_element, 'Id'                ).text = 'urn:uuid:' + self.UUID
		etree.SubElement(head_element, 'AnnotationText'    ).text = escape(self.annotation.encode('ascii', 'xmlcharrefreplace'))
		etree.SubElement(head_element, 'Hash'              ).text = self.digest
		etree.SubElement(head_element, 'EditRate'          ).text = '%d %d' % self.editrate
		etree.SubElement(head_element, 'EntryPoint'        ).text = '%d' % (self.entrypoint,)
		etree.SubElement(head_element, 'IntrinsicDuration' ).text = '%d' % (self.intrinsicduration,)
		etree.SubElement(head_element, 'Duration'          ).text = '%d' % (self.duration,)

class CompositionPlayList(Asset):
	def __init__(self, title, kind, reels=list(), rating=None):
		super(CompositionPlayList, self).__init__()
		self.title = title
		self.annotation = "Playlist '" + title + "'"
		self.kind = kind
		self.reels = reels
		self.rating = rating
		self.targetfilename = self.UUID + '_cpl.xml'

	def xml_SMPTE(self):
		title = escape(self.title.encode('ascii', 'xmlcharrefreplace'))

		# CPL head
		cpl = etree.Element('{http://www.smpte-ra.org/schemas/429-7/2006/CPL}CompositionPlaylist', 
		                    nsmap={None: 'http://www.smpte-ra.org/schemas/429-7/2006/CPL'})

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
		reellist = etree.SubElement(cpl, 'ReelList')

		for reel in self.reels:
			reel.yield_cpl_SMPTE(reellist)

		_xml = etree.tostring(cpl, pretty_print=True, xml_declaration=True, standalone=None, encoding='UTF-8')
		self.size = len(_xml)
		self.digest = dcp_digest(_xml)
		return _xml

	def xml_Interop(self):
		title = escape(self.title.encode('ascii', 'xmlcharrefreplace'))

		# CPL head
		cpl = etree.Element('{http://www.digicine.com/PROTO-ASDCP-CPL-20040511#}CompositionPlaylist', 
		                    nsmap={None: 'http://www.digicine.com/PROTO-ASDCP-CPL-20040511#'})

		etree.SubElement(cpl, 'Id'               ).text = 'urn:uuid:' + self.UUID
		etree.SubElement(cpl, 'IssueDate'        ).text = ISSUEDATE
		etree.SubElement(cpl, 'Issuer'           ).text = ISSUER
		etree.SubElement(cpl, 'Creator'          ).text = CREATOR
		etree.SubElement(cpl, 'ContentTitleText' ).text = title
		etree.SubElement(cpl, 'ContentKind'      ).text = self.kind

		etree.SubElement(cpl, 'RatingList')

		# Reels
		reellist = etree.SubElement(cpl, 'ReelList')

		for reel in self.reels:
			reel.yield_cpl_Interop(reellist)

		_xml = etree.tostring(cpl, pretty_print=True, xml_declaration=True, standalone=None, encoding='UTF-8')
		self.size = len(_xml)
		self.digest = dcp_digest(_xml)
		return _xml
	
	def write_SMPTE(self):
		pass
	
	def write_Interop(self):
		pass

	def yield_pkl_SMPTE(self, head_element):
		super(CompositionPlayList, self).yield_pkl_SMPTE(head_element)
		etree.SubElement(head_element, 'Type').text = 'text/xml'
	
	def yield_pkl_Interop(self, head_element):
		super(CompositionPlayList, self).yield_pkl_Interop(head_element)
		etree.SubElement(head_element, 'Type').text = 'text/xml;asdcpKind=CPL'

class PackingList(Asset):
	def __init__(self, assets=list()):
		super(PackingList, self).__init__()
		self.assets = assets
		self.targetfilename = self.UUID + '_pkl.xml'

	def xml_SMPTE(self):
		pkl = etree.Element('{http://www.smpte-ra.org/schemas/429-8/2007/PKL}PackingList', 
		                    nsmap={None: 'http://www.smpte-ra.org/schemas/429-8/2007/PKL'})
		etree.SubElement(pkl, 'Id'               ).text = 'urn:uuid:' + self.UUID
		etree.SubElement(pkl, 'IssueDate'        ).text = ISSUEDATE
		etree.SubElement(pkl, 'Issuer'           ).text = ISSUER
		etree.SubElement(pkl, 'Creator'          ).text = CREATOR
		etree.SubElement(pkl, 'Annotation' )

		_assetlist = etree.SubElement(pkl, 'AssetList')

		for asset in self.assets:
			_asset = etree.SubElement(_assetlist, 'Asset')
			asset.yield_pkl_SMPTE(_asset)

		_xml = etree.tostring(pkl, pretty_print=True, xml_declaration=True, standalone=True, encoding='UTF-8')
		self.size=len(_xml)
		self.digest=dcp_digest(_xml)
		return _xml
	
	def xml_Interop(self):
		pkl = etree.Element('{http://www.smpte-ra.org/schemas/429-8/2007/PKL}PackingList', 
		                    nsmap={None: 'http://www.smpte-ra.org/schemas/429-8/2007/PKL'})
		etree.SubElement(pkl, 'Id'               ).text = 'urn:uuid:' + self.UUID
		etree.SubElement(pkl, 'IssueDate'        ).text = ISSUEDATE
		etree.SubElement(pkl, 'Issuer'           ).text = ISSUER
		etree.SubElement(pkl, 'Creator'          ).text = CREATOR
		etree.SubElement(pkl, 'Annotation' )

		_assetlist = etree.SubElement(pkl, 'AssetList')

		for asset in self.assets:
			_asset = etree.SubElement(_assetlist, 'Asset')
			asset.yield_pkl_Interop(_asset)

		_xml = etree.tostring(pkl, pretty_print=True, xml_declaration=True, standalone=True, encoding='UTF-8')
		self.size=len(_xml)
		self.digest=dcp_digest(_xml)
		return _xml

	def yield_am_SMPTE(self, head_element):
		_asset = etree.SubElement(head_element, 'Asset')
		etree.SubElement(_asset, 'Id').text = 'urn:uuid:' + self.UUID
		etree.SubElement(_asset, 'PackingList').text = 'true'
		yield_ChunkList_SMPTE(_asset)
	
	def yield_am_Interop(self, head_element):
		_asset = etree.SubElement(head_element, 'Asset')
		etree.SubElement(_asset, 'Id').text = 'urn:uuid:' + self.UUID
		etree.SubElement(_asset, 'PackingList')
		yield_ChunkList_Interop(_asset)

class SoundTrack(Track):
	def __init__(self):
		super(SoundTrack, self).__init__()
		
	def yield_cpl_SMPTE(self, head_element):
		asset = etree.SubElement(head_element, 'MainSound')
		super(SoundTrack, self).yield_cpl_SMPTE(asset)

	def yield_cpl_Interop(self, head_element):
		asset = etree.SubElement(head_element, 'MainSound')
		super(SoundTrack, self).yield_cpl_Interop(asset)

	def yield_pkl_SMPTE(self, head_element):
		super(SoundTrack, self).yield_pkl_SMPTE(head_element)
		etree.SubElement(head_element, 'Type').text = 'application/mxf'
	
	def yield_pkl_Interop(self, head_element):
		super(SoundTrack, self).yield_pkl_Interop(head_element)
		etree.SubElement(head_element, 'Type').text = 'application/x-smpte-mxf;asdcpKind=Sound'

class PictureTrack(Track):
	def __init__(self, stereoscopic = False):
		super(PictureTrack, self).__init__()
		self.stereoscopic = stereoscopic

	def yield_cpl_SMPTE(self, head_element):
		if self.stereoscopic:
			asset = etree.SubElement(
				head_element, 
				'{http://www.smpte-ra.org/schemas/429-10/2008/Main-Stereo-Picture-CPL}MainStereoscopicPicture', 
				nsmap={'msp-cpl': 'http://www.smpte-ra.org/schemas/429-10/2008/Main-Stereo-Picture-CPL'} )
		else:
			asset = etree.SubElement(head_element, 'MainPicture')
		super(PictureTrack, self).yield_cpl_SMPTE(asset)
		etree.SubElement(asset, 'FrameRate').text = '%d %d' % self.framerate
		etree.SubElement(asset, 'ScreenAspectRatio').text = '%d %d' % self.aspectratio
	
	def yield_cpl_Interop(self, head_element):
		if self.stereoscopic:
			asset = etree.SubElement(
				head_element, 
				'{http://www.digicine.com/PROTO-ASDCP-CPL-20040511#}MainStereoscopicPicture', 
				nsmap={'msp-cpl': 'http://www.digicine.com/PROTO-ASDCP-CPL-20040511#'} )
		else:
			asset = etree.SubElement(head_element, 'MainPicture')
		super(PictureTrack, self).yield_cpl_Interop(asset)
		etree.SubElement(asset, 'FrameRate').text = '%d %d' % self.framerate
		etree.SubElement(asset, 'ScreenAspectRatio').text = '%.2f' % (float(self.aspectratio[0])/float(self.aspectratio[1]),)

	def yield_pkl_SMPTE(self, head_element):
		super(PictureTrack, self).yield_pkl_SMPTE(head_element)
		etree.SubElement(head_element, 'Type').text = 'application/mxf'
	
	def yield_pkl_Interop(self, head_element):
		super(PictureTrack, self).yield_pkl_Interop(head_element)
		etree.SubElement(head_element, 'Type').text = 'application/x-smpte-mxf;asdcpKind=Picture'

class Reel(object):
	def __init__(self, assets=list()):
		self.UUID=asdcp_genuuid()
		self.assets = assets
	
	def yield_cpl_SMPTE(self, head_element):
		reel = etree.SubElement(head_element, 'Reel')
		etree.SubElement(reel, 'Id').text = 'urn:uuid:' + self.UUID
		assetlist = etree.SubElement(reel, 'AssetList')
		for asset in self.assets:
			asset.yield_cpl_SMPTE(reel)

	def yield_cpl_Interop(self, head_element):
		reel = etree.SubElement(head_element, 'Reel')
		etree.SubElement(reel, 'Id').text = 'urn:uuid:' + self.UUID
		assetlist = etree.SubElement(reel, 'AssetList')	
		for asset in self.assets:
			asset.yield_cpl_Interop(reel)


class Assetmap(object):
	def __init__(self, assets=list()):
		self.assets = assets
		self.UUID = asdcp_genuuid()
		self.volumecount = 1
	
	def xml_SMPTE(self):
		assetmap = etree.Element('{http://www.smpte-ra.org/schemas/429-9/2007/AM}AssetMap', 
		                         nsmap={None: 'http://www.smpte-ra.org/schemas/429-9/2007/AM'})
		assetlist = etree.SubElement(assetmap, 'AssetList')
		for asset in assets:
			asset.yield_am_SMPTE(assetlist)

		_xml = etree.tostring(assetmap, pretty_print=True, xml_declaration=True, standalone=True, encoding='UTF-8')
		return _xml
	
	def xml_Interop(self):
		assetmap = etree.Element('{http://www.digicine.com/PROTO-ASDCP-AM-20040311#}AssetMap', 
		                         nsmap={None: 'http://www.digicine.com/PROTO-ASDCP-AM-20040311#', 
					 'xsi': 'http://www.w3.org/2001/XMLSchema-instance'})
		assetlist = etree.SubElement(assetmap, 'AssetList')
		for asset in assets:
			asset.yield_am_Interop(assetlist)

		_xml = etree.tostring(assetmap, pretty_print=True, xml_declaration=True, standalone=True, encoding='UTF-8')
		return _xml

class VolumeIndex(object):
	def xml_SMPTE(self):
		_volumeindex = etree.Element('{http://www.smpte-ra.org/schemas/429-9/2007/AM}VolumeIndex', 
		                             nsmap={None: 'http://www.smpte-ra.org/schemas/429-9/2007/AM'})
		etree.SubElement(_volumeindex, 'Index').text = '1'

		_xml = etree.tostring(_volumeindex, pretty_print=True, xml_declaration=True, standalone=True, encoding='UTF-8')
		return _xml

