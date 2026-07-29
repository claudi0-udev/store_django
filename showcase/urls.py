from django.urls import path
from .views import HelloWorld, HomePage, ListProducts, ProductDetail, AddNewProduct, GetSubcategories, GetFeatures, AddCategory, GetCategories, GetBrands, GetManufacturers, GetDistributors, AddBrand, AddDistributor, AddManufacturer, AddFeature, Register

urlpatterns = [
    path('', HomePage, name='home'),
    path('hello-world/', HelloWorld),
    path('products/', ListProducts, name='products'),
    path('products/detail/<int:productId>', ProductDetail, name='productDetail'),
    path('products/new', AddNewProduct, name='addProduct'),
    path('products/get_categories/', GetCategories, name='getCategories'),
    path('products/get_brands/', GetBrands, name='getBrands'),
    path('products/get_manufacturers/', GetManufacturers, name='getManufacturers'),
    path('products/get_distributors/', GetDistributors, name='getDistributors'),
    path('products/get_subcategory/<int:categoryID>', GetSubcategories, name='getCategoryById'),
    path('products/get_features/<int:categoryID>', GetFeatures, name='getFeatures'),
    path('products/add_category/', AddCategory, name='addCategory'),
    path('products/add_brand/', AddBrand, name='addBrand'),
    path('products/add_manufacturer/', AddManufacturer, name='addManufacturer'),
    path('products/add_distributor/', AddDistributor, name='addDistributor'),
    path('products/add_feature/', AddFeature, name='addFeature'),
    path('accounts/register/', Register, name='register'),
]