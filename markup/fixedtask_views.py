from sys import stdout
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse,Http404,HttpResponseRedirect
from django.shortcuts import render,get_object_or_404
from django.core.urlresolvers import reverse
from markup.models import Video,Label,RecommenderModel,Recommendation,Task,FixedTask,FixedTaskItem
from markup.util import current_videos_with_recommendations, render_label
from django.core.exceptions import PermissionDenied
from random import choice, uniform, shuffle, sample
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from StringIO import StringIO
import logging
logger = logging.getLogger(__name__)
import traceback

class FirstUserData:
	def __init__(self, user):
		self.user = user
		self.username = user.username
		self.second_users = []

class SecondUserData:
	def __init__(self, user):
		self.user = user
		self.username = user.username
		self.total = 0
		self.conflicts = 0


class ConflictData:
	def __init__(self, label1,label2):
		self.label1 = label1
		self.label2 = label2

def get_conflicts(user1,user2,fixedtask):
	conflicts = []

	for fti1 in FixedTaskItem.objects.filter(label__user=user1,task=fixedtask,label__value__in=Label.ISLABELED_VALUES):
		label1 = fti1.label
		try:
			fti2 = FixedTaskItem.objects.get(
				label__user=user2,
				task=fixedtask,
				label__current=label1.current,
				label__first=label1.first,
				label__second=label1.second,
				label__value__in=Label.ISLABELED_VALUES)
			label2 = fti2.label
			if label1.value != label2.value:
				conflicts.append(ConflictData(label1,label2))
		except ObjectDoesNotExist:
			continue
	return conflicts

def fixedtask_statistics(request):
	fixedtask = FixedTask.objects.get(pk=int(request.GET.get("fixedtask")))
	users = []
	for u in User.objects.all():
		if FixedTaskItem.objects.filter(task=fixedtask, label__user=u).exists():
			users.append(FirstUserData(u))
	for u1 in users:
		for u2 in users:
			sud = SecondUserData(u2.user)
			sud.conflicts = len(get_conflicts(u1.user,u2.user,fixedtask))
			sud.total = FixedTaskItem.objects.filter(label__value__in=Label.ISLABELED_VALUES,label__user=u1.user,task=fixedtask).count()
			u1.second_users.append(sud)
	return render(request,'markup/fixedtask_statistics.html',{'users':users,'fixedtask':fixedtask})
		

def show_conflicts(request):
	user1 = User.objects.get(username=request.GET.get("user1"))
	user2 = User.objects.get(username=request.GET.get("user2"))
	fixedtask = FixedTask.objects.get(pk=int(request.GET.get("fixedtask")))

	conflicts = get_conflicts(user1,user2,fixedtask)
	return render(request,'markup/conflicts.html',{"user1":user1,"user2":user2,"conflicts":conflicts})

def show_labels(request):
	fixedtask = FixedTask.objects.get(pk=int(request.GET.get("fixedtask")))
	result = StringIO()
	for fti in FixedTaskItem.objects.filter(task = fixedtask).order_by('label__current','label__user__username'):
		result.write("\t".join(
			[str(fti.label.current.url),
			str(fti.label.first.url),
			str(fti.label.second.url),
			str(fti.label.user.username),
			str(fti.label.value)]) + "\n")
	return HttpResponse(result.getvalue(),content_type="text/plain")

@login_required
def markup_fixed(request):
	user = request.user
	try:
		fixedtask = FixedTask.objects.get(pk = request.GET.get("fixedtask") )
	except KeyError:
		return HttpResponseRedirect(reverse('tasks'))
	except ObjectDoesNotExist:
		return HttpResponseRedirect(reverse('tasks'))

	unmarked_labels = []
	unmarked_labels.extend(fixedtask.label.filter(user=user,value="U"))
	if len(unmarked_labels) > 0:

		label = choice(unmarked_labels)

		return render_label(label,request,str(len(unmarked_labels)) + " pairs remaining.")
		
	else:
		return render(request,'markup/success.html',{})
