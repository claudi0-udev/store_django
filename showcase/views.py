from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from .models import Product, Feature, Category, FeatureValue, Brand, Manufacturer, Distributor
from django.core.paginator import Paginator

import json

# Create your views here.

def HelloWorld(request):
    return HttpResponse('<h2>Hello World!</h2>')

def ListProducts(request):
    products = Product.objects.all()
    paginator = Paginator(products, 5) #Show 20 products per page
    page_number = request.GET.get('page')
    page_products = paginator.get_page(page_number)
    print(page_products)
    return render(request, 'products_list.html', {
        'products' : page_products,
    })
    #Json Response
    #data_json = list(Product.objects.values())
    #data_json = {'products' : data_json}
    #return JsonResponse(data_json, safe=False)

def ProductDetail(request, productId):
    product = Product.objects.get(pk=productId)
    category = Category.objects.filter(id=product.category_id)
    featureValues = FeatureValue.objects.filter(product_id=productId)
    print(featureValues, product, category)
    #product = list(Product.objects.filter(id=productId).values())
    #return JsonResponse(product, safe=False)
    return render(request, 'product_detail.html', {
        'product': product,
        'category' : category,
        'featureValues' : featureValues,
    })

def AddNewProduct(request): #Create new product in DB
    if(request.method == 'GET'):
        brands = Brand.objects.all()
        manufacturers = Manufacturer.objects.all()
        distributors = Distributor.objects.all()
        categories = Category.objects.filter(parent_category_id=0)
        return render(request, 'add_product.html', {
            'brands' : brands,
            'manufacturers' : manufacturers,
            'distributors' : distributors,
            'categories' : categories,
        })
    else:
        name = request.POST['nameTxt']
        category = request.POST['categorySelect']
        msrp = request.POST['msrpTxt']
        price = request.POST['priceTxt']
        brand = request.POST['brandSelect']
        manufacturer = request.POST['manufacturerSelect']
        distributor = request.POST['distributorSelect']
        units = request.POST['unitsTxt']
        date = None if request.POST['dateTxt'] == '' else request.POST['dateTxt']
        description = request.POST['descriptionTxtArea']
        try:
            product = Product.objects.create(
                name = name,
                category_id = category,
                brand_id = brand,
                description = description,
                manufacturer_id = manufacturer,
                distributor_id = distributor,
                release_date = date,
                msrp = msrp,
                price = price,
                units = units,
            )
            product.save()
            #Now trying set feature values
            c = product.category.id
            pid = product.pk
            featuresFound = Feature.objects.filter(category_id = c)
            for f in featuresFound:
                feature_value = request.POST['txt_' + str(f.pk)]
                FeatureValue.objects.create(
                    feature_id = f.pk,
                    product_id = pid,
                    value = feature_value,
                )
        except Exception as e:
            print('Error creating new product : ' + str(e))
        return redirect('products')

def GetCategories(request): #Get all categories in JSON format
    categories = list(Category.objects.all().values())
    
    if(len(categories) > 0):
        data = {'message' : 'Success', 'categories' : categories}
    else:
        data = {'message' : 'Not Found'}
    
    return JsonResponse(data)

def GetSubcategories(request, categoryID): #Get categories by ID in JSON format
    sub_categories = list(Category.objects.filter(parent_category_id=categoryID).values())
    
    if(len(sub_categories) > 0):
        data = {'message' : 'Success', 'categories' : sub_categories}
    else:
        data = {'message' : 'Not Found'}
    
    return JsonResponse(data)

def GetFeatures(request, categoryID): #Get all features in JSON format
    features = list(Feature.objects.filter(category_id = categoryID).values())
    if(len(features) > 0):
        data = {'message' : 'Success', 'features' : features}
    else:
        data = {'message' : 'Not Found'}
    return JsonResponse(data)

def GetBrands(request): #Get all brands in JSON format
    brands = list(Brand.objects.all().values())
    
    if(len(brands) > 0):
        data = {'message' : 'Success', 'brands' : brands}
    else:
        data = {'message' : 'Not Found'}
    
    return JsonResponse(data)

def GetManufacturers(request): #Get all manufacturers in JSON format
    manufacturers = list(Manufacturer.objects.all().values())
    
    if(len(manufacturers) > 0):
        data = {'message' : 'Success', 'manufacturers' : manufacturers}
    else:
        data = {'message' : 'Not Found'}
    
    return JsonResponse(data)

def GetDistributors(request): #Get all distributors in JSON format
    distributors = list(Distributor.objects.all().values())
    
    if(len(distributors) > 0):
        data = {'message' : 'Success', 'distributors' : distributors}
    else:
        data = {'message' : 'Not Found'}
    
    return JsonResponse(data)

def AddCategory(request): #Add a new category in DB
    if request.method == 'POST':
        #name = request.POST['name'] 
        #parent_category_id = request.POST['parent_category_id']
        #values = {'name': name, 'parent_category_id' : parent_category_id}
        try:
            name = request.POST.get('name')
            parent_category_id = request.POST.get('parent_category_id')
            category = Category.objects.create(
                name = name,
                parent_category_id = parent_category_id
            )
            category.save()
            return JsonResponse({'message' : 'Success'})
        except Exception as e:
            print('Error creating new category : ' + str(e))

    return HttpResponse('Success')

def AddBrand(request): #Add a new brand in DB
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            brand = Brand.objects.create(
                name = name
            )
            brand.save()
            return JsonResponse({'message' : 'Success'})
        except Exception as e:
            print('Error creating new brand : ' + str(e))

    return HttpResponse('Success')

def AddManufacturer(request): #Add a new manunfacturer in DB
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            manufacturer = Manufacturer.objects.create(
                name = name
            )
            manufacturer.save()
            return JsonResponse({'message' : 'Success'})
        except Exception as e:
            print('Error creating new manufacturer : ' + str(e))

    return HttpResponse('Success')

def AddDistributor(request): #Add a new distributor in DB
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            distributor = Distributor.objects.create(
                name = name
            )
            distributor.save()
            return JsonResponse({'message' : 'Success'})
        except Exception as e:
            print('Error creating new distributor : ' + str(e))

    return HttpResponse('Success')

def AddFeature(request): #Add a new feature referencing category in DB
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            categoryId = request.POST.get('categoryId')
            feature = Feature.objects.create(
                name = name,
                category_id = categoryId,
            )
            feature.save()
            return JsonResponse({'message' : 'Success'})
        except Exception as e:
            print('Error creating new feature: ' + str(e))

    return HttpResponse('Success')
