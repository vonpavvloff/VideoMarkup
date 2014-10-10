from django.core.management.base import BaseCommand, CommandError
from markup.models import Video,RecommenderModel,Recommendation,Task,TaskItem
from django.core.exceptions import ObjectDoesNotExist
from optparse import make_option
from httplib import HTTPConnection
from urlparse import urlparse
from markup.util import get_embed,mapreduce,current_videos,add_recommendation,add_video
import logging
logger = logging.getLogger(__name__)
import json
from itertools import izip

class Command(BaseCommand):
	option_list = BaseCommand.option_list + (
		make_option("--model", dest="model", type="str", help="Source of the model"),
		make_option("--task", dest="task", type="str", help="Task identifier"),
		make_option('--title', dest="title", type="str", help="Model title"),
		make_option('--json', dest="json", action="store_true", default=False, help="The input is in json format."),
		make_option('-n', "--number", dest="number", type="int", default=5, help="Number of recommendations to store"),
	)
	def handle(self, *args, **options):
		model,created = RecommenderModel.objects.get_or_create(title=options["title"])
		task,created = Task.objects.get_or_create(title=options["task"])

		def add_recommendations(current_url,others,number):
			logger.info("Adding recommendations for url: " + current_url)
			if len(others) == 0:
				logger.info("Found no recommendations")
				return
			count = 0
			others.sort(reverse=True,key=lambda x:x[1])
			for video_url,weight in others:
				count += 1
				if count > number:
					break
				# Create recommendation for the current model
				try:
					add_recommendation(current_url,video_url,weight,model,task)
				except ObjectDoesNotExist:
					logger.info("Failed to add recommendation")
		
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
				dst="clickadd/video/markup/" + model_file)
			mapreduce(
				sort="clickadd/video/markup/" + model_file)
			mapreduce(
				read="clickadd/video/markup/" + model_file,
				server=server,
				stdout=model_file)
		else:
			model_file = options["model"]


		def get_items(input):
			for l in input:
				if options["json"]:
					cur_url, tab, data = l.partition('\t')
					urls = json.loads(data)
					for u,w in izip(urls,range(len(urls),0,-1)):
						yield cur_url,u,float(w)
				else:
					cur_url,other_url,weight = l[:-1].split("\t")[0:3]
					yield cur_url,other_url,float(weight)
			pass

		with open(model_file) as inp:
			current_url = ""
			others = []
			for cur_url,other_url,weight in get_items(inp):
				if cur_url == other_url:
					continue
				weight = float(weight)
				if cur_url != current_url:
					add_recommendations(current_url,others,options['number'])
					current_url = cur_url
					others = []
				others.append((other_url,weight))
			add_recommendations(current_url,others,options['number'])	
