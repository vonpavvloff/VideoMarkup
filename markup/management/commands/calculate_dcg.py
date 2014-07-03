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
logger = logging.getLogger(__name__)

def get_dcg_weight(recommendation):
	return Recommendation.objects.get(task=recommendation.task,current=recommendation.current,recommended=recommendation.recommended,model__title="DCG").weight

def calc_dcg(weights,positions):
	if positions <= 0:
		positions = len(weights)
	result = 0.0
	for i in range(min(len(weights),positions)):
		result += (2.0 ** weights[i])/log(i+2,2)
	return result

def get_intervals(values,alpha):
	n = len(values)
	mean = sum(values) / n
	stddev = sqrt(sum(map(lambda x: (x - mean)**2,values))/n)
	delta = t.ppf(1.0 - (1.0 - alpha)/2,n-1) * stddev / sqrt(n)
	lower = mean - delta
	upper = mean + delta
	return lower,upper

class Command(BaseCommand):
	option_list = BaseCommand.option_list + (
		make_option('-t', "--task", dest="task", type="str", help="Task"),
		make_option('-n', "--ndcg", dest="ndcg", action="store_true", default=False, help="Calculate NDCG"),
		make_option('-a', "--alpha", dest="alpha", type="float", default=0.99, help="Probability interval"),
		make_option('-s', "--substract", dest="substract", action="store_true", default=False, help="Calculate delta from the ideal DCG"),
		make_option('-p', "--positions", dest="positions", type="int", default=0, help="Number of positions to account for during dcg calculation."),
		make_option('--simulate-production', dest="simulate", action="store_true", default=False, help="Simulate production process, where production model is used in absence of experimental model, and default model is usd to increase recall."),
	)
	def handle(self, *args, **options):
		task = Task.objects.get(title=options["task"])
		dcg,created = RecommenderModel.objects.get_or_create(title="DCG")
		stdout.write("\t".join(["title","lower","mean","upper"]) + "\n")
		for rm in RecommenderModel.objects.all():
			dcg_values = []
			for cv in current_videos(task):
				results = []
				if options["simulate"]:
					# Take the current model
					for rec in Recommendation.objects.filter(current=cv,model=rm,task=task,recommended__is404=False).order_by("-weight")[:3]:
						results.append(get_dcg_weight(rec))
					if len(results) == 0:
						# Use production model, if there is no current model
						for rec in Recommendation.objects.filter(current=cv,model__title="production",task=task,recommended__is404=False).order_by("-weight")[:3]:
							results.append(get_dcg_weight(rec))
					# Append default model
					for rec in Recommendation.objects.filter(current=cv,model__title="default",task=task,recommended__is404=False).order_by("-weight")[:options["positions"]]:
						if len(results) >= options["positions"]:
							break
						results.append(get_dcg_weight(rec))
				else:
					# Just get items from the current model
					for rec in Recommendation.objects.filter(current=cv,model=rm,task=task,recommended__is404=False).order_by("-weight")[:options["positions"]]:
						results.append(get_dcg_weight(rec))

				# Calculate dcg for the current video
				dcg_value = calc_dcg(results,options["positions"])

				# Select weights of unknown videos
				if options["ndcg"] or options["substract"]:
					ideal_results = []
					for rec in Recommendation.objects.filter(current=cv,model=dcg,task=task,recommended__is404=False).order_by("-weight"):
						ideal_results.append(rec.weight)
					if options["ndcg"]:
						dcg_value /= calc_dcg(ideal_results,options["positions"])
					else:
						dcg_value = calc_dcg(ideal_results,options["positions"]) - dcg_value

				dcg_values.append(dcg_value)
			# Calculate mean and stddev
			mean = sum(dcg_values) / len(dcg_values)
			lower,upper = get_intervals(dcg_values,options["alpha"])
			stdout.write("\t".join([rm.title,str(lower),str(mean),str(upper)]) + "\n")


