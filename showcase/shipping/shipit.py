"""
Shipit Chile API integration stub.
Ready to activate — set StoreSettings.shipit_enabled=True and provide shipit_email + shipit_token.
Docs: https://developers.shipit.cl
"""
import urllib.request
import json
from decimal import Decimal


SHIPIT_API_URL = "https://api.shipit.cl/v/quotations"


def quote_shipit(settings, destination_commune, total_weight_kg, total_volume_cm3=None):
    """
    Fetch real-time shipping quote from Shipit API.
    Returns a dict with keys: price, courier, days, source
    Falls back to None on any error (caller should use internal rates).
    """
    if not settings.shipit_email or not settings.shipit_token:
        return None

    # Peso volumétrico: (l x a x h) / 4000  — si no se provee, usar peso físico
    billable_weight = total_weight_kg
    if total_volume_cm3:
        volumetric_kg = Decimal(str(total_volume_cm3)) / Decimal("4000")
        billable_weight = max(total_weight_kg, volumetric_kg)

    payload = json.dumps({
        "quotation": {
            "origin": settings.origin_commune,
            "destination": destination_commune,
            "parcel": {
                "weight": float(billable_weight),
                "height": 10,
                "width": 10,
                "length": 10,
            }
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        SHIPIT_API_URL,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/vnd.shipit.v4",
            "X-Shipit-Email": settings.shipit_email,
            "X-Shipit-Access-Token": settings.shipit_token,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        # Return the cheapest available rate
        rates = data if isinstance(data, list) else data.get("rates", [])
        if rates:
            cheapest = min(rates, key=lambda r: r.get("total_price", 999999))
            return {
                "price": Decimal(str(cheapest.get("total_price", 0))),
                "courier": cheapest.get("courier", {}).get("name", "Courier"),
                "days": cheapest.get("transit_days", "3-5"),
                "source": "shipit",
            }
    except Exception:
        pass
    return None
