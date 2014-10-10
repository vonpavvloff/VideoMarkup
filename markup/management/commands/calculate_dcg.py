from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from markup.models import Video,RecommenderModel,Recommendation,Label,Task
from markup.util import current_videos
from optparse import make_option
from sys import stdout
from math import log,sqrt
import subprocess
from scipy.stats import t
import logging
from random import sample,choice
logger = logging.getLogger(__name__)

def get_intervals(values,alpha):
	n = len(values)
	mean = sum(values) / n
	stddev = sqrt(sum(map(lambda x: (x - mean)**2,values))/n)
	delta = t.ppf(1.0 - (1.0 - alpha)/2,n-1) * stddev / sqrt(n)
	lower = mean - delta
	upper = mean + delta
	return lower,upper

def get_intervals_bootsrap(values,alpha):
	bsv = []
	for i in range(10000):
		vs = []
		for j in range(len(values)):
			vs.append(choice(values))
		mean = sum(vs) / len(vs)
		bsv.append(mean)
	index = int(10000 * (1.0 - alpha)) / 2
	bsv.sort()
	return bsv[index],bsv[-index]

def get_ideal_dcg(n):
	idcg = 0.0
	for i in range(n):
		idcg += 1.0 / (1.0 + i)
	return idcg

def calculate_dcg(tsk,rm,**options):
	dcg_values = []
	dcg,created = RecommenderModel.objects.get_or_create(title="DCG")
	for cv in current_videos(tsk):
		if options['youtube'] and not 'youtube' in cv.url:
			continue
		results = []
		model_to_use = rm
		addedvals = 0
		gainssum = 0.0
		discount = 1
		for rec in Recommendation.objects.filter(current=cv,model=dcg,task=tsk,recommended__is404=False).order_by("-weight"):
			try:
				curmodelrec = Recommendation.objects.filter(current=rec.current,recommended=rec.recommended,model=model_to_use).order_by('-weight')[0]
				if Recommendation.objects.filter(current=rec.current,model=model_to_use,weight__gt=curmodelrec.weight).count() < options['positions']:
					gainssum += 1.0 / discount
					addedvals += 1
			except IndexError:
				pass
			if addedvals >= options["positions"]:
				break
			discount += 1

		if options["ndcg"]:
			dcg_value = gainssum / get_ideal_dcg(options["positions"])
		else:
			dcg_value = gainssum

		dcg_values.append(dcg_value)
	# Calculate mean and stddev
	mean = sum(dcg_values) / len(dcg_values)
	if options["bootstrap"]:
		lower,upper = get_intervals_bootsrap(dcg_values,options["alpha"])
	else:
		lower,upper = get_intervals(dcg_values,options["alpha"])
	return (lower,mean,upper)


class Command(BaseCommand):
	option_list = BaseCommand.option_list + (
		make_option('-t', "--task", dest="task", type="str", help="Task"),
		make_option('-n', "--ndcg", dest="ndcg", action="store_true", default=False, help="Calculate NDCG"),
		make_option('-a', "--alpha", dest="alpha", type="float", default=0.99, help="Probability interval"),
		make_option('-p', "--positions", dest="positions", type="int", default=0, help="Number of positions to account for during dcg calculation."),
		make_option('--youtube', dest="youtube", action="store_true", default=False, help="Compare only youtube recommendations"),
		make_option('--simulate-production', dest="simulate", action="store_true", default=False, help="Simulate production process, where production model is used in absence of experimental model, and default model is usd to increase recall."),
		make_option('--bootstrap', dest="bootstrap", action="store_true", default=False, help="Use bootstrapping to calculate confidence intervals")
	)
	def handle(self, *args, **options):
		task = Task.objects.get(title=options["task"])
		stdout.write("\t".join(["title","lower","mean","upper"]) + "\n")
		for rm in RecommenderModel.objects.all():
			if not Recommendation.objects.filter(task=task,model=rm).exists():
				continue
			if rm.title == 'DCG':
				continue
			lower,mean,upper = calculate_dcg(task,rm,**options)
			stdout.write("\t".join([rm.title,str(lower),str(mean),str(upper)]) + "\n")
