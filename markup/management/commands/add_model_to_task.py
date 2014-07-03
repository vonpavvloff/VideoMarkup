from django.core.management.base import BaseCommand, CommandError
from markup.models import Video,RecommenderModel,Recommendation,Task,TaskItem
from django.core.exceptions import ObjectDoesNotExist
from optparse import make_option
from httplib import HTTPConnection
from urlparse import urlparse
from markup.util import get_embed,mapreduce,current_videos,add_recommendation,add_video
import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
	option_list = BaseCommand.option_list + (
		make_option("--model", dest="model", type="str", help="Source of the model"),
		make_option("--task", dest="task", type="str", help="Task identifier"),
		make_option('--title', dest="title", type="str", help="Model title"),
		make_option('-n', "--number", dest="number", type="int", default=4, help="Number of recommendations to store")
	)
	def handle(self, *args, **options):
		model,created = RecommenderModel.objects.get_or_create(title=options["title"])
		task,created = Task.objects.get_or_create(title=options["task"])

		def add_recommendations(current_url,others):
			logger.info("Adding recommendations for url: " + current_url)
			if len(others) == 0:
				logger.info("Found no recommendations")
				return

			try:
				current = TaskItem.objects.get(video__url=current_url,task=task)
			except ObjectDoesNotExist:
				logger.warn("Found a video: " + current_url + " that is not in task " + task.title)
				return

			count = 0
			for video_url,weight in others:
				count += 1
				if count > options["number"]:
					break
				try:
					video = add_video(video_url)
				except ObjectDoesNotExist:
					logger.info("Could not add video: " + video_url)
					continue
				# Create recommendation for the current model
				add_recommendation(current_url,video_url,weight,model,task)
		
		if options["model"].startswith("mapreduce://"):
			server,sep,table = options["model"][12:].partition("/")
			model_file = "recommendations." + options["title"] + "." + options["task"]
			with open("url_keys.tsv","w+") as out:
				for v in current_videos(task):
					out.write(v.url)
					out.write("\n")
			mapreduce(
				map="python filter_keys.py -k url_keys.tsv",
				src=table,
				server=server,
				file=["url_keys.tsv","filter_keys.py"],
				dst="rearrange/click_pool/video/markup/" + model_file)
			
			mapreduce(
				read="rearrange/click_pool/video/markup/" + model_file,
				server=server,
				stdout=model_file)
		else:
			model_file = options["model"]

		with open(model_file) as inp:
			current_url = ""
			others = []
			for l in inp:
				cur_url,other_url,weight = l[:-1].split("\t")[0:3]
				if cur_url == other_url:
					continue
				weight = float(weight)
				if cur_url != current_url:
					add_recommendations(current_url,others)
					current_url = cur_url
					others = []
				others.append((other_url,weight))
			add_recommendations(current_url,others)	
