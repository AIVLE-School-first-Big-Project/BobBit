from bbuser.models import User
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.forms.models import model_to_dict
from pricePredict.models import Product
import glob
import numpy as np


import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error
import joblib
from statsmodels.tsa.stattools import grangercausalitytests


def slidingwindow(data, feature, length, is_diff=False):
    df = data.copy()

    for i in range(1, length+1):
        df[feature+'-'+str(i)] = df[feature].shift(i)
        df[feature+'-'+str(i)] = df[feature+'-'+str(i)].astype('float64')

    if is_diff:
        df[feature+'1년증가량'] = df[feature+'-1']-df[feature+'-'+str(length)]

    return df


def get_fea_with_gran(data, feature):
    Min = 1
    min_idx = 0
    data = data.set_index('날짜')
    for i in range(1, 16):
        value = grangercausalitytests(data[['price', feature]], maxlag=15)[
            i][0]['ssr_ftest'][1]
        if Min > value:
            min_idx = i
            Min = value

    return min_idx


def M_to_K(x):
    if 'M' in x:
        x = float(x[:-1])*1000000
    else:
        x = float(x)*1000
    return str(x)


def df_formatting(price, df, material):
    # 4개월 전으로 shift
    features = ['날짜', material+'종가', material+'거래량', material+'변동 %', ]

    drop_indexs = df.loc[df['종가'].isna() == True].index
    df.drop(drop_indexs, inplace=True)

    df = df.replace('-', np.NaN)

    print(df['거래량'].isna().sum()/len(df))
    print(df['거래량'].isna().sum())
    print(len(df))
    print(df)
    if (df['거래량'].isna().sum()/len(df)) > 0.8:
        df.drop('거래량', axis=1, inplace=True)
    # formatting
    df['날짜'] = pd.to_datetime(df['날짜'], format='%Y년 %m월')
    if(df['종가'].dtypes != 'float64'):
        df['종가'] = df['종가'].str.replace(",", '')
    df['변동 %'] = df['변동 %'].str.replace("%", '')

    if '거래량' in list(df):
        df.fillna(method='ffill', inplace=True)
        df.fillna(method='bfill', inplace=True)
        df['거래량'] = df['거래량'].str.replace('K', '')
        df['거래량'] = df['거래량'].apply(M_to_K)
        df = df.astype({'종가': 'float', '변동 %': 'float', '거래량': 'float'})
        df.columns = features
    else:
        df = df.astype({'종가': 'float', '변동 %': 'float'})
        features.remove(material+'거래량')
        df.columns = features

    # df = slidingwindow(df, material+'종가', 12, is_diff=True)
    df = price.join(df.set_index('날짜'), on='날짜')

    df.fillna(method='ffill', inplace=True)
    df.fillna(method='bfill', inplace=True)

    for feature in features:
        if feature == '날짜':
            continue
        idx = get_fea_with_gran(df, feature)
        df[feature+'-'+str(idx)] = df[feature].shift(idx)
        df[feature+'-'+str(idx)] = df[feature+'-'+str(idx)].astype('float64')

    features.remove('날짜')
    df.drop(features, axis=1, inplace=True)
    return df


def C_to_DB_consumerprice(spec_list, product_csv, materials_csv):
    all_data = pd.read_csv('./static/csv/product_Crawling_csv/' + product_csv)
    materials_dfs = []

    # materials_csv dataframe화

    for spec in spec_list:
        df = all_data.loc[all_data['제품명'] == spec]
        # price 안나와있는 값 제거
        drop_index = df.loc[df['price'] == '-'].index
        df.drop(drop_index, inplace=True)
        # 날짜 colume 정규화
        df['날짜'] = pd.to_datetime(df['날짜'], format='%Y년 %m월')
        # 날짜 순 정렬
        df.sort_values(by='날짜', inplace=True, ignore_index=True)
        # price 전처리
        df['price'] = df['price'].str.replace(",", '')
        df = df.astype({'price': 'int'})
        # next_price(Target) 생성
        df['next_price'] = df['price'].shift(-1)

        for material in materials_csv:
            temp = pd.read_csv('./static/csv/materirals_Crawling_csv/' + material,
                               usecols=['날짜', '종가', '변동 %', '거래량'],
                               thousands=',')
            df = df_formatting(df, temp, material)
            # materials_dfs.append(df_formatting(price, temp, material))

        df.fillna(method='ffill', inplace=True)
        df.fillna(method='bfill', inplace=True)

        # material이랑 product랑 합치는부분
        # count = 0
        # for material in materials_dfs:
        #     df = df.join(material.set_index('날짜'), on='날짜')

        # 과거 데이터 중 NaN제거
        # drop_indexs = df.loc[df['m_price0'].isna() == True].index
        # df.drop(drop_indexs, inplace=True)
        filename = spec + '_prodata.csv'

        # 경로지정
        df.to_csv('./static/csv/result_product_csv/'+filename, index=False)

        # 현재 가격
        now_price = df['price'].array[-1]
        # 데이터 옮기기
        now_data = df.drop(columns=['제품명', '날짜', 'next_price'], axis=1)

        # 현재까지 데이터로 모델 생성
        # ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ
        # 현재 날짜 제거
        drop_indexs = df.loc[df['next_price'].isna() == True].index
        df.drop(drop_indexs, inplace=True)

        # # 날짜,이름 제거
        df.drop(columns=['날짜', '제품명'], axis=1, inplace=True)

        x = df.drop('next_price', axis=1)
        y = df['next_price']

        x_train, x_test = x[:int(len(x)*(70/100))], x[int(len(x)*(70/100)):]
        y_train, y_test = y[:int(len(y)*(70/100))], y[int(len(y)*(70/100)):]

        model_LR = LinearRegression()
        model_LR.fit(x, y)
        pred = model_LR.predict(now_data)

        # 마지막 예측가
        next_price = pred[-1]

        # 성능 평가용도
        test_model_LR = LinearRegression()
        test_model_LR.fit(x_train, y_train)
        y_pred = test_model_LR.predict(x_test)

        # RMSE
        RMSE = mean_squared_error(y_test, y_pred)**0.5
        MAPE = mean_absolute_percentage_error(y_test, y_pred)
        percent = round((((next_price - now_price)/now_price) * 100), 2)

        # Product DB 저장
        product = get_object_or_404(Product, pName=spec)
        product.price = now_price
        product.nextprice = next_price
        product.RMSE = RMSE
        product.MAPE = MAPE
        product.percent = percent
        product.save()

        # 모델 저장
        joblib.dump(model_LR, './static/model/' + spec + '.pkl')


def load_adpage(request):
    # 어드민 검증
    User = get_user_model()
    user = get_object_or_404(User, username=request.user)
    user = model_to_dict(user)
    if(user['username'] != 'admin'):
        return redirect('home')
    else:
        # 어드민일때

        # 원자재 list
        material_list = []
        # 가공품 File list
        product_list = []
        # product 이름들
        pName_list = []

        m_path = "./static/csv/materirals_Crawling_csv/*"
        p_path = "./static/csv/product_Crawling_csv/*"

        products = Product.objects.all().values('pName')
        for p in products:
            # temp = model_to_dict(p)
            pName_list.append(p['pName'])
        # print(glob.glob(m_path))
        for f in glob.glob(m_path):
            # print(f)
            try:
                f = f.split("\\")[1]
            except:
                f = f.split("/")[-1]
            material_list.append(f)

        for f in glob.glob(p_path):
            try:
                f = f.split("\\")[1]
            except:
                f = f.split("/")[-1]
            product_list.append(f)

        return render(request, 'bbadmin/adminpage.html',
                      {'material_list': material_list,
                       'product_list': product_list,
                       'pName_list': pName_list})


def Crawlingdata_to_DB(request):
    # form 처리
    try:
        if request.method == 'POST':
            postdict = dict(request.POST)
            # 추출하고 싶은 상품 list
            spec_list = postdict['product_name']
            # 커피 csv
            product_csv = postdict['product_csv'][0]
            # 원자재 csv
            materials_csv = postdict['material']

            C_to_DB_consumerprice(spec_list, product_csv, materials_csv)

            return redirect('bbadmin:adpage')

    except Exception as e:
        return JsonResponse({'content': str(e)}, safe=False)
