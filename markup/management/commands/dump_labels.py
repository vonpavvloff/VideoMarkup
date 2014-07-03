from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from markup.models import Video,RecommenderModel,Recommendation,Label
from optparse import make_option
from sys import stdout

class Command(BaseCommand):
	def handle(self, *args, **options):		
		for l in Label.objects.filter(value__in = Label.ISLABELED_VALUES):
			stdout.write(l.user.username)
			stdout.write("\t")
			stdout.write(l.task.title)
			stdout.write("\t")
			stdout.write(l.current.url)
			stdout.write("\t")
			stdout.write(l.first.url)
			stdout.write("\t")
			stdout.write(l.second.url)
			stdout.write("\t")
			stdout.write(str(l.value))
			stdout.write("\n")
