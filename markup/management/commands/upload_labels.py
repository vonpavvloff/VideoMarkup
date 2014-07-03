from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from markup.models import Video,RecommenderModel,Recommendation,Label,Task
from django.contrib.auth.models import User
from optparse import make_option
from sys import stdout,stderr

class Command(BaseCommand):
	option_list = BaseCommand.option_list + (
		make_option('-l', "--labels-file", dest="labels", type="str", help="File with labels"),
		make_option('-n', "--numeric", dest="numeric", action="store_true", default=False, help="Use numeric values instead of string labels."),
	)
	def handle(self, *args, **options):
		with open(options["labels"]) as inp:
			for l in inp:
				try:
					username,task,current,first,second,value = l.split()
					if options["numeric"]:
						value = int(value)
						if value > 0:
							value = "F"
						elif value < 0:
							value = "S"
						else:
							value = "U"
					task = Task.objects.get(title=markup)
					user = User.objects.get(username=username)
					curvideo = Video.objects.get(url=current)
					firstvideo = Video.objects.get(url=first)
					secondvideo = Video.objects.get(url=second)
				except ObjectDoesNotExist:
					stderr.write("Failed to add label:\n")
					stderr.write(l)
				label,created = Label.objects.get_or_create(current=curvideo,first=firstvideo,second=secondvideo,user=user, task = task)
				label.value = value
				label.save()

