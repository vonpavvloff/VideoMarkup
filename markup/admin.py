from django.contrib import admin
from markup.models import Video, Label, RecommenderModel, Recommendation, Task, DynamicTask, DynamicAssignment

# Register your models here.

admin.site.register(Video)
admin.site.register(Label)
admin.site.register(RecommenderModel)
admin.site.register(Task)
admin.site.register(Recommendation)
admin.site.register(DynamicTask)
admin.site.register(DynamicAssignment)
