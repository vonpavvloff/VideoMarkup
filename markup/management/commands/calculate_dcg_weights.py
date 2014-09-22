from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from markup.models import Video,RecommenderModel,Recommendation,Label,Task
from markup.util import current_videos
from optparse import make_option
from sys import stdout
from math import exp
import subprocess
import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
	option_list = BaseCommand.option_list + (
		make_option('-t', "--task", dest="task", type="str", help="Task"),
		make_option("--iterations", dest="iterations", type="int", default=100, help="Iterations"),
	)
	def handle(self, *args, **options):
		task = Task.objects.get(title=options["task"])
		# Create the DCG RecommenderModel
		dcg,created = RecommenderModel.objects.get_or_create(title="DCG")
		# Delete all recommendations for DCG
		Recommendation.objects.filter(task=task,model=dcg).delete()
		for cv in current_videos(task):
			# Get all samples
			videos_set = set()
			for r in cv.recommendations.filter(recommended__is404 = False, task = task).distinct():
				videos_set.add(r.recommended)
			videos = []
			videos.extend(videos_set)
			# Prepare files for matrixnet
			## Generate features.txt
			with open("features.txt","w+") as out:
				for i in range(len(videos)):
					features = [0]*len(videos)
					features[i] = 1
					line = [i,0,videos[i].url,0]
					line.extend(features)
					out.write("\t".join(map(str,line)) + "\n")
			## Generate features.txt.pairs
			with open("features.txt.pairs","w+") as out:
				for l in Label.objects.filter(task=task,current=cv, first__is404=False, second__is404=False, value__in=["F","S"]):
					first = videos.index(l.first)
					second = videos.index(l.second)
					if l.value == "F":
						out.write(str(first) + "\t" + str(second) + "\n")
					else:
						out.write(str(second) + "\t" + str(first) + "\n")
			# Launch matrixnet
			with open("matrixnet.log","w+") as out:
				subprocess.call(["./matrixnet","-P","-i",str(options["iterations"])],stdout=out)
			# Get the results from matrixnet
			# Save the DCG recommendations
			with open("features.txt.matrixnet") as inp:
				for v,line in zip(videos,inp):
					weight = float(line.split()[-1])
					weight = 1.0 / (1.0 + exp(-weight))
					rec,created = Recommendation.objects.get_or_create(current = cv, task=task, recommended = v, model = dcg)
					if not created:
						logger.warn('Found duplicate recommendation: ' + cv.url + ' ' + v.url)
					rec.weight = weight
					rec.save()


