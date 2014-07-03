from django.core.management.base import BaseCommand, CommandError
from markup.models import Video,RecommenderModel,Recommendation,Task,TaskItem
from django.core.exceptions import ObjectDoesNotExist
from markup.util import mapreduce,add_video,add_recommendation,get_video_title_from_search
from optparse import make_option
from httplib import HTTPConnection
from urlparse import urlparse
from datetime import datetime,timedelta
import subprocess
from urllib import unquote
from random import sample
import logging
import re
logger = logging.getLogger(__name__)

"""
  1. Extract 
"""


class Command(BaseCommand):
	def handle(self, *args, **options):
		
		with open("video_urls.txt","w+") as out:
			for v in Video.objects.all():
				out.write(v.url)
				out.write("\n")

		# Select the keys
		logger.info('Extracting titles')
		mapreduce(map="python extract_video_titles.py --media | python filter_keys.py -k video_urls.txt",
			src="video/waldata/media/prevdata",
			dst="rearrange/click_pool/video/markup/titles.media",
			file=["video_urls.txt","filter_keys.py","transform_pool.py","markup/extract_video_titles.py"])
		mapreduce(map="python extract_video_titles.py --xml | python filter_keys.py -k video_urls.txt",
			src="video/waldata/xml/prevdata",
			dst="rearrange/click_pool/video/markup/titles.xml",
			file=["video_urls.txt","filter_keys.py","transform_pool.py","markup/extract_video_titles.py"])
		mapreduce(read='rearrange/click_pool/video/markup/titles.media',
			stdout="titles.media")
		mapreduce(read='rearrange/click_pool/video/markup/titles.xml',
			stdout="titles.xml")

		logger.info('Saving titles')
		with open('titles.media') as inp:
			for l in inp:
				url,title = l[:-1].split('\t')
				try:
					v = Video.objects.get(url=url)
					v.title = title
					v.save()
				except ObjectDoesNotExist:
					continue

		with open('titles.xml') as inp:
			for l in inp:
				url,title = l[:-1].split('\t')
				try:
					v = Video.objects.get(url=url)
					v.title = title
					v.save()
				except ObjectDoesNotExist:
					continue

		for v in Video.objects.filter(title=""):
			try:
				title = get_video_title_from_search(v.url)
				v.title = title
				v.save()
				logger.info("Loaded title for video: " + v.url)
			except Exception, e:
				logger.exception("Failed to get title for video: " + v.url)
				continue
