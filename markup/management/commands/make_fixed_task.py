from sys import stdout,stderr
from django.core.management.base import BaseCommand, CommandError
from markup.models import Video,RecommenderModel,Recommendation,Task,TaskItem,FixedTask, FixedTaskItem,Label
from django.core.exceptions import ObjectDoesNotExist
from markup.util import mapreduce,add_video,add_recommendation,generate_random_triple
from django.contrib.auth.models import User
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
from itertools import cycle,izip


class Command(BaseCommand):
	option_list = BaseCommand.option_list + (
		make_option("--title", dest="title", type="str", help="Fixed task title"),
		make_option("--task", dest="task", type="str", help="Task title"),
		make_option('-c', "--count", dest="count", type="int", help="Total count of non-overlapping labels in task"),
		make_option("--user", dest="user", type="str", action="append", help="Users"),
		make_option("--overlap", dest="overlap", type="int", help="Overlap for users")
	)
	def handle(self, *args, **options):
		fixedtask,created = FixedTask.objects.get_or_create(title=options["title"])
		if not created:
			stderr.write("This task already exists, exiting.\n")
			logger.error("This task already exists, exiting.")
			return
		task = Task.objects.get(title=options["task"])

		usergroups = []
		for i in range(options["overlap"]):
			usergroups.append([])
		shuffle(options["user"])
		c = 0
		for u in options["user"]:
			usergroups[c].append(u)
			c = (c + 1) % options["overlap"]

		for t in izip(range(options["count"]),*map(cycle,usergroups)):
			current,first,second = generate_random_triple(task=task)
			users = t[1:]
			for u in users:
				try:
					user = User.objects.get(username=u)
				except ObjectDoesNotExist:
					user = User.objects.create_user(u,u + "@yandex-team.ru","pass")
					user.save()
				l,created = Label.objects.get_or_create(current=current,first=first,second=second,task=task,user=user)
				FixedTaskItem.objects.get_or_create(task=fixedtask,label=l)
