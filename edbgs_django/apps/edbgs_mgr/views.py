"""ED BGS Manager django views."""
from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def index(request):
  """Basic main page view."""
  return HttpResponse('The main page of the ED BGS Manager app.')
