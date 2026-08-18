from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q, Sum
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
)




def HelloWorld(request):
    return HttpResponse('<h2>Hello World!</h2>')


def HomePage(request):
    featured_products = Product.objects.filter(is_active=True).select_related('category', 'brand', 'manufacturer', 'distributor').order_by('-id')[:6]
    best_selling_products = Product.objects.filter(is_active=True).select_related('category').order_by('-units')[:4]
    new_products = Product.objects.filter(is_active=True).select_related('category').order_by('-id')[:4]
    categories = Category.objects.order_by('name')[:8]

    search_query = (request.GET.get('q') or '').strip()
    category_id = request.GET.get('category')
    ordering = request.GET.get('ordering') or '-id'

    products_query = Product.objects.filter(is_active=True).select_related('category', 'brand', 'manufacturer', 'distributor')

    if search_query:
        products_query = products_query.filter(name__icontains=search_query)

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
    if show_archived:
        products = Product.objects.filter(is_active=False).select_related('category', 'brand', 'manufacturer', 'distributor').order_by('-deleted_at')
    else:
        products = Product.objects.filter(is_active=True).select_related('category', 'brand', 'manufacturer', 'distributor').order_by('-id')

    paginator = Paginator(products, 5)
    page_number = request.GET.get('page')
    page_products = paginator.get_page(page_number)
    archived_count = Product.objects.filter(is_active=False).count() if is_staff else 0

    return render(request, 'products_list.html', {
        'products': page_products,
        'show_archived': show_archived,
        'archived_count': archived_count,
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
    messages.success(request, f'Se agregó "{product.name}" al carrito.')

    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('cartDetail')


def CartRemove(request, productId):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=productId)
    cart.remove(product)
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
    return redirect('cartDetail')


def CartClear(request):
    cart = Cart(request)
    cart.clear()
    messages.info(request, 'Se ha vaciado el carrito de compras.')
    return redirect('cartDetail')


def OrderCreate(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.warning(request, 'Tu carrito de compras está vacío.')
        return redirect('products')

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            order.total_amount = cart.get_total_price()
            order.status = 'paid'
            order.paid = True
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
            send_order_confirmation_email(order)
            messages.success(request, f'¡Pedido #{order.id} realizado con éxito! Te enviamos un correo de confirmación con el detalle a {order.email}.')
            return redirect('orderConfirmation', orderId=order.id)
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            }
        form = OrderCreateForm(initial=initial_data)

    return render(request, 'order_create.html', {
        'cart': cart,
        'form': form,
    })


def OrderConfirmation(request, orderId):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), pk=orderId)
    return render(request, 'order_confirmation.html', {'order': order})


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




