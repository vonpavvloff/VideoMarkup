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

"""
  0. grep user_sessions to select the set of prevurls
  1. click_pool to select all video views from the test id
    * query,prevurl,url
  2. select random N videos (what do i do with repetitions? - remove them for now)
    * sample_pool by prevurl | if url:url in query then it is production recommendation else it is default recommendation | reduce by prevurl and select 3 production and 4 default, assign weights
  3. Upload to system
"""

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
		make_option('-d', "--default-count", dest="dcount", type="int", help="Number of videos in default recommendations"),
		make_option('-i', "--test-id", dest="testid", type="int", help="Test id, from whick to collect recommendations"),
		make_option('--nomapreduce', dest="nomapreduce", action="store_true", default=False, help="Do not run mapreduce commands."),
	)
	def handle(self, *args, **options):
		if options["nomapreduce"]:
			markup.util.skipMapReduceCommands = True
		logger.info('Creating task and recommender models')
		task,created = Task.objects.get_or_create(title=options["title"])
		if not created:
			stderr.write("This task already exists, exiting.\n")
			logger.error("This task already exists, exiting.")
			return
		defmodel,created = RecommenderModel.objects.get_or_create(title="default")
		prodmodel,created = RecommenderModel.objects.get_or_create(title="production")

		inputs = map(lambda x: 'user_sessions/' + x, dates(options['bdate'],options['edate']))
		probability = 0.01 / len(inputs)

		# Select the keys
		logger.info('Selecting the previous urls')
		mapreduce(map="grep related_url= | grep type=RELATED_VIDEO_REQUEST | grep service=video.yandex | grep dom-region=ru | awk 'rand() < " + str(probability) + "' | cut -f 8 | awk '{print $0 \"\\t\"}'",
			src=inputs,
			dst="rearrange/click_pool/video/markup/prevurl_sample." + options['title'])
		mapreduce(read="rearrange/click_pool/video/markup/prevurl_sample." + options['title'],stdout="pool_sample.tsv")

		if not options["nomapreduce"]:
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
		else:
			logger.info('Adding already generated previous urls')
			with open("url_keys.tsv") as inp:
				for l in inp:
					video = add_video(l.strip())
					TaskItem.objects.get_or_create(task=task,video=video)
		
		# Run click pool to collect production results
		logger.info('Running click_pool to collect urls to markup')
		if not options["nomapreduce"]:
			subprocess.call(['./click_pool',
				'-s','cedar00.search.yandex.net:8013',
				'-b', options['bdate'],
				'-e', options['edate'],
				'-f','query,prevurl,url',
				'-F','reqrelev.country == ru && test.' + str(options['testid']),
				'-d', 'rearrange/click_pool/video/markup/correct_sampling.' + options['title'],
				'-p',str(options["dcount"] + 3),
				'-t','video_related'],
				env={'MR_NET_TABLE':'ipv6', 'MR_USER':'clickadd'})
		# Filter pool to leave only required keys
		logger.info('Filtering pool')
		mapreduce(map="python transform_pool.py -f qid,nothing,target,url1,weight,position,query,prevurl,url -t prevurl,position,url,query | python filter_keys.py -k url_keys.tsv",
			subkey="",
			src='rearrange/click_pool/video/markup/correct_sampling.' + options['title'],
			dst='rearrange/click_pool/video/markup/urls_to_markup.' + options['title'],
			file=["transform_pool.py","filter_keys.py","sample_pool.py","url_keys.tsv"])

		mapreduce(reduce='uniq',
			subkey="",
			src='rearrange/click_pool/video/markup/urls_to_markup.' + options['title'],
			dst='rearrange/click_pool/video/markup/urls_to_markup_uniq.' + options['title'])

		mapreduce(read='rearrange/click_pool/video/markup/urls_to_markup_uniq.' + options['title'],
			subkey="",
			stdout="urls_to_markup_uniq.tsv")

		def process(prevurl,position,url,query):
			shorturl = url
			if url.startswith("http://"):
				shorturl = url[7:]
			if shorturl in query:
				add_recommendation(prevurl,url,1.0 / (position + 1.0),prodmodel,task)
			else:
				add_recommendation(prevurl,url,1.0 / (position + 1.0),defmodel,task)

		logger.info('Adding recommendations')
		with open('urls_to_markup_uniq.tsv') as inp:
			for l in inp:
				prevurl,position,url,query = l[:-1].split('\t')
				position = int(position)
				try:
					logger.info('Found recommendation for prevurl: ' + prevurl + ' position: ' + str(position) + " " + url)
					process(prevurl,position,url,query)
				except ObjectDoesNotExist:
					logger.info('Failed to add recommendation')

