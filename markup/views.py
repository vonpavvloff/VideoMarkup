from sys import stdout
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse,Http404,HttpResponseRedirect
from django.shortcuts import render,get_object_or_404
from django.core.urlresolvers import reverse
from markup.models import Video,Label,RecommenderModel,Recommendation,Task,FixedTask,FixedTaskItem,DynamicTask,DynamicAssignment
from markup.util import current_videos_with_recommendations,generate_random_triple,render_label
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

@login_required
def task_selection(request):
	return render(request,'markup/tasks.html',{'tasks':Task.objects.all(),'fixedtasks':FixedTask.objects.all(),'dynamictasks':DynamicTask.objects.all()})

# Create your views here.
@login_required
def markup(request):
	user = request.user
	try:
		task = Task.objects.get(pk = request.GET.get("task") )
	except KeyError:
		return HttpResponseRedirect(reverse('tasks'))
	except ObjectDoesNotExist:
		return HttpResponseRedirect(reverse('tasks'))

	totallabels = Label.objects.filter(task=task,user=user,value__in=Label.ISLABELED_VALUES).count()

	current,first,second = generate_random_triple(task=task,user=user)
	label,created = Label.objects.get_or_create(current = current, first = first, second = second, user = user, task = task)
	return render_label(label,request,"You have labeled " + str(totallabels) + " pairs.")

@login_required
def dynamic_markup(request):
	user = request.user
	dynamictask = DynamicTask.objects.get(pk = request.GET.get("task") )

	task = dynamictask.task
	try:
		assignment = DynamicAssignment.objects.get(user=user,dynamictask=dynamictask)
	except ObjectDoesNotExist:
		return render(request,'markup/success.html',{})
	totallabels = Label.objects.filter(task=task,user=user,value__in=Label.ISLABELED_VALUES).count()
	if totallabels >= assignment.size:
		return render(request,'markup/success.html',{})
	# Get unknown labels
	label = Label.objects.filter(task=task,user=user,value='U').first()
	if label is None:
		# No unknown labels, create a label and give it to the assessor with the lowest number of labels
		created = False
		attempts = 10
		while not created:
			current,first,second = generate_random_triple(task=task,user=user)
			label, created = Label.objects.get_or_create(current = current, first = first, second = second, user = user, task = task)
			attempts -= 1
			if attempts <= 0:
				raise ObjectDoesNotExist
		label.ordering = 'L'
		label.save()
		all_users = [(u,Label.objects.filter(user=u,task=task,value__in=Label.ISLABELED_VALUES).count()) for u in User.objects.filter(dynamic_assignment__dynamictask=dynamictask)]
		all_users.sort(key=lambda u: u[1])
		created = False
		for other_user,count in all_users:
			if other_user == user:
				continue
			other_label, created = Label.objects.get_or_create(current = current, first = first, second = second, user = other_user, task = task)
			if not created:
				continue
			other_label.ordering = 'R'
			other_label.save()
			break
		if not created:
			raise ObjectDoesNotExist
	return render_label(label,request,"You have labeled %(current_number)s pairs out of total %(assignment_size)s." %{'current_number':totallabels,'assignment_size':assignment.size})

@login_required
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
		else:
			current.is404 = False
			current.save()
			first.is404 = False
			first.save()
			second.is404 = False
			second.save()


		logger.info("LABEL\t" + str(label))

		return HttpResponse('')
	except Exception, e:
		logger.exception("An exception during label processing occured.")
		raise e

def dologin(request):
	return render(request,'markup/login.html',{'next':request.GET.get('next',reverse('task_selection'))})

def register(request):
	username = request.POST['username']
	try:
		user = User.objects.get(username=username)
	except ObjectDoesNotExist:
		user = User.objects.create_user(username,username + "@yandex-team.ru","pass")
		user.save()

	user = authenticate(username=username, password='pass')
	login(request, user)

	return HttpResponseRedirect(request.POST.get('next',reverse('task_selection')))

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
			task.models.append(Recommendation.objects.filter(task = t, model = m, current__is404=False, recommended__is404=False).count())
		tasks.append(task)
	return render(request,'markup/task_statistics.html',{'tasks':tasks,'models':models})


def all_labels(request):
	params = {}
	if 'user' in request.GET:
		params['user'] = User.objects.get(username=request.GET['user'])
	if 'task' in request.GET:
		params['task'] = Task.objects.get(pk=request.GET['task'])
	result = StringIO()
	for l in Label.objects.filter(**params).filter(value__in=Label.ISLABELED_VALUES):
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
