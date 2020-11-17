from django.shortcuts import render
from django.http import HttpResponse, HttpRequest, HttpResponseRedirect, HttpResponseForbidden
#from .models import Chart

# Create your views here.
# Create your views here.
def landingpage(request: HttpRequest) -> HttpResponse:
    return HttpResponse('Welcome young ladies.')
