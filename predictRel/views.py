from django.shortcuts import render
from pricePredict.models import Product
import urllib.parse
import requests 

# Create your views here.
def get_news(keyword):
    client_id = 'R5V8X2w9Pkvb5_9XWb1P'
    client_secret = 'EuFmp6rjVk'

    url = 'https://openapi.naver.com/v1/search/news.json' 
    headers = {'X-Naver-Client-Id':client_id, 'X-Naver-Client-Secret':client_secret} 
    params = {'query':keyword, 'display':3 } 
    r = requests.get(url, params = params, headers = headers)

    j = r.json()
    return j


def predictRelView(request, product):
    product_mat = {
        'ramyun': ['런던 설탕', '런던 소맥', '미국 대두', '미국 팜유', '미국 소맥' ],
        'bob':['쌀'],
        'sauce':['미국 대두'],
        'egg':['계란'],
        'ice':['런던 설탕'],
        'coffee':['런던 설탕']
    }

    products = Product.objects.all()
    print(products)
    news = []
    for mat in product_mat[product]:
        news.append([mat, get_news(mat)])
      
    context = {'news':news, 'products':products, 'pName':product}
    
    return render(request, 'predictRel/predictRel.html', context)