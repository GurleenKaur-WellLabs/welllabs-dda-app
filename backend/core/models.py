from django.contrib.gis.db import models

# Create your models here.

class Watershed(models.Model):

    name = models.CharField(max_length=255, null=True)

    geom = models.MultiPolygonField()

    class Meta:
        managed = False
        db_table = "watersheds"
