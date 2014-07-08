from markup.models import Task, Recommendation,Video,TaskItem,RecommenderModel,Label
from django.core.exceptions import ObjectDoesNotExist
from httplib import HTTPConnection
from urlparse import urlparse
from urllib import quote,urlopen
import subprocess
import logging
from xml.dom.minidom import parse
from random import shuffle,choice,sample
logger = logging.getLogger(__name__)

skipMapReduceCommands = False

def get_embed(video_url):
	conn = HTTPConnection("video.yandex.net")
	get_embed_url = "/embed.xml?params=%26embed%3Dy&width=612.8&height=344.7&link=" + quote(video_url)
	logger.info("Getting embed: " + get_embed_url)
	conn.request("GET",get_embed_url)
	res = conn.getresponse()
	result = res.getheader("Location")

	if result is not None:
		result = result.replace("?autoplay=1","?autoplay=0")
		result = result.replace("&autoplay=1","&autoplay=0")
		result = result.replace("?autoStart=true","?autoStart=false")
		result = result.replace("&autoStart=true","&autoStart=false")
		result = result.replace("?auto=1","?auto=0")
		result = result.replace("&auto=1","&auto=0")
		result = result.replace("?ap=1","?ap=0")
		result = result.replace("&ap=1","&ap=0")

		if 'video.yandex.ru' in result:
			result = result.replace("&autoplay=0","")
			result = result.replace("?autoplay=0&","?")
			result = result.replace("?autoplay=0","")

	return result

def current_videos(task):
	for ti in TaskItem.objects.filter(task=task).select_related():
		video = ti.video
		if not video.is404:
			yield ti.video

def current_videos_with_recommendations(task):
	for ti in TaskItem.objects.filter(task=task).select_related():
		video = ti.video
		if (video.recommendations.count() > 1) and not video.is404:
			yield ti.video

def add_video(url):
	if not url.startswith("http://") and not url.startswith("https://"):
		url = "http://" + url
	try:
		video,created = Video.objects.get_or_create(url=url)
	except Exception:
		logger.exception("An exception during adding video.")
		raise ObjectDoesNotExist
	if created:
		embed = get_embed(url)
		if embed != None:
			video.embed = embed
			video.save()
		else:
			video.delete()
			logger.info('Failed to add video ' + url)
			raise ObjectDoesNotExist
	logger.info("Added video " + url)
	return video

def add_recommendation(current_url,recommended_url,weight,model,task):
	if not isinstance(model,RecommenderModel):
		model,created = RecommenderModel.objects.get_or_create(title=model)
	if not isinstance(task,Task):
		task,created = Task.objects.get_or_create(title=task)
	video = add_video(recommended_url)
	try:
		current = add_video(current_url)
		TaskItem.objects.get(task=task,video=current)
	except ObjectDoesNotExist:
		logger.warn("Adding recommendation to a video that is not in task, or could not get the current video " + current_url + " " + recommended_url)
		video.delete()
		raise
	rec, created = Recommendation.objects.get_or_create(current = current, recommended = video, model = model, task = task)
	rec.weight = weight
	rec.save()
	logger.info("Added recommendation: " + current_url + " " + recommended_url + " " + str(model) + " " + str(task))

def mapreduce(**params):
	if skipMapReduceCommands:
		return 0
	attrs = ["/Berkanavt/mapreduce/bin/mapreduce-dev"]
	def add(key,value):
		attrs.append('-' + str(key))
		attrs.append(str(value))
	
	output = None
	close_output = False
	input = None
	close_input = False

	try:
		for k,v in params.items():
			if k == 'stdout':
				if isinstance(v,str):
					output = open(v,'w+')
					close_output = True
				else:
					output = v
				continue
			elif k == 'stdin':
				if isinstance(v,str):
					input = open(v)
					close_input = True
				else:
					input = v
				continue
			else:
				if isinstance(v,str):
					add(k,v)
				else:
					for i in v:
						add(k,i)

		if 'server' not in params:
			add('server','cedar00.search.yandex.net:8013')

		if 'opt' not in params:
			add('opt','user=clickadd')

		logger.info(str(attrs))

		code = subprocess.call(attrs, env={'MR_NET_TABLE':'ipv6'}, stdout = output, stdin = input)
		return code
	finally:
		if close_input:
			input.close()
		if close_output:
			output.close()

def get_video_title_from_search(url):
	searchurl = 'http://video-xmlsearch.hamster.yandex.ru/xmlsearch?g=1.dg.20.1.-1&waitall=da&text=url:' + quote(url)
	try:
		inp = urlopen(searchurl)
		dom = parse(inp)
		return dom.getElementsByTagName('title')[0].firstChild.data
	finally:
		inp.close()

def generate_random_triple(**params):
	task = params["task"]
	attempts = 10
	while attempts > 0:
		attempts -= 1
		currentVideos = []
		currentVideos.extend(current_videos_with_recommendations(task))
		currentVideo = choice(currentVideos) # Select a random current video, room for optimization here
		recs = []
		recs.extend(currentVideo.recommendations.filter(recommended__is404 = False, task = task).distinct())
		recVideos = set()
		recVideos.update(map(lambda x:x.recommended,recs))
		if len(recVideos) < 2:
			continue
		pair = sample(recVideos,2)
		if currentVideo in pair:
			continue
		if pair[0].url == pair[1].url:
			continue
		pair.sort(key=lambda x:x.pk)
		if 'user' in params:
			if Label.objects.filter(
				current = currentVideo,
				task = task,
				first = pair[0],
				second=pair[1],
				user=params['user'],
				value__in=Label.ISLABELED_VALUES).exists():
				continue	
		return currentVideo,pair[0],pair[1]
	raise ObjectDoesNotExist
