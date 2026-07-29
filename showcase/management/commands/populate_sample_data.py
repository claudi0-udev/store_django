from django.core.management.base import BaseCommand
from django.utils import timezone
from showcase.models import (
    Brand,
    Category,
    Distributor,
    Feature,
    FeatureValue,
    Manufacturer,
    Product,
)


class Command(BaseCommand):
    help = "Populate the database with realistic sample data for an online store"

    def handle(self, *args, **options):
        self.stdout.write("Creating sample store data...")

        brands = {
            "Apple": Brand.objects.get_or_create(name="Apple")[0],
            "Samsung": Brand.objects.get_or_create(name="Samsung")[0],
            "Sony": Brand.objects.get_or_create(name="Sony")[0],
            "Philips": Brand.objects.get_or_create(name="Philips")[0],
            "Nike": Brand.objects.get_or_create(name="Nike")[0],
        }

        manufacturers = {
            "Apple Inc.": Manufacturer.objects.get_or_create(name="Apple Inc.")[0],
            "Samsung Electronics": Manufacturer.objects.get_or_create(name="Samsung Electronics")[0],
            "Sony Corporation": Manufacturer.objects.get_or_create(name="Sony Corporation")[0],
            "Philips": Manufacturer.objects.get_or_create(name="Philips")[0],
            "Nike, Inc.": Manufacturer.objects.get_or_create(name="Nike, Inc.")[0],
        }

        distributors = {
            "TechDistribution": Distributor.objects.get_or_create(name="TechDistribution")[0],
            "Global Retail Co.": Distributor.objects.get_or_create(name="Global Retail Co.")[0],
            "Prime Supply": Distributor.objects.get_or_create(name="Prime Supply")[0],
            "SportLine": Distributor.objects.get_or_create(name="SportLine")[0],
        }

        categories = {}
        root_categories = [
            ("Electrónica", 0),
            ("Ropa", 0),
            ("Hogar", 0),
        ]
        for name, parent_id in root_categories:
            category, _ = Category.objects.get_or_create(name=name, parent_category_id=parent_id)
            categories[name] = category

        subcategories = [
            ("Celulares", categories["Electrónica"].id),
            ("Laptops", categories["Electrónica"].id),
            ("Auriculares", categories["Electrónica"].id),
            ("Zapatillas", categories["Ropa"].id),
            ("Cafeteras", categories["Hogar"].id),
        ]
        for name, parent_id in subcategories:
            category, _ = Category.objects.get_or_create(name=name, parent_category_id=parent_id)
            categories[name] = category

        feature_map = {}
        feature_definitions = [
            (categories["Celulares"], "Color"),
            (categories["Celulares"], "Almacenamiento"),
            (categories["Celulares"], "Batería"),
            (categories["Laptops"], "Procesador"),
            (categories["Laptops"], "Memoria RAM"),
            (categories["Auriculares"], "Conectividad"),
            (categories["Auriculares"], "Cancelación de ruido"),
            (categories["Zapatillas"], "Talla"),
            (categories["Zapatillas"], "Material"),
            (categories["Cafeteras"], "Capacidad"),
            (categories["Cafeteras"], "Tipo de filtro"),
        ]
        for category, feature_name in feature_definitions:
            feature, _ = Feature.objects.get_or_create(name=feature_name, category=category)
            feature_map[(category.id, feature_name)] = feature

        product_data = [
            {
                "name": "iPhone 15 Pro",
                "category": categories["Celulares"],
                "brand": brands["Apple"],
                "manufacturer": manufacturers["Apple Inc."],
                "distributor": distributors["TechDistribution"],
                "description": "Smartphone premium con cámara avanzada, pantalla OLED y rendimiento de alto nivel para uso diario y creativo.",
                "release_date": timezone.now().date().replace(year=timezone.now().year - 1),
                "msrp": 1299,
                "price": 1199,
                "units": 25,
                "features": {
                    "Color": "Titanio natural",
                    "Almacenamiento": "256 GB",
                    "Batería": "Hasta 23 horas",
                },
            },
            {
                "name": "Galaxy S24 Ultra",
                "category": categories["Celulares"],
                "brand": brands["Samsung"],
                "manufacturer": manufacturers["Samsung Electronics"],
                "distributor": distributors["Global Retail Co."],
                "description": "Teléfono Android de gama alta con pantalla grande, cámara versátil y excelente experiencia multimedia.",
                "release_date": timezone.now().date().replace(year=timezone.now().year - 1),
                "msrp": 1399,
                "price": 1299,
                "units": 18,
                "features": {
                    "Color": "Negro",
                    "Almacenamiento": "512 GB",
                    "Batería": "Hasta 21 horas",
                },
            },
            {
                "name": "MacBook Air M2",
                "category": categories["Laptops"],
                "brand": brands["Apple"],
                "manufacturer": manufacturers["Apple Inc."],
                "distributor": distributors["Prime Supply"],
                "description": "Laptop ultraligera con chip M2, ideal para trabajo, estudio y navegación intensiva.",
                "release_date": timezone.now().date().replace(year=timezone.now().year - 2),
                "msrp": 1499,
                "price": 1399,
                "units": 12,
                "features": {
                    "Procesador": "Apple M2",
                    "Memoria RAM": "16 GB",
                },
            },
            {
                "name": "WH-1000XM5",
                "category": categories["Auriculares"],
                "brand": brands["Sony"],
                "manufacturer": manufacturers["Sony Corporation"],
                "distributor": distributors["TechDistribution"],
                "description": "Auriculares premium con cancelación de ruido activa y sonido envolvente para viajes y trabajo.",
                "release_date": timezone.now().date().replace(year=timezone.now().year - 1),
                "msrp": 399,
                "price": 349,
                "units": 30,
                "features": {
                    "Conectividad": "Bluetooth 5.3",
                    "Cancelación de ruido": "Activa",
                },
            },
            {
                "name": "Air Zoom Pegasus 40",
                "category": categories["Zapatillas"],
                "brand": brands["Nike"],
                "manufacturer": manufacturers["Nike, Inc."],
                "distributor": distributors["SportLine"],
                "description": "Zapatillas deportivas con amortiguación ligera y diseño versátil para entrenar o moverte con comodidad.",
                "release_date": timezone.now().date().replace(year=timezone.now().year - 1),
                "msrp": 129,
                "price": 109,
                "units": 40,
                "features": {
                    "Talla": "42",
                    "Material": "Mesh y espuma EVA",
                },
            },
            {
                "name": "Cafetera Philips 3200",
                "category": categories["Cafeteras"],
                "brand": brands["Philips"],
                "manufacturer": manufacturers["Philips"],
                "distributor": distributors["Global Retail Co."],
                "description": "Cafetera automática con molinillo integrado y varios modos de preparación para cada preferencia.",
                "release_date": timezone.now().date().replace(year=timezone.now().year - 2),
                "msrp": 599,
                "price": 549,
                "units": 15,
                "features": {
                    "Capacidad": "1.8 litros",
                    "Tipo de filtro": "Cápsulas compatibles",
                },
            },
        ]

        for item in product_data:
            product, created = Product.objects.get_or_create(
                name=item["name"],
                defaults={
                    "category": item["category"],
                    "brand": item["brand"],
                    "description": item["description"],
                    "manufacturer": item["manufacturer"],
                    "distributor": item["distributor"],
                    "release_date": item["release_date"],
                    "msrp": item["msrp"],
                    "price": item["price"],
                    "units": item["units"],
                },
            )
            if created:
                for feature_name, value in item["features"].items():
                    feature = feature_map[(item["category"].id, feature_name)]
                    FeatureValue.objects.get_or_create(
                        feature=feature,
                        product=product,
                        defaults={"value": value},
                    )

        self.stdout.write(self.style.SUCCESS("Sample data created successfully."))
