from django.conf.urls import patterns, url

urlpatterns = patterns('',
	url(r'^robots.txt$','markup.views.robots', name='robots'),
	url(r'^$','markup.views.dologin', name='nothing'),
	url(r'^dologin/$','markup.views.dologin', name='dologin'),
	url(r'^register/$','markup.views.register', name='register'),

	url(r'^markup$','markup.views.markup', name='markup'),
	url(r'^tasks/$','markup.views.task_selection', name='task_selection'),
	url(r'^label/$','markup.views.label', name='label'),
	url(r'^statistics/$','markup.views.statistics', name='statistics'),
	url(r'^labels$','markup.views.all_labels', name='all_labels'),
	url(r'^userstats$','markup.views.user_stats', name='user_stats'),

	url(r'^markupfixed$','markup.fixedtask_views.markup_fixed', name='markup_fixed'),
	url(r'^fixedtask_statistics$','markup.fixedtask_views.fixedtask_statistics', name='fixedtask_statistics'),
	url(r'^conflicts$','markup.fixedtask_views.show_conflicts', name='show_conflicts'),
)
