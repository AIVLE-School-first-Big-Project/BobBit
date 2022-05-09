from multiprocessing import context
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
from django.views.generic.base import TemplateView
from pricePredict.models import Product
from django.forms.models import model_to_dict
from django.http import JsonResponse
from datetime import date
# Create your views here.


# class HomeView(TemplateView):
#     template_name = "home.html"


def HomeView(request):
    print(request.user)
    User = get_user_model()
    today = date.today()

    search_list = []
    ranking_list = []
    s_list = Product.objects.values()
    r_list = Product.objects.all().order_by('-percent').values()
    r_list = list(r_list)
    r_list = r_list[:5]

    try:
        user = User.objects.get(username=request.user)
    except User.DoesNotExist:
        user = None
    if user:
        for search_item in range(len(s_list)):
            search_list.append(s_list[search_item]["pName"])
        return render(request, "home.html", {"today":  today, "r_list": r_list, "search_list": search_list, 'is_first_login': user.first_login})
    else:
        for search_item in range(len(s_list)):
            search_list.append(s_list[search_item]["pName"])
        return render(request, "home.html", {"today":  today, "r_list": r_list, "search_list": search_list, 'is_first_login': 0})


def modal_check(request):
    User = get_user_model()
    user = User.objects.get(username=request.user)
    user.first_login = 0
    user.save()
    return JsonResponse({"message": '성공'})
