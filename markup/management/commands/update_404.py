from django.core.management.base import BaseCommand, CommandError
from markup.models import Video,RecommenderModel,Recommendation,Task,TaskItem
from django.core.exceptions import ObjectDoesNotExist
from markup.util import get_video_title_from_search
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
		for v in Video.objects.all():
			try:
				t = get_video_title_from_search(v.url)
				logger.info("Found " + v.url + " in search")
				v.is404 = False
				v.save()
			except Exception, e:
				logger.exception("Failed to find video " + v.url + " in search, marking it as 404")
				v.is404 = True
				v.save()
