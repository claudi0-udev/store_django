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
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone


from .cart import Cart
from .emails import send_order_confirmation_email
from .forms import OrderCreateForm, ProductForm, UserLoginForm, UserRegistrationForm


from .models import (
    Brand,
    Category,
    Distributor,
    Feature,
    FeatureValue,
    Manufacturer,
    Order,
    OrderItem,
    Product,
    ProductAuditLog,
    ShippingRate,
    StoreSettings,
)




def HelloWorld(request):
    return HttpResponse('<h2>Hello World!</h2>')


def HomePage(request):
    featured_products = Product.objects.filter(is_active=True).select_related('category', 'brand', 'manufacturer', 'distributor').order_by('-id')[:6]
    best_selling_products = Product.objects.filter(is_active=True).select_related('category').order_by('-units')[:4]
    new_products = Product.objects.filter(is_active=True).select_related('category').order_by('-id')[:4]
    categories = Category.objects.order_by('name')[:8]

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

    if ordering in {'-id', 'id', '-price', 'price', '-units', 'units'}:
        products_query = products_query.order_by(ordering)
    else:
        products_query = products_query.order_by('-id')

    products = products_query[:8]

    return render(request, 'home.html', {
        'featured_products': featured_products,
        'best_selling_products': best_selling_products,
        'new_products': new_products,
        'categories': categories,
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

    category = Category.objects.filter(id=product.category_id)
    feature_values = FeatureValue.objects.filter(product_id=productId).select_related('feature')

    # Productos relacionados (Cross-selling)
    related_qs = Product.objects.filter(is_active=True, category=product.category).exclude(id=product.id)[:4]
    related_products = list(related_qs)
    if len(related_products) < 4:
        extra_needed = 4 - len(related_products)
        excluded_ids = [product.id] + [p.id for p in related_products]
        extra_qs = Product.objects.filter(is_active=True).exclude(id__in=excluded_ids)[:extra_needed]
        related_products.extend(list(extra_qs))

    return render(request, 'product_detail.html', {
        'product': product,
        'category': category,
        'featureValues': feature_values,
        'related_products': related_products,
    })




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
            order.total_amount = cart.get_total_price() + shipping.price

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
            settings.save()
            messages.success(request, 'Configuración guardada exitosamente.')

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
