from django.shortcuts import render

# Create your views here.


def priceViewbyParam(request, product_id):

    if request.method == 'GET':
        return render(
            request, 'pricePredict/test.html',
            {'data': product_id}
        )
