from decimal import Decimal

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator

from .models import Brand, Category, Distributor, Feature, FeatureValue, Manufacturer, Product


def HelloWorld(request):
    return HttpResponse('<h2>Hello World!</h2>')


def staff_required(view_func):
    decorated = user_passes_test(lambda user: user.is_staff, login_url='login')(view_func)
    return login_required(decorated, login_url='login')


def ListProducts(request):
    # Use select_related to reduce the number of queries when rendering the product list.
    products = Product.objects.select_related('category', 'brand', 'manufacturer', 'distributor').order_by('-id')
    paginator = Paginator(products, 5)
    page_number = request.GET.get('page')
    page_products = paginator.get_page(page_number)
    return render(request, 'products_list.html', {
        'products': page_products,
    })


def ProductDetail(request, productId):
    # Return a 404 instead of crashing when a product ID does not exist.
    product = get_object_or_404(Product.objects.select_related('category', 'brand', 'manufacturer', 'distributor'), pk=productId)
    category = Category.objects.filter(id=product.category_id)
    feature_values = FeatureValue.objects.filter(product_id=productId).select_related('feature')
    return render(request, 'product_detail.html', {
        'product': product,
        'category': category,
        'featureValues': feature_values,
    })


@staff_required
def AddNewProduct(request):
    brands = Brand.objects.all().order_by('name')
    manufacturers = Manufacturer.objects.all().order_by('name')
    distributors = Distributor.objects.all().order_by('name')
    categories = Category.objects.filter(parent_category_id=0).order_by('name')

    if request.method == 'GET':
        return render(request, 'add_product.html', {
            'brands': brands,
            'manufacturers': manufacturers,
            'distributors': distributors,
            'categories': categories,
        })

    # Normalize and validate form values before creating a product.
    name = (request.POST.get('nameTxt') or '').strip()
    category_id = request.POST.get('categorySelect')
    msrp_raw = request.POST.get('msrpTxt', '')
    price_raw = request.POST.get('priceTxt', '')
    brand_id = request.POST.get('brandSelect')
    manufacturer_id = request.POST.get('manufacturerSelect')
    distributor_id = request.POST.get('distributorSelect')
    units_raw = request.POST.get('unitsTxt', '0')
    date = None if request.POST.get('dateTxt', '') == '' else request.POST.get('dateTxt')
    description = (request.POST.get('descriptionTxtArea') or '').strip()

    form_data = {
        'nameTxt': name,
        'categorySelect': category_id,
        'msrpTxt': msrp_raw,
        'priceTxt': price_raw,
        'brandSelect': brand_id,
        'manufacturerSelect': manufacturer_id,
        'distributorSelect': distributor_id,
        'unitsTxt': units_raw,
        'dateTxt': date,
        'descriptionTxtArea': description,
    }

    errors = []

    def _parse_optional_decimal(value):
        if value in (None, ''):
            return None
        return Decimal(value)

    try:
        # Parse money fields as Decimal so prices can store cents safely.
        price = _parse_optional_decimal(price_raw)
        msrp = _parse_optional_decimal(msrp_raw)
        units = int(units_raw) if units_raw not in (None, '') else 0
        category_id = None if category_id in (None, '') else int(category_id)
        brand_id = None if brand_id in (None, '') else int(brand_id)
        manufacturer_id = None if manufacturer_id in (None, '') else int(manufacturer_id)
        distributor_id = None if distributor_id in (None, '') else int(distributor_id)
    except (TypeError, ValueError):
        errors.append('Please enter valid numeric values for MSRP and price')
        return render(request, 'add_product.html', {
            'brands': brands,
            'manufacturers': manufacturers,
            'distributors': distributors,
            'categories': categories,
            'errors': errors,
            'form_data': form_data,
        })

    if not name:
        errors.append('Please provide a product name')
    if not description:
        errors.append('Please provide a product description')
    if category_id is None:
        errors.append('Please select a category')
    if price is None:
        errors.append('Please provide a price')
    elif price < Decimal('1'):
        errors.append('Price must be at least 1')

    if errors:
        return render(request, 'add_product.html', {
            'brands': brands,
            'manufacturers': manufacturers,
            'distributors': distributors,
            'categories': categories,
            'errors': errors,
            'form_data': form_data,
        })

    try:
        product = Product(
            name=name,
            category_id=category_id,
            brand_id=brand_id,
            description=description,
            manufacturer_id=manufacturer_id,
            distributor_id=distributor_id,
            release_date=date,
            msrp=msrp,
            price=price,
            units=units or 0,
        )
        product.save()

        # Persist feature values only when a non-empty value is provided.
        if product.category_id is not None:
            features_found = Feature.objects.filter(category_id=product.category_id)
            for feature in features_found:
                feature_value = (request.POST.get('txt_' + str(feature.pk), '') or '').strip()
                if feature_value:
                    FeatureValue.objects.create(
                        feature_id=feature.pk,
                        product_id=product.pk,
                        value=feature_value,
                    )
    except (ValidationError, ValueError, TypeError):
        errors.append('The product could not be saved. Please review the submitted values.')
        return render(request, 'add_product.html', {
            'brands': brands,
            'manufacturers': manufacturers,
            'distributors': distributors,
            'categories': categories,
            'errors': errors,
            'form_data': form_data,
        })

    return redirect('products')


def GetCategories(request):
    categories = list(Category.objects.all().order_by('name').values())
    if len(categories) > 0:
        data = {'message': 'Success', 'categories': categories}
    else:
        data = {'message': 'Not Found'}
    return JsonResponse(data)


def GetSubcategories(request, categoryID):
    sub_categories = list(Category.objects.filter(parent_category_id=categoryID).order_by('name').values())
    if len(sub_categories) > 0:
        data = {'message': 'Success', 'categories': sub_categories}
    else:
        data = {'message': 'Not Found'}
    return JsonResponse(data)


def GetFeatures(request, categoryID):
    features = list(Feature.objects.filter(category_id=categoryID).order_by('name').values())
    if len(features) > 0:
        data = {'message': 'Success', 'features': features}
    else:
        data = {'message': 'Not Found'}
    return JsonResponse(data)


def GetBrands(request):
    brands = list(Brand.objects.all().order_by('name').values())
    if len(brands) > 0:
        data = {'message': 'Success', 'brands': brands}
    else:
        data = {'message': 'Not Found'}
    return JsonResponse(data)


def GetManufacturers(request):
    manufacturers = list(Manufacturer.objects.all().order_by('name').values())
    if len(manufacturers) > 0:
        data = {'message': 'Success', 'manufacturers': manufacturers}
    else:
        data = {'message': 'Not Found'}
    return JsonResponse(data)


def GetDistributors(request):
    distributors = list(Distributor.objects.all().order_by('name').values())
    if len(distributors) > 0:
        data = {'message': 'Success', 'distributors': distributors}
    else:
        data = {'message': 'Not Found'}
    return JsonResponse(data)


def Register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('products')
    else:
        form = UserCreationForm()

    return render(request, 'register.html', {'form': form})


@staff_required
def AddCategory(request):
    if request.method == 'POST':
        # Validate category input before persisting it.
        name = (request.POST.get('name') or '').strip()
        parent_category_id_raw = request.POST.get('parent_category_id')
        if not name:
            return JsonResponse({'message': 'Error', 'error': 'El nombre es obligatorio.'}, status=400)

        try:
            parent_category_id = None if parent_category_id_raw in (None, '', '0') else int(parent_category_id_raw)
        except (TypeError, ValueError):
            return JsonResponse({'message': 'Error', 'error': 'El identificador de categoría padre es inválido.'}, status=400)

        category = Category.objects.create(name=name, parent_category_id=parent_category_id)
        return JsonResponse({'message': 'Success', 'category_id': category.id})

    return JsonResponse({'message': 'Method not allowed'}, status=405)


@staff_required
def AddBrand(request):
    if request.method == 'POST':
        # Validate brand input before persisting it.
        name = (request.POST.get('name') or '').strip()
        if not name:
            return JsonResponse({'message': 'Error', 'error': 'El nombre es obligatorio.'}, status=400)

        brand = Brand.objects.create(name=name)
        return JsonResponse({'message': 'Success', 'brand_id': brand.id})

    return JsonResponse({'message': 'Method not allowed'}, status=405)


@staff_required
def AddManufacturer(request):
    if request.method == 'POST':
        # Validate manufacturer input before persisting it.
        name = (request.POST.get('name') or '').strip()
        if not name:
            return JsonResponse({'message': 'Error', 'error': 'El nombre es obligatorio.'}, status=400)

        manufacturer = Manufacturer.objects.create(name=name)
        return JsonResponse({'message': 'Success', 'manufacturer_id': manufacturer.id})

    return JsonResponse({'message': 'Method not allowed'}, status=405)


@staff_required
def AddDistributor(request):
    if request.method == 'POST':
        # Validate distributor input before persisting it.
        name = (request.POST.get('name') or '').strip()
        if not name:
            return JsonResponse({'message': 'Error', 'error': 'El nombre es obligatorio.'}, status=400)

        distributor = Distributor.objects.create(name=name)
        return JsonResponse({'message': 'Success', 'distributor_id': distributor.id})

    return JsonResponse({'message': 'Method not allowed'}, status=405)


@staff_required
def AddFeature(request):
    if request.method == 'POST':
        # Validate feature names and category references before persisting them.
        name = (request.POST.get('name') or '').strip()
        category_id = request.POST.get('categoryId')
        if not name or category_id in (None, ''):
            return JsonResponse({'message': 'Error', 'error': 'El nombre y la categoría son obligatorios.'}, status=400)

        try:
            feature = Feature.objects.create(name=name, category_id=int(category_id))
        except (TypeError, ValueError):
            return JsonResponse({'message': 'Error', 'error': 'La categoría es inválida.'}, status=400)

        return JsonResponse({'message': 'Success', 'feature_id': feature.id})

    return JsonResponse({'message': 'Method not allowed'}, status=405)
