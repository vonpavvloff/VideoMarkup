from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Task(models.Model):
	title = models.CharField(max_length = 300)
	def __str__(self):
		return self.title

class Video(models.Model):
	url = models.URLField(unique = True,max_length=255)
	embed = models.TextField(default = "")
	title = models.TextField(default = "")
	is404 = models.BooleanField(default = False)
	task = models.ManyToManyField(Task, through='TaskItem')
	def __str__(self):
		return self.url

class TaskItem(models.Model):
	task = models.ForeignKey(Task)
	video = models.ForeignKey(Video)

class Label(models.Model):
	LABEL_VALUES = (
		('U', 'Unknown'),
		('F', 'First'),
		('f', 'First 404'),
		('S', 'Second'),
		('s', 'Second 404'),
		('B', 'Both bad'),
		('c', 'Current 404'),
	)
	ISLABELED_VALUES=['F','S','B','f','s','c']
	user = models.ForeignKey(User)
	time = models.DateTimeField(auto_now_add = True)
	current = models.ForeignKey(Video, related_name="+")
	first = models.ForeignKey(Video, related_name="+")
	second = models.ForeignKey(Video, related_name="+")
	value = models.CharField(max_length=1, choices=LABEL_VALUES, default="U")
	task = models.ForeignKey(Task)
	ORDER_VALUES = (
		('L','Left'),
		('R','Right'),
		('A','Any'),
	)
	ordering = models.CharField(max_length=1, choices=LABEL_VALUES, default='A')
	
	def __str__(self):
		return self.user.username + "\t" + self.current.url + "\t" + self.first.url + "\t" + self.second.url + "\t" + self.ordering + "\t" + self.value

class FixedTask(models.Model):
	title = models.CharField(max_length = 300)
	label = models.ManyToManyField(Label, through='FixedTaskItem')

class FixedTaskItem(models.Model):
	task = models.ForeignKey(FixedTask)
	label = models.ForeignKey(Label)

class DynamicTask(models.Model):
	title = models.CharField(max_length = 300)
	task = models.ForeignKey(Task)
	def __str__(self):
		return self.title

class DynamicAssignment(models.Model):
	dynamictask = models.ForeignKey(DynamicTask)
	user = models.ForeignKey(User, related_name="dynamic_assignments", related_query_name="dynamic_assignment")
	size = models.IntegerField()
	def __str__(self):
		return self.dynamictask.title + " " + self.user.username + " " + str(self.size)

class RecommenderModel(models.Model):
	title = models.CharField(max_length = 300)
	def __str__(self):
		return self.title

class Recommendation(models.Model):
	current = models.ForeignKey(Video, related_name="recommendations", related_query_name="recommendation")
	recommended = models.ForeignKey(Video, related_name="+")
	model = models.ForeignKey(RecommenderModel)
	task = models.ForeignKey(Task)
	weight = models.FloatField(default = 0.0)
	def __str__(self):
		return self.model.title + "\t" + self.current.url + "\t" + self.recommended.url + "\t" + str(self.weight)
