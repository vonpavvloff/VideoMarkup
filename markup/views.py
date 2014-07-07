from sys import stdout
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse,Http404,HttpResponseRedirect
from django.shortcuts import render,get_object_or_404
from django.core.urlresolvers import reverse
from markup.models import Video,Label,RecommenderModel,Recommendation,Task,FixedTask,FixedTaskItem
from markup.util import current_videos_with_recommendations,generate_random_triple
from django.core.exceptions import PermissionDenied
from random import choice, uniform, shuffle, sample
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from StringIO import StringIO
import logging
logger = logging.getLogger(__name__)
import traceback

def choice_weighted(seq,weighter):
	vals = []
	sum = 0.0
	for s in seq:
		weight = weighter(s)
		assert weight > 0
		sum += weight
		vals.append((s,weight))
	rnd = uniform(0,sum)
	for s,w in vals:
		rnd -= w
		if rnd <= 0:
			return s
	raise IndexError()

def sample_weighted(seq,weighter,number):
	vals = []
	sum = 0.0
	for s in seq:
		weight = weighter(s)
		assert weight > 0
		sum += weight
		vals.append((s,weight))

	result = []
	for i in range(number):
		val = choice_weighted(vals, lambda x: x[1])
		result.append(val[0])
		vals.remove(val)
	
	return result

@login_required(login_url='/markup/dologin/')
def task_selection(request):
	return render(request,'markup/tasks.html',{'tasks':Task.objects.all(),'fixedtasks':FixedTask.objects.all()})

# Create your views here.
@login_required(login_url='/markup/dologin/')
def markup(request):
	user = request.user
	try:
		task = Task.objects.get(pk = request.GET.get("task") )
	except KeyError:
		return HttpResponseRedirect('/markup/tasks/')
	except ObjectDoesNotExist:
		return HttpResponseRedirect('/markup/tasks/')

	totallabels = Label.objects.filter(task=task,user=user,value__in=["F","S","B"]).count()

	current,first,second = generate_random_triple(task=task,user=user)
	pair = [first,second]
	shuffle(pair)
	return render(request,'markup/markup.html',{'current':current,
		'first':pair[0],
		'second':pair[1],
		'path':request.path,
		'task':task,
		'message': "You have labeled " + str(totallabels) + " pairs."})
	logger.warn("Failed to get markup objects.")
	raise ObjectDoesNotExist

@login_required(login_url='/markup/dologin/')
def label(request):
	try:
		task = int(request.POST['task'])
		current = int(request.POST['current'])
		first = int(request.POST['first'])
		second = int(request.POST['second'])
		value = request.POST['value']

		if first > second:
			# swap
			tmp = first
			first = second
			second = tmp
			# Also swap label
			if value == "F":
				value = "S"
			elif value == "S":
				value = "F"

			elif value == "f":
				value = "s"
			elif value == "s":
				value = "f"

		current = Video.objects.get(pk=current)
		first = Video.objects.get(pk=first)
		second = Video.objects.get(pk=second)
		task = Task.objects.get(pk=task)
		label,created = Label.objects.get_or_create(current = current, first = first, second = second, user = request.user, task = task)

		label.value = value
		label.save()

		if value == 'c':
			current.is404 = True
			current.save()
		elif value == 'f':
			first.is404 = True
			first.save()
		elif value == 's':
			second.is404 = True
			second.save()


		logger.info("LABEL\t" + str(label))

		return HttpResponse('')
	except Exception, e:
		logger.exception("An exception during label processing occured.")
		raise e

def dologin(request):
	return render(request,'markup/login.html',{'next':request.GET.get('next','/markup/tasks/')}) # TODO add a backwards calculator here

def register(request):
	username = request.POST['username']
	try:
		user = User.objects.get(username=username)
	except ObjectDoesNotExist:
		user = User.objects.create_user(username,username + "@yandex-team.ru","pass")
		user.save()

	user = authenticate(username=username, password='pass')
	login(request, user)

	return HttpResponseRedirect(request.POST.get('next','/markup/tasks/'))

def statistics(request):
	tasks = []
	models = RecommenderModel.objects.all()[:]
	for t in Task.objects.all():
		class task_stat:
			def __init__(self):
				self.title = ""
				self.size = 0
				self.models = []
		task = task_stat()
		task.title = t.title
		task.size = t.video_set.count()
		for m in models:
			task.models.append(Recommendation.objects.filter(task = t, model = m).count())
		tasks.append(task)
	return render(request,'markup/task_statistics.html',{'tasks':tasks,'models':models})


def all_labels(request):
	params = {}
	if 'user' in request.GET:
		params['user'] = User.objects.get(username=request.GET['user'])
	if 'task' in request.GET:
		params['task'] = Task.objects.get(pk=request.GET['task'])
	result = StringIO()
	for l in Label.objects.filter(**params):
		result.write("\t".join(
			[str(l.task.title),
			str(l.current.url),
			str(l.first.url),
			str(l.second.url),
			str(l.user.username),
			str(l.value)]) + "\n")
	return HttpResponse(result.getvalue(),content_type="text/plain")

def user_stats(request):
	params = {}
	if 'task' in request.GET:
		params['task'] = Task.objects.get(pk=request.GET['task'])
	result = {}
	for l in Label.objects.filter(**params):
		if l.user.username not in result:
			result[l.user.username] = 0
		result[l.user.username] += 1
	out = StringIO()
	for u,v in result.items():
		out.write(u + "\t" + str(v) + "\n")
	return HttpResponse(out.getvalue(),content_type="text/plain")

def robots(request):
	return HttpResponse("User-agent: *\nDisallow: /\n",content_type="text/plain")
