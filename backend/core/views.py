from django.shortcuts import render

# Create your views here.

from django.http import JsonResponse
from django.contrib.gis.geos import Point

from .models import Watershed


def watershed_lookup(request):

    lat = float(request.GET.get("lat"))
    lng = float(request.GET.get("lng"))

    point = Point(lng, lat, srid=4326)

    watershed = Watershed.objects.filter(
        geom__contains=point
    ).first()

    if not watershed:
        return JsonResponse(
            {"error": "not found"},
            status=404
        )

    return JsonResponse({
        "id": watershed.id,
        "name": watershed.name
    })
