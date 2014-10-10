from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from markup.models import Video,RecommenderModel,Recommendation,Label,Task
from markup.util import current_videos,add_video
from optparse import make_option
import urllib2
import xml.dom.minidom
import logging
from random import random
from time import sleep
logger = logging.getLogger(__name__)

class Command(BaseCommand):
	option_list = BaseCommand.option_list + (
		make_option('-t', "--task", dest="task", type="str", help="Task"),
		make_option('-n', "--number", dest="number", type="int", default=5, help="Number of recommendations to store"),
	)
	def handle(self, *args, **options):
		task = Task.objects.get(title=options['task'])
		model,created = RecommenderModel.objects.get_or_create(title='youtube')
		for current in current_videos(task):
			if Recommendation.objects.filter(current = current, model = model, task = task).exists():
				logger.info('Skipping url: ' + current.url)
				continue
			if current.url.startswith('http://www.youtube.com/watch?v='):
				yid = current.url.partition('=')[2]
				req = urllib2.Request('http://gdata.youtube.com/feeds/api/videos/' + yid + '/related')
				req.add_header('User-agent', 'Yandex')
				logger.info('Requesting recommendations from Youtube for video: ' + current.url)
				try:
					r = urllib2.urlopen(req)
					data = r.read()
					logger.info('Parsing xml')
					dom = xml.dom.minidom.parseString(data)
					count = 0.0
					for entry in dom.getElementsByTagName('entry'):
						count += 1
						title = entry.getElementsByTagName('title')[0].firstChild.nodeValue
						for link in entry.getElementsByTagName('link'):
							if link.getAttribute('rel') == 'alternate':
								url = link.getAttribute('href')
								url = url.partition('&')[0]
								break
						logger.info('Found recommendation: ' + url)
						video = add_video(url,title)
						Recommendation.objects.get_or_create(current = current, recommended = video, model = model, task = task, weight = 1.0 / count)
						if count >= options["number"]:
							break
				except urllib2.HTTPError:
					logger.error('Failed to download data for url: ' + current.url)
				sleep(random() * 60)
