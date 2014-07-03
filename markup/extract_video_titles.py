from sys import argv,stdin,stdout,path
from optparse import OptionParser
import json
from datetime import datetime
from urlparse import urlparse
import codecs 

if __name__ == "__main__":
	parser = OptionParser("usage: %prog [options]")
	parser.add_option('-m', "--media", dest="media", action="store_true", default=False, help="Parse media")
	parser.add_option('-x', "--xml", dest="xml", action="store_true", default=False, help="Parse xml")
	(options, args) = parser.parse_args()

	for l in stdin:
		key,sep,val = l[:-1].partition('\t')
		try:
			mapping = json.loads(val)
		except UnicodeDecodeError:
			continue
		except ValueError:
			continue
		if options.xml:
			try:
				url = "http://" + mapping["CanonicalUrl"]["Value"]
			except KeyError:
				url = "http://" + key
		else:
			url = "http://" + key
		try:
			if options.media:
				title = mapping["PageAttrs"]["Title"] 
			elif options.xml:
				title = mapping["Items"][0]["Texts"][0]["Value"] 
		except KeyError:
			continue
		
		stdout.write(str(url))
		stdout.write('\t')
		stdout.write(codecs.encode(title, 'UTF-8', 'strict'))
		stdout.write('\n')
