import csv
import json
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate, TruncMonth

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone


from .cart import Cart
from .emails import send_dispatch_notification_email, send_order_confirmation_email

from .forms import OrderCreateForm, ProductForm, UserLoginForm, UserRegistrationForm


from .models import (
    Brand,
    Category,
    Coupon,
    Distributor,
    Feature,

    FeatureValue,
    Manufacturer,
    Order,
    OrderItem,
    Product,
    ProductAuditLog,
    ProductImage,
    ProductReview,
    ShippingRate,

    StoreSettings,
)





def HelloWorld(request):
    return HttpResponse('<h2>Hello World!</h2>')


def HomePage(request):
    featured_products = Product.objects.filter(is_active=True).select_related('category', 'brand', 'manufacturer', 'distributor').order_by('-id')[:6]
    best_selling_products = Product.objects.filter(is_active=True).select_related('category').order_by('-units')[:4]
    new_products = Product.objects.filter(is_active=True).select_related('category').order_by('-id')[:4]

    # Categorías Populares dinámicas con métricas de ventas y visitas
    categories_qs = Category.objects.filter(Q(parent_category_id=0) | Q(parent_category_id__isnull=True)).annotate(
        product_count=Count('product', filter=Q(product__is_active=True)),
        total_sold=Coalesce(Sum('product__order_items__quantity', filter=Q(product__is_active=True, product__order_items__order__paid=True)), 0),
        product_views=Coalesce(Sum('product__views_count', filter=Q(product__is_active=True)), 0),
    ).annotate(
        total_views=F('views_count') + F('product_views')
    )



    popular_categories = categories_qs.order_by('-total_sold', '-total_views', '-product_count', 'name')[:8]
    all_categories = Category.objects.order_by('name')

    search_query = (request.GET.get('q') or request.GET.get('search') or '').strip()
    category_id = request.GET.get('category')
    ordering = request.GET.get('ordering') or '-id'

    products_query = Product.objects.filter(is_active=True).select_related('category', 'brand', 'manufacturer', 'distributor')

    if search_query:
        products_query = products_query.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    if category_id:
        products_query = products_query.filter(category_id=category_id)
        Category.objects.filter(pk=category_id).update(views_count=F('views_count') + 1)

    if ordering in {'-id', 'id', '-price', 'price', '-units', 'units'}:
        products_query = products_query.order_by(ordering)
    else:
        products_query = products_query.order_by('-id')

    products = products_query[:8]

    return render(request, 'home.html', {
        'featured_products': featured_products,
        'best_selling_products': best_selling_products,
        'new_products': new_products,
        'popular_categories': popular_categories,
        'categories': all_categories,
        'search_query': search_query,
        'category_id': category_id,
        'ordering': ordering,
        'products': products,
    })



def staff_required(view_func):
    decorated = user_passes_test(lambda user: user.is_staff, login_url='login')(view_func)
    return login_required(decorated, login_url='login')


def ListProducts(request):
    user = getattr(request, 'user', None)
    is_staff = bool(user and user.is_authenticated and user.is_staff)
    show_archived = request.GET.get('archived') == '1' and is_staff

    search_query = (request.GET.get('q') or request.GET.get('search') or '').strip()
    category_id = request.GET.get('category')
    brand_id = request.GET.get('brand')
    ordering = request.GET.get('ordering') or '-id'

    if show_archived:
        products_qs = Product.objects.filter(is_active=False).select_related('category', 'brand', 'manufacturer', 'distributor').order_by('-deleted_at')
    else:
        products_qs = Product.objects.filter(is_active=True).select_related('category', 'brand', 'manufacturer', 'distributor')

    if search_query:
        products_qs = products_qs.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    if category_id:
        products_qs = products_qs.filter(category_id=category_id)

    if brand_id:
        products_qs = products_qs.filter(brand_id=brand_id)

    if not show_archived:
        if ordering in {'-id', 'id', '-price', 'price', '-units', 'units'}:
            products_qs = products_qs.order_by(ordering)
        else:
            products_qs = products_qs.order_by('-id')

    paginator = Paginator(products_qs, 8)
    page_number = request.GET.get('page')
    page_products = paginator.get_page(page_number)
    archived_count = Product.objects.filter(is_active=False).count() if is_staff else 0
    categories = Category.objects.order_by('name')
    brands = Brand.objects.order_by('name')

    return render(request, 'products_list.html', {
        'products': page_products,
        'show_archived': show_archived,
        'archived_count': archived_count,
        'search_query': search_query,
        'category_id': category_id,
        'brand_id': brand_id,
        'ordering': ordering,
        'categories': categories,
        'brands': brands,
        'total_results': paginator.count,
    })



def ProductDetail(request, productId):
    product = get_object_or_404(Product.objects.select_related('category', 'brand', 'manufacturer', 'distributor'), pk=productId)
    user = getattr(request, 'user', None)
    is_staff = bool(user and user.is_authenticated and user.is_staff)
    if not product.is_active and not is_staff:
        messages.error(request, 'El producto solicitado no se encuentra disponible en el catálogo.')
        return redirect('products')

    # Incrementar vistas de producto y categoría
    Product.objects.filter(pk=productId).update(views_count=F('views_count') + 1)
    if product.category_id:
        Category.objects.filter(pk=product.category_id).update(views_count=F('views_count') + 1)

    category = Category.objects.filter(id=product.category_id)
    feature_values = FeatureValue.objects.filter(product_id=productId).select_related('feature')

    # Reseñas y Calificaciones
    reviews = list(product.reviews.select_related('user').all())
    review_count = len(reviews)
    avg_rating = product.get_average_rating()

    # Comprobar si el usuario actual ya opinó y si tiene compra verificada
    user_review = None
    is_verified_buyer = False
    if user and user.is_authenticated:
        user_review = next((r for r in reviews if r.user_id == user.id), None)
        is_verified_buyer = Order.objects.filter(user=user, paid=True, items__product=product).exists()

    # Desglose de estrellas (porcentajes de 1 a 5)
    rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in reviews:
        if 1 <= r.rating <= 5:
            rating_counts[r.rating] += 1

    rating_breakdown = []
    for star in range(5, 0, -1):
        count = rating_counts[star]
        percent = int((count / review_count * 100)) if review_count > 0 else 0
        rating_breakdown.append({
            'star': star,
            'count': count,
            'percent': percent,
        })

    # Productos relacionados (Cross-selling)
    related_qs = Product.objects.filter(is_active=True, category=product.category).exclude(id=product.id)[:4]
    related_products = list(related_qs)
    if len(related_products) < 4:
        extra_needed = 4 - len(related_products)
        excluded_ids = [product.id] + [p.id for p in related_products]
        extra_qs = Product.objects.filter(is_active=True).exclude(id__in=excluded_ids)[:extra_needed]
        related_products.extend(list(extra_qs))

    whatsapp_msg = f"Hola! Quisiera consultar sobre el producto: {product.name}"

    return render(request, 'product_detail.html', {
        'product': product,
        'category': category,
        'featureValues': feature_values,
        'related_products': related_products,
        'reviews': reviews,
        'review_count': review_count,
        'avg_rating': avg_rating,
        'user_review': user_review,
        'is_verified_buyer': is_verified_buyer,
        'rating_breakdown': rating_breakdown,
        'whatsapp_custom_message': whatsapp_msg,
    })



@login_required(login_url='login')
def AddProductReview(request, productId):
    """Permite a un usuario autenticado calificar y opinar sobre un producto."""
    if request.method != 'POST':
        return redirect('productDetail', productId=productId)

    product = get_object_or_404(Product, pk=productId, is_active=True)
    rating_raw = request.POST.get('rating', '5')
    title = request.POST.get('title', '').strip()
    comment = request.POST.get('comment', '').strip()

    try:
        rating = int(rating_raw)
        if rating < 1 or rating > 5:
            rating = 5
    except ValueError:
        rating = 5

    if not title or not comment:
        messages.error(request, 'Por favor completa el título y el comentario de tu opinión.')
        return redirect('productDetail', productId=productId)

    # Verificar si el usuario compró el producto
    is_verified = Order.objects.filter(user=request.user, paid=True, items__product=product).exists()

    ProductReview.objects.update_or_create(
        product=product,
        user=request.user,
        defaults={
            'rating': rating,
            'title': title,
            'comment': comment,
            'is_verified_purchase': is_verified,
        }
    )

    messages.success(request, '¡Gracias! Tu opinión ha sido publicada exitosamente.')
    return redirect('productDetail', productId=productId)





@staff_required
def AddNewProduct(request):
    brands = Brand.objects.all().order_by('name')
    manufacturers = Manufacturer.objects.all().order_by('name')
    distributors = Distributor.objects.all().order_by('name')
    categories = Category.objects.filter(parent_category_id=0).order_by('name')

    if request.method == 'GET':
        form = ProductForm()
        return render(request, 'add_product.html', {
            'brands': brands,
            'manufacturers': manufacturers,
            'distributors': distributors,
            'categories': categories,
            'form': form,
        })

    form_data = {
        'nameTxt': (request.POST.get('nameTxt') or '').strip(),
        'categorySelect': request.POST.get('categorySelect', ''),
        'msrpTxt': request.POST.get('msrpTxt', ''),
        'priceTxt': request.POST.get('priceTxt', ''),
        'brandSelect': request.POST.get('brandSelect', ''),
        'manufacturerSelect': request.POST.get('manufacturerSelect', ''),
        'distributorSelect': request.POST.get('distributorSelect', ''),
        'unitsTxt': request.POST.get('unitsTxt', '0'),
        'dateTxt': request.POST.get('dateTxt', ''),
        'descriptionTxtArea': (request.POST.get('descriptionTxtArea') or '').strip(),
    }

    form = ProductForm({
        'name': form_data['nameTxt'],
        'category': form_data['categorySelect'],
        'brand': form_data['brandSelect'],
        'manufacturer': form_data['manufacturerSelect'],
        'distributor': form_data['distributorSelect'],
        'description': form_data['descriptionTxtArea'],
        'release_date': form_data['dateTxt'],
        'msrp': form_data['msrpTxt'],
        'price': form_data['priceTxt'],
        'units': form_data['unitsTxt'],
    }, request.FILES)

    if form.is_valid():
        product = form.save()
        extra_files = request.FILES.getlist('extra_images')
        for f in extra_files:
            ProductImage.objects.create(product=product, image=f)
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
        messages.success(request, 'Producto creado exitosamente.')
        return redirect('products')


    errors = []
    for field_errors in form.errors.values():
        for error in field_errors:
            errors.append(error)

    return render(request, 'add_product.html', {
        'brands': brands,
        'manufacturers': manufacturers,
        'distributors': distributors,
        'categories': categories,
        'errors': errors,
        'form_data': form_data,
        'form': form,
    })


@user_passes_test(lambda u: u.is_staff, login_url='login')
def EditProduct(request, productId):
    product = get_object_or_404(Product.objects.select_related('category', 'brand', 'manufacturer', 'distributor'), pk=productId)
    brands = Brand.objects.all().order_by('name')
    manufacturers = Manufacturer.objects.all().order_by('name')
    distributors = Distributor.objects.all().order_by('name')
    categories = Category.objects.filter(parent_category_id=0).order_by('name')

    if request.method == 'GET':
        form_data = {
            'nameTxt': product.name,
            'categorySelect': str(product.category_id or ''),
            'msrpTxt': str(product.msrp or ''),
            'priceTxt': str(product.price or ''),
            'brandSelect': str(product.brand_id or ''),
            'manufacturerSelect': str(product.manufacturer_id or ''),
            'distributorSelect': str(product.distributor_id or ''),
            'unitsTxt': str(product.units if product.units is not None else '0'),
            'dateTxt': product.release_date.strftime('%Y-%m-%d') if product.release_date else '',
            'descriptionTxtArea': product.description,
        }
        form = ProductForm(instance=product)
        return render(request, 'edit_product.html', {
            'product': product,
            'brands': brands,
            'manufacturers': manufacturers,
            'distributors': distributors,
            'categories': categories,
            'form_data': form_data,
            'form': form,
        })

    form_data = {
        'nameTxt': (request.POST.get('nameTxt') or '').strip(),
        'categorySelect': request.POST.get('categorySelect', ''),
        'msrpTxt': request.POST.get('msrpTxt', ''),
        'priceTxt': request.POST.get('priceTxt', ''),
        'brandSelect': request.POST.get('brandSelect', ''),
        'manufacturerSelect': request.POST.get('manufacturerSelect', ''),
        'distributorSelect': request.POST.get('distributorSelect', ''),
        'unitsTxt': request.POST.get('unitsTxt', '0'),
        'dateTxt': request.POST.get('dateTxt', ''),
        'descriptionTxtArea': (request.POST.get('descriptionTxtArea') or '').strip(),
    }

    data = {
        'name': form_data['nameTxt'],
        'category': form_data['categorySelect'],
        'brand': form_data['brandSelect'],
        'manufacturer': form_data['manufacturerSelect'],
        'distributor': form_data['distributorSelect'],
        'description': form_data['descriptionTxtArea'],
        'release_date': form_data['dateTxt'],
        'msrp': form_data['msrpTxt'],
        'price': form_data['priceTxt'],
        'units': form_data['unitsTxt'],
    }

    form = ProductForm(data, request.FILES, instance=product)

    if form.is_valid():
        product = form.save()
        extra_files = request.FILES.getlist('extra_images')
        for f in extra_files:
            ProductImage.objects.create(product=product, image=f)
        if product.category_id is not None:
            features_found = Feature.objects.filter(category_id=product.category_id)
            for feature in features_found:
                feature_value = (request.POST.get('txt_' + str(feature.pk), '') or '').strip()
                if feature_value:
                    FeatureValue.objects.update_or_create(
                        feature_id=feature.pk,
                        product_id=product.pk,
                        defaults={'value': feature_value},
                    )
        messages.success(request, f'Producto "{product.name}" actualizado exitosamente.')
        return redirect('productDetail', productId=product.id)

    errors = []
    for field_errors in form.errors.values():
        for error in field_errors:
            errors.append(error)

    return render(request, 'edit_product.html', {
        'product': product,
        'brands': brands,
        'manufacturers': manufacturers,
        'distributors': distributors,
        'categories': categories,
        'errors': errors,
        'form_data': form_data,
        'form': form,
    })


@user_passes_test(lambda u: u.is_staff, login_url='login')
def DeleteProductImage(request, imageId):
    image = get_object_or_404(ProductImage, pk=imageId)
    product_id = image.product_id
    image.delete()
    messages.success(request, 'Imagen secundaria eliminada exitosamente.')
    return redirect('editProduct', productId=product_id)



@user_passes_test(lambda u: u.is_staff, login_url='login')
def DeleteProduct(request, productId):
    product = get_object_or_404(Product, pk=productId)
    if request.method == 'POST':
        product_name = product.name
        # Guardar snapshot de respaldo antes de archivar
        backup_data = {
            'id': product.id,
            'name': product.name,
            'category': product.category.name if product.category else None,
            'category_id': product.category_id,
            'brand': product.brand.name if product.brand else None,
            'manufacturer': product.manufacturer.name if product.manufacturer else None,
            'distributor': product.distributor.name if product.distributor else None,
            'description': product.description,
            'price': str(product.price),
            'msrp': str(product.msrp) if product.msrp else None,
            'units': product.units,
            'image_url': product.image.url if product.image else None,
            'release_date': str(product.release_date) if product.release_date else None,
        }
        ProductAuditLog.objects.create(
            product_id=product.id,
            product_name=product.name,
            action='soft_deleted',
            user=request.user if request.user.is_authenticated else None,
            backup_data=backup_data,
        )
        product.is_active = False
        product.deleted_at = timezone.now()
        product.save()
        messages.success(request, f'Producto "{product_name}" archivado/retirado del catálogo. Se generó copia de respaldo en auditoría.')
        return redirect('products')
    return render(request, 'delete_product_confirm.html', {'product': product})


@user_passes_test(lambda u: u.is_staff, login_url='login')
def RestoreProduct(request, productId):
    product = get_object_or_404(Product, pk=productId)
    product.is_active = True
    product.deleted_at = None
    product.save()
    ProductAuditLog.objects.create(
        product_id=product.id,
        product_name=product.name,
        action='restored',
        user=request.user if request.user.is_authenticated else None,
        backup_data={'restored_at': str(timezone.now())},
    )
    messages.success(request, f'Producto "{product.name}" restaurado exitosamente en el catálogo.')
    return redirect('productDetail', productId=product.id)


@user_passes_test(lambda u: u.is_staff, login_url='login')
def ArchivedProductsList(request):
    archived_products = Product.objects.filter(is_active=False).select_related('category', 'brand').order_by('-deleted_at')
    audit_logs = ProductAuditLog.objects.select_related('user').order_by('-timestamp')[:30]
    return render(request, 'archived_products.html', {
        'archived_products': archived_products,
        'audit_logs': audit_logs,
    })




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
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'¡Bienvenido(a) a la tienda, {user.first_name or user.username}! Tu cuenta ha sido creada exitosamente.')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('home')
    else:
        form = UserRegistrationForm()

    return render(request, 'register.html', {
        'form': form,
        'next': request.GET.get('next', ''),
    })



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


def CartDetail(request):
    cart = Cart(request)
    return render(request, 'cart_detail.html', {'cart': cart})


def LiveProductSearch(request):
    query = (request.GET.get('q') or '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    products = Product.objects.filter(is_active=True).filter(
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(category__name__icontains=query) |
        Q(brand__name__icontains=query)
    ).select_related('category', 'brand')[:6]

    results = []
    for p in products:
        results.append({
            'id': p.id,
            'name': p.name,
            'price': str(p.price),
            'image': p.image.url if p.image else '',
            'category': p.category.name if p.category else '',
            'brand': p.brand.name if p.brand else '',
            'units': p.units,
            'url': f'/products/detail/{p.id}/',
        })

    return JsonResponse({'results': results})


def CartAdd(request, productId):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=productId)
    quantity = 1
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1
        override = request.POST.get('override', False) in (True, 'True', 'true', '1')
    else:
        override = False

    cart.add(product=product, quantity=quantity, override_quantity=override)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({
            'success': True,
            'message': f'"{product.name}" agregado al carrito.',
            'product_id': product.id,
            'product_name': product.name,
            'product_image': product.image.url if product.image else '',
            'product_price': str(product.price),
            'cart_total_quantity': cart.get_total_quantity(),
            'cart_total_price': str(cart.get_total_price()),
        })

    messages.success(request, f'Se agregó "{product.name}" al carrito.')
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('cartDetail')


def CartRemove(request, productId):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=productId)
    cart.remove(product)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({
            'success': True,
            'product_id': product.id,
            'message': f'"{product.name}" eliminado del carrito.',
            'cart_total_quantity': cart.get_total_quantity(),
            'cart_total_price': str(cart.get_total_price()),
        })

    messages.info(request, f'Se eliminó "{product.name}" del carrito.')
    return redirect('cartDetail')


def CartUpdate(request, productId):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=productId)
    action = request.POST.get('action') or request.GET.get('action')
    if action == 'increment':
        cart.add(product, quantity=1, override_quantity=False)
    elif action == 'decrement':
        cart.decrement(product)
    elif action == 'set':
        try:
            qty = int(request.POST.get('quantity', 1))
            cart.add(product, quantity=qty, override_quantity=True)
        except (ValueError, TypeError):
            pass

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        item_qty = 0
        item_subtotal = '0.00'
        product_id_str = str(product.id)
        if product_id_str in cart.cart:
            item_qty = cart.cart[product_id_str]['quantity']
            item_subtotal = str(Decimal(cart.cart[product_id_str]['price']) * item_qty)
        return JsonResponse({
            'success': True,
            'product_id': product.id,
            'item_quantity': item_qty,
            'item_subtotal': item_subtotal,
            'cart_total_quantity': cart.get_total_quantity(),
            'cart_total_price': str(cart.get_total_price()),
        })

    return redirect('cartDetail')


def CartClear(request):
    cart = Cart(request)
    cart.clear()
    messages.info(request, 'Se ha vaciado el carrito de compras.')
    return redirect('cartDetail')


def ApplyCoupon(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        cart = Cart(request)
        success, message = cart.apply_coupon(code)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'cartDetail'
    return redirect(next_url)


def RemoveCoupon(request):
    if request.method == 'POST':
        cart = Cart(request)
        cart.remove_coupon()
        messages.info(request, 'Cupón removido del carrito.')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'cartDetail'
    return redirect(next_url)



from .payments.gateways import confirm_order_payment, get_gateway_display_info


def OrderCreate(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.warning(request, 'Tu carrito de compras está vacío.')
        return redirect('products')

    last_order = None
    if request.user.is_authenticated:
        last_order = Order.objects.filter(user=request.user).order_by('-created_at').first()

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user

            # Calculate shipping cost based on destination region
            from showcase.shipping.calculator import calculate_shipping
            shipping = calculate_shipping(cart, form.cleaned_data.get('region', ''))
            order.shipping_cost = shipping.price
            order.shipping_courier = shipping.courier
            order.shipping_estimated_days = shipping.days

            # Aplicar cupón de descuento si está activo en el carrito
            coupon = cart.get_coupon()
            discount_amount = cart.get_discount()
            if coupon and discount_amount > Decimal('0.00'):
                order.coupon = coupon
                order.discount_amount = discount_amount
                coupon.used_count += 1
                coupon.save()

            order.total_amount = max(Decimal('0.00'), cart.get_total_price() - discount_amount) + shipping.price

            order.status = 'pending'
            order.paid = False
            order.save()


            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity'],
                )
                product = item['product']
                if product.units >= item['quantity']:
                    product.units -= item['quantity']
                else:
                    product.units = 0
                product.save()

            cart.clear()

            if order.payment_method == 'transfer':
                send_order_confirmation_email(order)
                messages.success(request, f'¡Pedido #{order.id} registrado con éxito! Por favor realiza la transferencia según los datos indicados.')
                return redirect('orderConfirmation', orderId=order.id)
            else:
                return redirect('paymentPortal', orderId=order.id)
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            }
            if last_order:
                initial_data.update({
                    'phone': last_order.phone,
                    'address': last_order.address,
                    'city': last_order.city,
                    'region': last_order.region,
                    'country': last_order.country,
                    'postal_code': last_order.postal_code,
                    'latitude': last_order.latitude,
                    'longitude': last_order.longitude,
                    'payment_method': last_order.payment_method,
                })
        form = OrderCreateForm(initial=initial_data)

    store_settings = StoreSettings.get_solo()
    return render(request, 'order_create.html', {
        'cart': cart,
        'form': form,
        'last_order': last_order,
        'free_shipping_threshold': store_settings.free_shipping_threshold,
    })



def PaymentPortal(request, orderId):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), pk=orderId)
    if order.paid:
        messages.info(request, f'El pedido #{order.id} ya se encuentra pagado.')
        return redirect('orderConfirmation', orderId=order.id)

    gateway_info = get_gateway_display_info(order.payment_method)
    return render(request, 'payments/payment_portal.html', {
        'order': order,
        'gateway_info': gateway_info,
    })


def PaymentProcess(request, orderId):
    import random
    import uuid
    order = get_object_or_404(Order, pk=orderId)
    if order.paid:
        return redirect('orderConfirmation', orderId=order.id)

    if request.method == 'POST':
        action = request.POST.get('action', 'approve')
        card_type = request.POST.get('card_type', 'Visa Crédito')
        card_number = request.POST.get('card_number', '4532 8765 4321 8890')
        installments = request.POST.get('installments', '1')
        gateway = request.POST.get('gateway', order.payment_method)

        if action == 'approve':
            card_last4 = card_number.replace(' ', '')[-4:] if card_number else '8890'
            auth_code = str(random.randint(100000, 999999))
            txn_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"

            confirm_order_payment(
                order=order,
                auth_code=auth_code,
                card_last4=card_last4,
                card_type=card_type,
                installments=installments,
                transaction_id=txn_id,
                gateway_name=gateway
            )
            messages.success(request, f'¡Pago aprobado exitosamente! N° de Autorización: {auth_code}.')
            return redirect('orderConfirmation', orderId=order.id)

        elif action == 'reject':
            reason = request.POST.get('reject_reason', 'Fondos insuficientes o límite excedido')
            messages.error(request, f'Tu transacción no pudo ser autorizada: {reason}.')
            return redirect('paymentFailure', orderId=order.id)

        elif action == 'cancel':
            messages.warning(request, 'Has cancelado el proceso de pago. Puedes reintentar cuando gustes.')
            return redirect('paymentFailure', orderId=order.id)

    return redirect('paymentPortal', orderId=order.id)


def PaymentFailure(request, orderId):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), pk=orderId)
    if order.paid:
        return redirect('orderConfirmation', orderId=order.id)

    return render(request, 'payments/payment_failure.html', {
        'order': order,
    })


def PaymentRetry(request, orderId):
    from .models import PAYMENT_METHOD_CHOICES
    order = get_object_or_404(Order, pk=orderId)
    if order.paid:
        return redirect('orderConfirmation', orderId=order.id)

    if request.method == 'POST':
        new_method = request.POST.get('payment_method')
        valid_methods = [k for k, v in PAYMENT_METHOD_CHOICES]
        if new_method in valid_methods:
            order.payment_method = new_method
            order.save()
            if new_method == 'transfer':
                send_order_confirmation_email(order)
                messages.info(request, 'Se ha seleccionado transferencia bancaria como medio de pago.')
                return redirect('orderConfirmation', orderId=order.id)
            return redirect('paymentPortal', orderId=order.id)

    return redirect('paymentPortal', orderId=order.id)


def OrderConfirmation(request, orderId):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), pk=orderId)
    gateway_info = get_gateway_display_info(order.payment_method)
    return render(request, 'order_confirmation.html', {
        'order': order,
        'gateway_info': gateway_info,
    })



@login_required(login_url='login')
def OrderHistory(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product').order_by('-created_at')
    return render(request, 'order_history.html', {'orders': orders})


@login_required(login_url='login')
def OrderDetail(request, orderId):
    if request.user.is_staff:
        order = get_object_or_404(Order.objects.prefetch_related('items__product'), pk=orderId)
    else:
        order = get_object_or_404(Order.objects.prefetch_related('items__product'), pk=orderId, user=request.user)
    return render(request, 'order_confirmation.html', {'order': order, 'from_history': True})


@user_passes_test(lambda u: u.is_staff, login_url='login')
def ManageOrdersList(request):
    status_filter = request.GET.get('status', 'all')
    search_query = (request.GET.get('q') or '').strip()

    orders_query = Order.objects.prefetch_related('items__product').order_by('-created_at')

    if status_filter in ('pending', 'paid', 'shipped', 'completed', 'cancelled'):
        orders_query = orders_query.filter(status=status_filter)

    if search_query:
        if search_query.isdigit():
            orders_query = orders_query.filter(
                Q(id=int(search_query)) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(tracking_number__icontains=search_query)
            )
        else:
            orders_query = orders_query.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(address__icontains=search_query) |
                Q(city__icontains=search_query) |
                Q(tracking_number__icontains=search_query)
            )

    paginator = Paginator(orders_query, 10)
    page_number = request.GET.get('page')
    page_orders = paginator.get_page(page_number)

    # Metrics
    total_orders = Order.objects.count()
    pending_count = Order.objects.filter(status='pending').count()
    paid_count = Order.objects.filter(status='paid').count()
    shipped_count = Order.objects.filter(status='shipped').count()
    completed_count = Order.objects.filter(status='completed').count()
    cancelled_count = Order.objects.filter(status='cancelled').count()
    total_revenue = Order.objects.filter(paid=True).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')

    return render(request, 'manage_orders.html', {
        'orders': page_orders,
        'status_filter': status_filter,
        'search_query': search_query,
        'total_orders': total_orders,
        'pending_count': pending_count,
        'paid_count': paid_count,
        'shipped_count': shipped_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'total_revenue': total_revenue,
    })


@user_passes_test(lambda u: u.is_staff, login_url='login')
def ManageOrderDetail(request, orderId):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), pk=orderId)
    return render(request, 'manage_order_detail.html', {
        'order': order,
    })


@user_passes_test(lambda u: u.is_staff, login_url='login')
def ManageOrderUpdateStatus(request, orderId):
    order = get_object_or_404(Order, pk=orderId)
    if request.method == 'POST':
        old_status = order.status
        new_status = request.POST.get('status')
        if new_status in dict(Order._meta.get_field('status').choices):
            order.status = new_status

        order.paid = request.POST.get('paid') in ('true', 'True', '1', 'on', True)
        if 'phone' in request.POST:
            order.phone = (request.POST.get('phone') or '').strip()
        order.tracking_company = (request.POST.get('tracking_company') or '').strip()
        order.tracking_number = (request.POST.get('tracking_number') or '').strip()
        order.notes = (request.POST.get('notes') or '').strip()

        try:
            order.save()
            messages.success(request, f'Orden #{order.id} actualizada exitosamente a "{order.get_status_display()}".')

            # Enviar correo si el estado cambió a despachado/entregado o si se solicitó explícitamente
            should_notify = request.POST.get('notify_email') == 'on' or (
                old_status != new_status and new_status in ('shipped', 'delivered')
            )
            if should_notify:
                sent = send_dispatch_notification_email(order)
                if sent:
                    messages.info(request, f'📧 Notificación de despacho enviada a {order.email}.')

        except ValidationError as e:
            error_msg = '; '.join(sum(e.message_dict.values(), [])) if hasattr(e, 'message_dict') else str(e)
            messages.error(request, f'No se pudo actualizar la orden #{order.id}: {error_msg}')

        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('manageOrderDetail', orderId=order.id)

    return redirect('manageOrderDetail', orderId=order.id)







@user_passes_test(lambda u: u.is_staff, login_url="login")
def ManageAnalyticsDashboard(request):
    now = timezone.now()
    today = now.date()
    twelve_months_ago = now - timedelta(days=365)
    thirty_days_ago = now - timedelta(days=30)

    # KPIs
    total_orders = Order.objects.count()
    paid_orders = Order.objects.filter(paid=True)
    total_revenue = paid_orders.aggregate(t=Sum("total_amount"))["t"] or Decimal("0.00")
    completed_count = Order.objects.filter(status="completed").count()
    pending_count = Order.objects.filter(status="pending").count()
    orders_today = Order.objects.filter(created_at__date=today).count()
    paid_count = paid_orders.count()
    avg_ticket = (total_revenue / paid_count) if paid_count > 0 else Decimal("0.00")

    # Ventas mensuales (últimos 12 meses)
    monthly_qs = (
        Order.objects
        .filter(paid=True, created_at__gte=twelve_months_ago)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("total_amount"), count=Count("id"))
        .order_by("month")
    )
    monthly_labels = [item["month"].strftime("%b %Y") for item in monthly_qs]
    monthly_revenue = [float(item["total"]) for item in monthly_qs]
    monthly_counts = [item["count"] for item in monthly_qs]

    # Pedidos diarios (últimos 30 días)
    daily_qs = (
        Order.objects
        .filter(created_at__date__gte=thirty_days_ago)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    daily_labels = [item["day"].strftime("%d/%m") for item in daily_qs]
    daily_counts = [item["count"] for item in daily_qs]

    # Distribución de estados
    status_qs = (
        Order.objects
        .values("status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    status_display = {
        "pending": "Pendiente",
        "paid": "Pagada/Preparación",
        "shipped": "En Camino",
        "completed": "Completada",
        "cancelled": "Cancelada",
    }
    status_labels = [status_display.get(s["status"], s["status"]) for s in status_qs]
    status_counts = [s["count"] for s in status_qs]

    # Métodos de pago
    payment_qs = (
        Order.objects
        .filter(paid=True)
        .values("payment_method")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    payment_display = {
        "webpay": "Webpay Plus",
        "mercadopago": "Mercado Pago",
        "sandbox_card": "Tarjeta Directa",
        "transfer": "Transferencia",
    }
    payment_labels = [payment_display.get(p["payment_method"], p["payment_method"]) for p in payment_qs]
    payment_counts = [p["count"] for p in payment_qs]

    # Top 5 productos más vendidos
    top_products_qs = (
        OrderItem.objects
        .values("product__name")
        .annotate(total_qty=Sum("quantity"), total_revenue=Sum("price"))
        .order_by("-total_qty")[:5]
    )
    top_product_labels = [p["product__name"] or "Producto retirado" for p in top_products_qs]
    top_product_qty = [p["total_qty"] for p in top_products_qs]

    # Ingresos por categoría
    category_qs = (
        OrderItem.objects
        .filter(order__paid=True)
        .values("product__category__name")
        .annotate(revenue=Sum("price"))
        .order_by("-revenue")[:6]
    )
    category_labels = [c["product__category__name"] or "Sin categoría" for c in category_qs]
    category_revenue = [float(c["revenue"]) for c in category_qs]

    # Stock crítico
    low_stock_products = (
        Product.objects
        .filter(is_active=True, units__lte=5)
        .select_related("category")
        .order_by("units")[:10]
    )

    # Últimas 5 órdenes
    recent_orders = (
        Order.objects
        .prefetch_related("items")
        .order_by("-created_at")[:5]
    )

    context = {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "completed_count": completed_count,
        "pending_count": pending_count,
        "orders_today": orders_today,
        "avg_ticket": avg_ticket,
        "monthly_labels_json": json.dumps(monthly_labels),
        "monthly_revenue_json": json.dumps(monthly_revenue),
        "monthly_counts_json": json.dumps(monthly_counts),
        "daily_labels_json": json.dumps(daily_labels),
        "daily_counts_json": json.dumps(daily_counts),
        "status_labels_json": json.dumps(status_labels),
        "status_counts_json": json.dumps(status_counts),
        "payment_labels_json": json.dumps(payment_labels),
        "payment_counts_json": json.dumps(payment_counts),
        "top_product_labels_json": json.dumps(top_product_labels),
        "top_product_qty_json": json.dumps(top_product_qty),
        "category_labels_json": json.dumps(category_labels),
        "category_revenue_json": json.dumps(category_revenue),
        "low_stock_products": low_stock_products,
        "recent_orders": recent_orders,
        "now": now,
    }
    return render(request, "analytics_dashboard.html", context)


@user_passes_test(lambda u: u.is_staff, login_url="login")
def ManageAnalyticsExportCSV(request):
    now = timezone.now()
    twelve_months_ago = now - timedelta(days=365)

    monthly_qs = (
        Order.objects
        .filter(paid=True, created_at__gte=twelve_months_ago)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("total_amount"), count=Count("id"))
        .order_by("month")
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=ventas_mensuales.csv"

    writer = csv.writer(response)
    writer.writerow(["Mes", "Ingresos (CLP)", "Numero de Pedidos"])
    for row in monthly_qs:
        writer.writerow([
            row["month"].strftime("%B %Y"),
            "{:.2f}".format(float(row["total"])),
            row["count"],
        ])

    return response


def ShippingQuote(request):
    """AJAX endpoint — returns shipping cost JSON for a given region and cart."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    region = request.GET.get('region', '')
    cart = Cart(request)
    if not cart:
        return JsonResponse({'price': 0, 'courier': '', 'days': '', 'is_free': False})
    from showcase.shipping.calculator import calculate_shipping
    result = calculate_shipping(cart, region)
    return JsonResponse(result.to_dict())


@user_passes_test(lambda u: u.is_staff, login_url='login')
def ManageSettings(request):
    """Admin panel to configure global store settings and shipping rates."""
    settings = StoreSettings.get_solo()
    shipping_rates = ShippingRate.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action', 'settings')

        if action == 'settings':
            settings.store_name = request.POST.get('store_name', settings.store_name).strip() or settings.store_name
            settings.store_email = request.POST.get('store_email', '').strip()
            settings.store_phone = request.POST.get('store_phone', '').strip()
            settings.origin_commune = request.POST.get('origin_commune', settings.origin_commune).strip() or settings.origin_commune
            settings.origin_address = request.POST.get('origin_address', '').strip()
            threshold_raw = request.POST.get('free_shipping_threshold', '').strip()
            if threshold_raw:
                try:
                    settings.free_shipping_threshold = Decimal(threshold_raw.replace(',', '.'))
                except Exception:
                    pass
            settings.shipit_email = request.POST.get('shipit_email', '').strip()
            settings.shipit_token = request.POST.get('shipit_token', '').strip()
            settings.shipit_enabled = request.POST.get('shipit_enabled') == 'on'

            # Branding y Personalización de Marca
            if 'site_logo' in request.FILES:
                settings.site_logo = request.FILES['site_logo']
            if 'site_favicon' in request.FILES:
                settings.site_favicon = request.FILES['site_favicon']
            if 'footer_text' in request.POST:
                settings.footer_text = request.POST.get('footer_text', settings.footer_text).strip()

            # Banners del Carrusel
            settings.banner1_title = request.POST.get('banner1_title', settings.banner1_title).strip()
            settings.banner1_subtitle = request.POST.get('banner1_subtitle', settings.banner1_subtitle).strip()
            settings.banner1_bg_color = request.POST.get('banner1_bg_color', settings.banner1_bg_color).strip()

            settings.banner2_title = request.POST.get('banner2_title', settings.banner2_title).strip()
            settings.banner2_subtitle = request.POST.get('banner2_subtitle', settings.banner2_subtitle).strip()
            settings.banner2_bg_color = request.POST.get('banner2_bg_color', settings.banner2_bg_color).strip()

            settings.banner3_title = request.POST.get('banner3_title', settings.banner3_title).strip()
            settings.banner3_subtitle = request.POST.get('banner3_subtitle', settings.banner3_subtitle).strip()
            settings.banner3_bg_color = request.POST.get('banner3_bg_color', settings.banner3_bg_color).strip()

            settings.enable_live_sales_notifications = request.POST.get('enable_live_sales_notifications') == 'on'

            # WhatsApp Live Support Widget
            if 'whatsapp_number' in request.POST:
                settings.whatsapp_number = request.POST.get('whatsapp_number', settings.whatsapp_number).strip()
            if 'whatsapp_default_message' in request.POST:
                settings.whatsapp_default_message = request.POST.get('whatsapp_default_message', settings.whatsapp_default_message).strip()
            settings.enable_whatsapp_widget = request.POST.get('enable_whatsapp_widget') == 'on'

            settings.save()
            messages.success(request, 'Configuración y personalización de marca guardadas exitosamente.')




        elif action == 'add_rate':
            try:
                ShippingRate.objects.create(
                    region=request.POST.get('region', '').strip(),
                    weight_min_kg=Decimal(request.POST.get('weight_min_kg', '0').replace(',', '.')),
                    weight_max_kg=Decimal(request.POST.get('weight_max_kg', '5').replace(',', '.')),
                    price=Decimal(request.POST.get('price', '0').replace(',', '.')),
                    courier_name=request.POST.get('courier_name', 'Starken').strip(),
                    estimated_days=request.POST.get('estimated_days', '3-5 días hábiles').strip(),
                    is_active=request.POST.get('is_active') != 'off',
                )
                messages.success(request, 'Tarifa de envío añadida.')
            except Exception as e:
                messages.error(request, f'Error al añadir tarifa: {e}')

        elif action == 'delete_rate':
            rate_id = request.POST.get('rate_id')
            ShippingRate.objects.filter(pk=rate_id).delete()
            messages.success(request, 'Tarifa eliminada.')

        return redirect('manageSettings')

    return render(request, 'manage_settings.html', {
        'store_settings': settings,
        'shipping_rates': shipping_rates,
    })


@user_passes_test(lambda u: u.is_staff, login_url='login')
def ManageCoupons(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            code = request.POST.get('code', '').strip().upper()
            discount_type = request.POST.get('discount_type', 'percentage')
            discount_value = Decimal(request.POST.get('discount_value', '0.00') or '0.00')
            min_purchase_amount = Decimal(request.POST.get('min_purchase_amount', '0.00') or '0.00')
            max_uses_raw = request.POST.get('max_uses', '').strip()
            max_uses = int(max_uses_raw) if max_uses_raw.isdigit() else None
            is_active = request.POST.get('is_active') == 'on'

            if not code or discount_value <= Decimal('0.00'):
                messages.error(request, 'El código y el valor del descuento deben ser válidos.')
            else:
                try:
                    Coupon.objects.create(
                        code=code,
                        discount_type=discount_type,
                        discount_value=discount_value,
                        min_purchase_amount=min_purchase_amount,
                        max_uses=max_uses,
                        is_active=is_active,
                    )
                    messages.success(request, f'Cupón "{code}" creado exitosamente.')
                except Exception as e:
                    messages.error(request, f'Error al crear el cupón: {e}')

        elif action == 'toggle_active':
            coupon_id = request.POST.get('coupon_id')
            coupon = get_object_or_404(Coupon, pk=coupon_id)
            coupon.is_active = not coupon.is_active
            coupon.save()
            state_str = 'activado' if coupon.is_active else 'desactivado'
            messages.info(request, f'Cupón "{coupon.code}" {state_str}.')

        elif action == 'delete':
            coupon_id = request.POST.get('coupon_id')
            coupon = get_object_or_404(Coupon, pk=coupon_id)
            code_str = coupon.code
            coupon.delete()
            messages.success(request, f'Cupón "{code_str}" eliminado exitosamente.')

        return redirect('manageCoupons')

    coupons = Coupon.objects.all()
    return render(request, 'manage_coupons.html', {
        'coupons': coupons,
    })


def RecentSalesNotificationAPI(request):
    """
    API endpoint que retorna un listado en JSON de las compras recientes
    realizadas en la tienda para alimentar los avisos emergentes (toasts).
    """
    settings = StoreSettings.get_solo()
    if not settings.enable_live_sales_notifications:
        return JsonResponse({'enabled': False, 'notifications': []})

    from django.urls import reverse

    recent_items = (
        OrderItem.objects
        .select_related('order', 'product')
        .filter(order__paid=True, product__is_active=True, product__deleted_at__isnull=True)
        .order_by('-order__created_at')[:10]
    )

    notifications = []
    now = timezone.now()

    for item in recent_items:
        order = item.order
        product = item.product
        if not product:
            continue

        first_name = (order.first_name or 'Cliente').strip()
        last_initial = order.last_name[0].upper() + '.' if order.last_name else ''
        buyer_display = f"{first_name} {last_initial}".strip()
        city_display = order.city or 'Pichidegua'

        diff = now - order.created_at
        if diff.total_seconds() < 3600:
            mins = max(1, int(diff.total_seconds() // 60))
            time_ago = f"hace {mins} min"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() // 3600)
            time_ago = f"hace {hours} h"
        else:
            days = int(diff.total_seconds() // 86400)
            time_ago = f"hace {days} d"

        image_url = product.image.url if product.image else None

        notifications.append({
            'buyer_name': buyer_display,
            'city': city_display,
            'product_name': product.name,
            'product_url': reverse('productDetail', kwargs={'productId': product.id}),
            'product_image': image_url,
            'time_ago': time_ago,
        })

    return JsonResponse({'enabled': True, 'notifications': notifications})


def ManifestJSON(request):
    """
    Retorna el archivo manifest.json para habilitar la instalación PWA.
    """
    settings = StoreSettings.get_solo()
    store_name = settings.store_name or 'Store Django'

    logo_url = settings.site_logo.url if settings.site_logo else '/static/images/logo_icon.png'

    manifest_data = {
        "name": store_name,
        "short_name": store_name[:12],
        "description": settings.footer_text or "Tienda en línea con despacho y seguimiento",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#007bff",
        "icons": [
            {
                "src": logo_url,
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": logo_url,
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    return JsonResponse(manifest_data)


def ServiceWorkerJS(request):
    """
    Retorna el JavaScript del Service Worker para almacenamiento en caché y offline PWA.
    """
    sw_code = """
const CACHE_NAME = 'store-django-pwa-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/offline/',
  'https://cdn.jsdelivr.net/npm/bootstrap@4.3.1/dist/css/bootstrap.min.css',
  'https://code.jquery.com/jquery-3.3.1.min.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match('/offline/');
      })
    );
  } else {
    event.respondWith(
      caches.match(event.request).then((cachedResponse) => {
        return cachedResponse || fetch(event.request);
      })
    );
  }
});
"""
    response = HttpResponse(sw_code.strip(), content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response


def OfflinePage(request):
    """
    Página de contingencia mostrada cuando el usuario está sin conexión.
    """
    return render(request, 'offline.html')



