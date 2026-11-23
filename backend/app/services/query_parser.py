"""NLP and regex-based parser for procurement and commercial requirement inquiries."""
import re
from typing import Optional, Tuple
from app.lib.units import normalize_unit_string, UNIT_REGISTRY
from app.schemas.business_matching import ParsedBusinessRequirement

# Common cities and regional territories for destination extraction (sorted by length descending for greedy match)
COMMON_CITIES = [
    "Chhatrapati Sambhajinagar", "Western Maharashtra", "Delhi NCR", "Navi Mumbai", "South Gujarat",
    "Visakhapatnam", "Aurangabad", "Chandigarh", "Ahmedabad", "Bengaluru", "Hyderabad",
    "Bangalore", "Gurugram", "Vadodara", "Kolhapur", "Solapur", "Lucknow", "Kolkata", "Chennai",
    "Gaurgaon", "Nagpur", "Nashik", "Mumbai", "Jaipur", "Indore", "Bhopal", "Satara", "Sangli",
    "Thane", "Surat", "Noida", "Delhi", "Pune", "Maharashtra", "Gujarat", "Karnataka", "NCR"
]


def extract_quantity_and_unit(text: str) -> Tuple[Optional[float], Optional[str]]:
    """Extract numeric quantity and normalized canonical unit from text."""
    # Pattern matching numbers followed by common units
    pattern = re.compile(
        r"(?P<qty>\d+(?:,\d+)*(?:\.\d+)?)\s*(?P<unit>MT|metric\s*tonnes?|tonnes?|tons?|kgs?|kilograms?|bags?_50kg|bags?|truckloads?|bulkers?|containers?|sq\.?\s*ft|square\s*feet|pallets?|man[_\s]days?|man[_\s]months?|hours?|hrs?|units?|pieces?)\b",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if match:
        raw_qty = match.group("qty").replace(",", "")
        raw_unit = match.group("unit").strip()
        try:
            qty = float(raw_qty)
        except ValueError:
            qty = None

        norm_unit = normalize_unit_string(raw_unit)
        # Unit normalization mapping
        if norm_unit in ("BULKERS", "BULKER", "TRUCKLOAD", "TRUCKLOADS"):
            unit = "TRUCKLOAD"
        elif norm_unit in ("MT", "TONNE", "TONNES", "TON", "TONS", "METRIC_TONNE"):
            unit = "METRIC_TONNE"
        elif norm_unit in ("KG", "KGS", "KILOGRAM", "KILOGRAMS"):
            unit = "KILOGRAM"
        elif norm_unit in ("BAG", "BAGS", "BAG_50KG", "BAGS_50KG"):
            unit = "BAG_50KG"
        elif norm_unit in ("SQ_FT", "SQUARE_FEET", "SQFT"):
            unit = "SQ_FT"
        elif norm_unit in ("CONTAINER", "CONTAINERS"):
            unit = "CONTAINER"
        elif norm_unit in ("PALLET", "PALLETS"):
            unit = "PALLET"
        elif norm_unit in ("MAN_DAY", "MAN_DAYS", "MANDAY", "MANDAYS"):
            unit = "MAN_DAY"
        elif norm_unit in ("MAN_MONTH", "MAN_MONTHS"):
            unit = "MAN_MONTH"
        else:
            unit = norm_unit

        return qty, unit

    # Fallback: standalone quantity
    num_match = re.search(r"\b(\d+(?:,\d+)*(?:\.\d+)?)\b", text)
    if num_match:
        try:
            return float(num_match.group(1).replace(",", "")), None
        except ValueError:
            pass

    return None, None


def extract_timeline_days(text: str) -> Optional[int]:
    """Extract timeline in days from text."""
    # "within 45 days", "in 30 days"
    day_match = re.search(r"(?:within|in|target|timeline:?)\s*(\d+)\s*(?:days?|d)\b", text, re.IGNORECASE)
    if day_match:
        return int(day_match.group(1))

    # "within 2 weeks", "in 3 weeks"
    week_match = re.search(r"(?:within|in|target)\s*(\d+)\s*(?:weeks?|w)\b", text, re.IGNORECASE)
    if week_match:
        return int(week_match.group(1)) * 7

    # "within 1 month"
    month_match = re.search(r"(?:within|in|target)\s*(\d+)\s*(?:months?|m)\b", text, re.IGNORECASE)
    if month_match:
        return int(month_match.group(1)) * 30

    # Standalone "45 days"
    simple_day = re.search(r"\b(\d+)\s*days?\b", text, re.IGNORECASE)
    if simple_day:
        return int(simple_day.group(1))

    return None


def extract_destination_city(text: str) -> Optional[str]:
    """Extract destination city or regional territory from text."""
    # Check known cities and territories
    for city in COMMON_CITIES:
        if re.search(rf"\b{re.escape(city)}\b", text, re.IGNORECASE):
            return city

    # Look for "in <City>", "to <City>", "for <City>"
    prep_match = re.search(r"\b(?:in|to|for|at|destination:?)\s+([A-Z][a-zA-Z\s]{2,30})\b", text)
    if prep_match:
        cand = prep_match.group(1).strip()
        # Clean trailing project/scope nouns
        cand = re.sub(
            r"\b(?:pipeline|project|site|plant|terminal|network|depot|region|area|hub|works|corridor)\b",
            "",
            cand,
            flags=re.IGNORECASE,
        ).strip()
        # Avoid common false positives
        if cand and cand.lower() not in ("india", "days", "standard", "trial", "bulk", "requirement", "materials"):
            return cand

    return None


def extract_taxonomy_and_item(text: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], str]:
    """Match taxonomy references, canonical names, or infer custom product/service.

    Returns:
        (product_code, grade_code, service_code, item_name, inquiry_type)
    """
    lower = text.lower()

    def has_kw(kw: str) -> bool:
        """Match exact word boundary to prevent accidental substring collisions (e.g. 'sustainable' vs 'nabl')."""
        return bool(re.search(rf"\b{re.escape(kw.lower())}\b", lower))

    def has_any_kw(kws: Tuple[str, ...]) -> bool:
        return any(has_kw(k) for k in kws)

    prod_code: Optional[str] = None
    grade_code: Optional[str] = None
    serv_code: Optional[str] = None
    item_name: Optional[str] = None

    # 1. Product Grade & Canonical Product Detection
    # Check LC3 & Sustainable Cements
    if (
        has_any_kw(("lc3-50", "lc3 50", "lc3_50"))
        or "low carbon blend" in lower
        or "sustainable cement blend" in lower
    ):
        prod_code, grade_code, item_name = (
            "CALCINED_CLAY_LC3",
            "LC3_50_STANDARD",
            "Limestone Calcined Clay Cement (LC3-50)",
        )
    elif (
        has_any_kw((
            "lc3",
            "calcined clay",
            "sustainable cement",
            "green cement",
            "low carbon cement",
            "low-carbon cement",
            "eco cement",
            "cement blend",
            "cement blends",
        ))
        or (
            has_kw("cement")
            and has_any_kw(("sustainable", "green", "low carbon", "decarbonized", "eco"))
        )
    ):
        prod_code, grade_code, item_name = (
            "CALCINED_CLAY_LC3",
            "LC3_50_STANDARD",
            "Limestone Calcined Clay Cement (LC3)",
        )
    # Check OPC
    elif has_any_kw(("opc 53", "opc-53", "grade 53", "53 grade", "opc_53")):
        prod_code, grade_code, item_name = (
            "ORDINARY_PORTLAND_CEMENT",
            "OPC_53_IS_269",
            "Ordinary Portland Cement (OPC 53)",
        )
    elif has_any_kw(("opc 43", "opc-43", "grade 43", "43 grade", "opc_43")):
        prod_code, grade_code, item_name = (
            "ORDINARY_PORTLAND_CEMENT",
            "OPC_43_IS_269",
            "Ordinary Portland Cement (OPC 43)",
        )
    elif has_any_kw(("opc", "ordinary portland")):
        prod_code, item_name = (
            "ORDINARY_PORTLAND_CEMENT",
            "Ordinary Portland Cement (OPC)",
        )
    # Check PPC
    elif has_any_kw(("ppc", "pozzolana", "portland pozzolana", "fly ash cement")):
        prod_code, item_name = (
            "PORTLAND_POZZOLANA_CEMENT",
            "Portland Pozzolana Cement (PPC)",
        )
    # Check Clinker
    elif has_any_kw(("clinker", "cement clinker")):
        prod_code, item_name = (
            "CEMENT_CLINKER",
            "Cement Clinker Intermediate",
        )

    # 2. Service Taxonomy Detection (Word Boundaries to prevent collision)
    if not prod_code:
        if has_any_kw((
            "bulker", "bulkers", "haulage", "transport", "fleet",
            "truckload", "truck", "trucks", "tanker", "logistics", "freight"
        )):
            serv_code, item_name = (
                "CONSTRUCTION_LOGISTICS",
                "Bulk Construction Material Transport & Fleet",
            )
        elif has_any_kw((
            "testing", "laboratory", "audit", "audits", "nabl", "quality check", "test lab"
        )) or (has_kw("lab") and not has_any_kw(("collab", "collaboration", "collaborative", "elaborate"))):
            serv_code, item_name = (
                "MATERIAL_TESTING_NABL",
                "Materials Testing & Laboratory Quality Audits",
            )
        elif has_any_kw((
            "maintenance", "calibration", "epc support", "repair", "shutdown", "kiln repair"
        )):
            serv_code, item_name = (
                "PLANT_MAINTENANCE",
                "Preventive Plant & Kiln Maintenance Services",
            )

    # 3. Inquiry Type / Intent Resolution
    if serv_code:
        inquiry_type = "RFI_SERVICE"
    else:
        inquiry_type = "RFQ_PRODUCT"

    if has_any_kw((
        "exploratory", "explore", "exploring", "business relationship",
        "commercial relationship", "potential relationship", "potential business",
        "synergies", "synergy", "joint evaluation", "joint opportunities"
    )):
        inquiry_type = "EXPLORATORY_COLLABORATION"
    elif has_any_kw((
        "distributor application", "dealership application", "stockist application",
        "become a distributor", "seeking distributorship"
    )):
        inquiry_type = "DISTRIBUTOR_APPLICATION"
    elif has_any_kw((
        "distributor", "distributors", "dealership", "dealers",
        "stockist", "stockists", "warehousing", "retailer", "channel", "distribution network"
    )):
        inquiry_type = "DISTRIBUTION_EXPANSION"
    elif has_any_kw((
        "partnership", "joint venture", "co-manufacturing", "alliance",
        "feedstock sourcing", "raw material sourcing"
    )):
        inquiry_type = "SOURCING_PARTNERSHIP"
    elif has_any_kw((
        "alternative", "substitute", "secondary supplier", "dual source", "low carbon alternative"
    )):
        inquiry_type = "ALTERNATIVE_SOURCING"

    # 4. Fallback: derive item name from query if still missing
    if not prod_code and not serv_code:
        if inquiry_type == "DISTRIBUTION_EXPANSION":
            item_name = "Distribution & Channel Sourcing"
        elif inquiry_type == "SOURCING_PARTNERSHIP":
            item_name = "Strategic Commercial Partnership"
        elif inquiry_type == "EXPLORATORY_COLLABORATION":
            item_name = "Exploratory Business Collaboration"
        elif inquiry_type == "ALTERNATIVE_SOURCING":
            item_name = "Alternative Sourcing Inquiry"
        else:
            clean_words = [
                w for w in text.split()
                if not re.match(r"^\d+$", w)
                and w.lower() not in (
                    "need", "looking", "for", "require", "in", "within", "days",
                    "days.", "mt", "tons", "tonnes", "pune", "mumbai", "exploring", "potential"
                )
            ]
            item_name = " ".join(clean_words).strip() or "Custom Requirement"

    return prod_code, grade_code, serv_code, item_name, inquiry_type


def parse_procurement_query(query: str) -> ParsedBusinessRequirement:
    """Parse unstructured procurement inquiry into structured requirement components."""
    clean_query = query.strip()
    qty, unit = extract_quantity_and_unit(clean_query)
    timeline = extract_timeline_days(clean_query)
    city = extract_destination_city(clean_query)
    prod_code, grade_code, serv_code, item_name, inq_type = extract_taxonomy_and_item(clean_query)

    return ParsedBusinessRequirement(
        raw_query=clean_query,
        item_name=item_name,
        matched_product_code=prod_code,
        matched_grade_code=grade_code,
        matched_service_code=serv_code,
        quantity=qty,
        quantity_unit=unit,
        destination_city=city,
        target_timeline_days=timeline,
        inquiry_type=inq_type,
        confidence=0.9 if (prod_code or serv_code) else 0.75,
    )
