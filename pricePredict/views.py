from operator import mod
from django.shortcuts import render
from sympy import product
from .models import Product, Categori, VirtualProduct
from django.forms.models import model_to_dict
from datetime import date
from .categori_to_emoji import EMOJI
import pandas as pd
import joblib
import requests
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model

# Create your views here.
import json
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST


def CrawlingCoupang(product_name):
    # 쿠팡 크롤링하는 부분
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'}
    url = f'https://www.coupang.com/np/search?component=&q=' + \
        product_name + '&channel=user'
    response = requests.get(url, headers=headers)
    response.encoding = 'utf-8'
    bs = BeautifulSoup(response.text, "html.parser")
    elements = bs.select("#productList > .search-product")[:4]
    datas = []

    for element in elements:
        if(len(element.select(".number")) == 0):
            continue
        free = False
        if(element.select(".badge")[0].text != ""):
            free = True
        datas.append({
            "pName": element.select(".name")[0].text,
            "pFree": free,
            "price": element.select(".price-value")[0].text,
            "plink": "https://www.coupang.com" + element.select("a")[0].get("href")
        })

    return datas


def priceViewbyParam(request, product_id):
    # 오늘 날짜
    today = date.today()
    lastmonth = today.month

    product = Product.objects.get(pNo=product_id)
    # 좋아요 되어잇는지 아닌지
    isLike = None
    user = request.user
    if product.wish_user.filter(id=user.id).exists():
        isLike = True
    else:
        isLike = False

    product_dict = model_to_dict(product)
    cNo = product_dict['cKey']

    # ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ
    # 데이터 불러오기
    pd_data = pd.read_csv(
        'static/csv/result_product_csv/' + product_dict['pName'] + '_prodata.csv')

    # 모델 불러오기
    model = joblib.load('static/model/'+product_dict['pName']+'.pkl')
    # 마지막 행 가져와서 예측
    last_idx = pd_data.index[-1]

    now_data = pd_data.drop(
        columns=['제품명', '날짜', 'next_price'], axis=1)

    # 현재 가격
    now_price = now_data['price'].array[-1]

    pd_data = pd_data[['날짜', 'price']]
    pd_data.rename(columns={'날짜': 'date', 'price': 'value'}, inplace=True)
    pd_data = pd_data.to_json(orient='records')

    pred = model.predict(now_data)
    # 마지막 예측가
    next_price = pred[-1]

    # ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ
    categori_list = Product.objects.filter(cKey=cNo)

    pd_list = []
    product_info = product_dict

    for item in categori_list:
        pd_list.append({
            'pName': model_to_dict(item)['pName'],
            'pNo': model_to_dict(item)['pNo'],
            'price': model_to_dict(item)['price'],
        })

    # ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ크롤링 ㅡㅡㅡㅡㅡㅡㅡㅡㅡ
    # crawlingdata = CrawlingCoupang(product_info['pName'])
    crawlingdata = []

    if request.method == 'GET':
        return render(
            request, 'pricePredict/price_page.html',
            {'today': today,  # 오늘 날짜
             'pd_list': pd_list,
             'lastmonth': lastmonth,
             'crawlingdata': crawlingdata,
             'icon': EMOJI[cNo],
             'product_info': product_info,  # 해당 상품의 db 데이터
             'pd_data': pd_data,        # 해당 상품의 지금까지 csv데이터
             'next_price': next_price,  # 다음달 상품 가격
             'now_price': now_price,    # 현재 상품 가격
             'wish_count': product.count_wish_user(),
             'isLike': isLike,
             })


@login_required
@require_POST
def product_wish(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=product_id)
        user = request.user
        message = None

        if product.wish_user.filter(id=user.id).exists():
            product.wish_user.remove(user)
            message = '좋아요 취소'
        else:
            product.wish_user.add(request.user)
            message = '좋아요'

        context = {'wish_count': product.count_wish_user(), 'message': message}
        return JsonResponse(context, safe=False)


@login_required
@require_POST
def product_buy(request, product_id):
    if request.method == 'POST':
        try:
            quantityVal = request.POST['quantityVal']
            priceVal = request.POST['priceVal']
            User = get_user_model()
            user = get_object_or_404(User, username=request.user)
            user.point = user.point - (int(priceVal) * int(quantityVal))
            user.save()

            if(get_object_or_404(VirtualProduct, pNo=product_id, userID=user) == None):
                virtualProduct = VirtualProduct(
                    pNo=get_object_or_404(Product, pNo=product_id),
                    pNum=int(quantityVal),
                    userID=user
                )
                virtualProduct.save()
            else:
                virtualProduct = get_object_or_404(
                    VirtualProduct, pNo=product_id, userID=user)
                virtualProduct.pNum = virtualProduct.pNum + int(quantityVal)
                virtualProduct.save()

            return JsonResponse({'content': True}, safe=False)
        except Exception as e:
            return JsonResponse({'content': str(e)}, safe=False)


def test(request):
    products = Product.objects.all()
    user = request.user
    for product in products:
        print(product.wish_user.filter(id=user.id))
