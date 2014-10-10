from sys import stdout,stderr
from django.core.management.base import BaseCommand, CommandError
from markup.models import Video,RecommenderModel,Recommendation,Task,TaskItem,FixedTask, FixedTaskItem,Label,DynamicTask,DynamicAssignment
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from optparse import make_option
import logging
logger = logging.getLogger(__name__)
from itertools import cycle,izip

class Command(BaseCommand):
	option_list = BaseCommand.option_list + (
		make_option("--title", dest="title", type="str", help="Dynamic task title"),
		make_option("--task", dest="task", type="str", help="Task title"),
		make_option('-c', "--count", dest="count", type="int", help="Total number of labels for each evaluator"),
		make_option("--user", dest="user", type="str", action="append", help="Users"),
	)
	def handle(self, *args, **options):
		task = Task.objects.get(title=options["task"])
		dyntask,created = DynamicTask.objects.get_or_create(title=options["title"],task=task)
		if not created:
			stderr.write("This task already exists, exiting.\n")
			logger.error("This task already exists, exiting.")
			return
		for u in options['user']:
			try:
				user = User.objects.get(username=u)
			except ObjectDoesNotExist:
				user = User.objects.create_user(u,u + "@yandex-team.ru","pass")
				user.save()
			DynamicAssignment.objects.create(user=user,size=options['count'],dynamictask=dyntask)
