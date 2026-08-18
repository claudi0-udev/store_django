from django.contrib import admin
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


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'phone', 'city', 'paid', 'status', 'tracking_company', 'tracking_number', 'total_amount', 'created_at']
    list_filter = ['paid', 'status', 'created_at', 'tracking_company']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'tracking_number']
    list_editable = ['status', 'paid']
    inlines = [OrderItemInline]
    actions = ['mark_as_shipped', 'mark_as_completed']

    def mark_as_shipped(self, request, queryset):
        count = queryset.update(status='shipped')
        self.message_user(request, f'{count} orden(es) marcadas como enviadas.')
    mark_as_shipped.short_description = 'Marcar órdenes seleccionadas como Enviadas'

    def mark_as_completed(self, request, queryset):
        count = queryset.update(status='completed')
        self.message_user(request, f'{count} orden(es) marcadas como completadas.')
    mark_as_completed.short_description = 'Marcar órdenes seleccionadas como Completadas'



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'category', 'price', 'units', 'is_active', 'deleted_at']
    list_filter = ['is_active', 'category', 'brand']
    search_fields = ['name', 'description']
    actions = ['restore_products', 'soft_delete_products']

    def restore_products(self, request, queryset):
        count = queryset.update(is_active=True, deleted_at=None)
        self.message_user(request, f'{count} producto(s) restaurado(s) exitosamente.')
    restore_products.short_description = 'Restaurar productos seleccionados (Reactivar)'

    def soft_delete_products(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} producto(s) archivado(s)/desactivado(s).')
    soft_delete_products.short_description = 'Archivar productos seleccionados (Soft Delete)'


@admin.register(ProductAuditLog)
class ProductAuditLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'product_id', 'product_name', 'action', 'user', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['product_name', 'product_id']
    readonly_fields = ['product_id', 'product_name', 'action', 'user', 'timestamp', 'backup_data']


admin.site.register(Feature)
admin.site.register(FeatureValue)
admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(Manufacturer)
admin.site.register(Distributor)


