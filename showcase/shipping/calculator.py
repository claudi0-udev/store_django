from decimal import Decimal
from .shipit import quote_shipit


# Region keyword matching map — normalize region strings from geocoding
REGION_MAP = [
    ("Metropolitana",         "Región Metropolitana"),
    ("Valparaíso",            "Valparaíso"),
    ("Viña del Mar",          "Valparaíso"),
    ("O'Higgins",             "O'Higgins"),
    ("Rancagua",              "O'Higgins"),
    ("Maule",                 "Maule"),
    ("Ñuble",                 "Ñuble"),
    ("Biobío",                "Biobío"),
    ("Concepción",            "Biobío"),
    ("Araucanía",             "La Araucanía"),
    ("Los Ríos",              "Los Ríos"),
    ("Los Lagos",             "Los Lagos"),
    ("Aysén",                 "Aysén"),
    ("Magallanes",            "Magallanes"),
    ("Atacama",               "Atacama"),
    ("Coquimbo",              "Coquimbo"),
    ("Antofagasta",           "Antofagasta"),
    ("Tarapacá",              "Tarapacá"),
    ("Arica",                 "Arica y Parinacota"),
]

# Default internal rate table — used as fallback if no DB rates found
DEFAULT_RATES = {
    "Región Metropolitana": [(5,   3490, "Starken",      "2-3 días hábiles"),
                              (15,  4990, "Starken",      "2-3 días hábiles"),
                              (30,  6990, "Starken",      "2-3 días hábiles"),
                              (999, 8990, "Starken",      "3-5 días hábiles")],
    "Valparaíso":           [(5,   3990, "Starken",      "2-4 días hábiles"),
                              (15,  5490, "Starken",      "2-4 días hábiles"),
                              (30,  7490, "Starken",      "3-5 días hábiles"),
                              (999, 9490, "Starken",      "3-5 días hábiles")],
    "O'Higgins":            [(5,   3990, "Starken",      "2-4 días hábiles"),
                              (15,  5490, "Starken",      "2-4 días hábiles"),
                              (30,  7490, "Starken",      "3-5 días hábiles"),
                              (999, 9490, "Starken",      "3-5 días hábiles")],
    "Maule":                 [(5,   4490, "Starken",      "3-5 días hábiles"),
                              (15,  5990, "Starken",      "3-5 días hábiles"),
                              (30,  7990, "Starken",      "4-6 días hábiles"),
                              (999, 9990, "Starken",      "4-6 días hábiles")],
    "Ñuble":                 [(5,   4490, "Starken",      "3-5 días hábiles"),
                              (15,  5990, "Starken",      "3-5 días hábiles"),
                              (30,  7990, "Starken",      "4-6 días hábiles"),
                              (999, 9990, "Starken",      "4-6 días hábiles")],
    "Biobío":               [(5,   4490, "Starken",      "3-5 días hábiles"),
                              (15,  5990, "Starken",      "3-5 días hábiles"),
                              (30,  7990, "Starken",      "4-6 días hábiles"),
                              (999, 9990, "Starken",      "4-6 días hábiles")],
    "La Araucanía":          [(5,   4990, "Blue Express", "4-6 días hábiles"),
                              (15,  6990, "Blue Express", "4-6 días hábiles"),
                              (30,  8990, "Blue Express", "5-7 días hábiles"),
                              (999,10990, "Blue Express", "5-7 días hábiles")],
    "Los Ríos":              [(5,   5490, "Blue Express", "4-7 días hábiles"),
                              (15,  7490, "Blue Express", "4-7 días hábiles"),
                              (30,  9990, "Blue Express", "5-8 días hábiles"),
                              (999,11990, "Blue Express", "5-8 días hábiles")],
    "Los Lagos":             [(5,   5490, "Blue Express", "4-7 días hábiles"),
                              (15,  7490, "Blue Express", "4-7 días hábiles"),
                              (30,  9990, "Blue Express", "5-8 días hábiles"),
                              (999,11990, "Blue Express", "5-8 días hábiles")],
    "default":               [(5,   5990, "Blue Express", "5-8 días hábiles"),
                              (15,  7990, "Blue Express", "5-8 días hábiles"),
                              (30, 10990, "Blue Express", "6-9 días hábiles"),
                              (999,12990, "Blue Express", "6-9 días hábiles")],
}


class ShippingResult:
    def __init__(self, price, courier, days, source="internal", is_free=False):
        self.price = Decimal(str(price))
        self.courier = courier
        self.days = days
        self.source = source
        self.is_free = is_free

    def to_dict(self):
        return {
            "price": float(self.price),
            "courier": self.courier,
            "days": self.days,
            "source": self.source,
            "is_free": self.is_free,
        }


def normalize_region(region_str):
    """Map a free-text region string (from reverse geocoding) to a canonical region name."""
    if not region_str:
        return "default"
    for keyword, canonical in REGION_MAP:
        if keyword.lower() in region_str.lower():
            return canonical
    return "default"


def calculate_total_weight(cart):
    """Sum weight_kg * quantity for all cart items."""
    total = Decimal("0.000")
    for item in cart:
        product = item["product"]
        weight = getattr(product, "weight_kg", Decimal("1.000")) or Decimal("1.000")
        total += Decimal(str(weight)) * item["quantity"]
    return total


def calculate_shipping(cart, destination_region):
    """
    Main entry point. Returns a ShippingResult.
    1. Check free shipping threshold.
    2. Try Shipit API if configured.
    3. Fall back to internal rate table.
    """
    from showcase.models import StoreSettings, ShippingRate

    settings = StoreSettings.get_solo()
    cart_total = cart.get_total_price()
    total_weight = calculate_total_weight(cart)
    canonical_region = normalize_region(destination_region)

    # 1. Free shipping
    if cart_total >= settings.free_shipping_threshold:
        return ShippingResult(price=0, courier="Envío Gratis", days="", source="free", is_free=True)

    # 2. Try Shipit
    if settings.shipit_enabled and settings.shipit_token:
        result = quote_shipit(settings, destination_region, total_weight)
        if result:
            return ShippingResult(
                price=result["price"],
                courier=result["courier"],
                days=str(result["days"]) + " días hábiles",
                source="shipit",
            )

    # 3. Internal DB rates
    db_rate = (
        ShippingRate.objects
        .filter(
            region=canonical_region,
            weight_min_kg__lte=total_weight,
            weight_max_kg__gte=total_weight,
            is_active=True,
        )
        .first()
    )
    if db_rate:
        return ShippingResult(
            price=db_rate.price,
            courier=db_rate.courier_name,
            days=db_rate.estimated_days,
            source="db",
        )

    # 4. Hardcoded fallback
    tiers = DEFAULT_RATES.get(canonical_region, DEFAULT_RATES["default"])
    for max_kg, price, courier, days in tiers:
        if total_weight <= max_kg:
            return ShippingResult(price=price, courier=courier, days=days, source="default")

    last = tiers[-1]
    return ShippingResult(price=last[1], courier=last[2], days=last[3], source="default")
