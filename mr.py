import subprocess
import logging
logger = logging.getLogger(__name__)
from itertools import chain

defaultServer = 'cedar00.search.yandex.net:8013'
defaultUser = 'clickadd'
defaultFilePath = '/home/pavvloff/bin/'

class MapReduceFailed(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return "MapReduce operation exited with code " + str(self.value)

def mapreduce(**params):
	import mr
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
			elif k == 'file':
				if isinstance(v,str):
					if not '/' in v:
						add(k,mr.defaultFilePath + v)
					else:
						add(k,v)
				else:
					for i in v:
						if not '/' in i:
							add(k,mr.defaultFilePath + i)
						else:
							add(k,i)
			else:
				if isinstance(v,str):
					add(k,v)
				else:
					for i in v:
						add(k,i)

		if 'server' not in params:
			add('server',mr.defaultServer)

		if 'opt' not in params:
			add('opt','user=' + mr.defaultUser)

		env = {'MR_NET_TABLE':'ipv6','MR_OPT':"threadcount=50,jobcount.multiplier=50"}

		logger.info(" ".join(chain(map(lambda x: x[0] + '=' + x[1],env.items()),attrs)))

		code = subprocess.call(attrs, env=env, stdout = output, stdin = input)
		if code != 0:
			raise MapReduceFailed(code)
	finally:
		if close_input:
			input.close()
		if close_output:
			output.close()
