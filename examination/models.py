from __future__ import unicode_literals

from django.db import models

# Create your models here.
# 
class User(models.Model):
    student_id = models.CharField(max_length=11)
    password = models.CharField(max_length=64)
    ip = models.CharField(max_length=15)
    score = models.IntegerField()
    def __unicode__(self):
        return self.student_id

class Problems(models.Model):
    stem_type = models.CharField(max_length=30)
    difficulty_degree = models.CharField(max_length=2)
    stem = models.CharField(max_length=3000,verbose_name='stem')
    options = models.CharField(max_length=1000,blank=True)
    answer = models.CharField(max_length=1000)
    def __unicode__(self):
        return self.stem
