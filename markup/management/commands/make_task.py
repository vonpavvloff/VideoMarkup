from sys import stdout,stderr
from django.core.management.base import BaseCommand, CommandError
from markup.models import Video,RecommenderModel,Recommendation,Task,TaskItem
from django.core.exceptions import ObjectDoesNotExist
from markup.util import mapreduce,add_video,add_recommendation
from optparse import make_option
from httplib import HTTPConnection
from urlparse import urlparse
from datetime import datetime,timedelta
import subprocess
from urllib import unquote
from random import shuffle
import logging
import re
import markup.util
logger = logging.getLogger(__name__)


def dates(bdate,edate):
	start = datetime.strptime(bdate,"%Y%m%d")
	end = datetime.strptime(edate,"%Y%m%d")
	delta = timedelta(days=1)
	while True:
		yield start.strftime("%Y%m%d")
		start += delta
		if start > end:
			break

class Command(BaseCommand):
	option_list = BaseCommand.option_list + (
		make_option('-t', "--title", dest="title", type="str", help="Task title"),
		make_option('-b', "--begin-date", dest="bdate", type="str", help="Begin date"),
		make_option('-e', "--end-date", dest="edate", type="str", help="End date"),
		make_option('-c', "--count", dest="count", type="int", help="Number of videos in task"),
	)
	def handle(self, *args, **options):
		logger.info('Creating task and recommender models')
		task,created = Task.objects.get_or_create(title=options["title"])

		if not created:
			logger.warn('Removing old task with the same title')
			task.delete()
			task,created = Task.objects.get_or_create(title=options["title"])

		inputs = map(lambda x: 'user_sessions/' + x, dates(options['bdate'],options['edate']))
		probability = 0.01 / len(inputs)

		# Select the keys
		logger.info('Selecting the previous urls')
		mapreduce(map="grep related_url= | grep type=RELATED_VIDEO_REQUEST | grep service=video.yandex | grep dom-region=ru | awk 'rand() < " + str(probability) + "' | cut -f 8 | awk '{print $0 \"\\t\"}'",
			src=inputs,
			dst="clickadd/video/markup/prevurl_sample." + options['title'])
		mapreduce(read="clickadd/video/markup/prevurl_sample." + options['title'],stdout="pool_sample.tsv")
		mapreduce(read="clickadd/video/markup/prevurl_sample." + options['title'],stdout="pool_sample.tsv")
		# Parse prev urls
		logger.info('Parsing previous urls')
		all_keys = []
		with open("pool_sample.tsv") as inp:
			for l in inp:
				all_keys.append(unquote(re.search("(\?|&)related_url=(http[^&]+)&",l.strip()).group(2)))
		# Sample the required ammount
		shuffle(all_keys)
		
		# Create videos and populate task
		logger.info('Saving previous urls for the task')
		with open("url_keys.tsv","w+") as out:
			count = 0
			for k in all_keys:
				try:
					video = add_video(k)
					TaskItem.objects.get_or_create(task=task,video=video)
					out.write(k)
					out.write("\n")
					count += 1
					if count >= options["count"]:
						break
				except ObjectDoesNotExist:
					continue
