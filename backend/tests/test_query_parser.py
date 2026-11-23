"""Unit tests for NLP procurement query parser."""
import pytest
from app.services.query_parser import (
    extract_destination_city,
    extract_quantity_and_unit,
    extract_taxonomy_and_item,
    extract_timeline_days,
    parse_procurement_query,
)


def test_extract_quantity_and_unit_mass():
    qty, unit = extract_quantity_and_unit("Need 1,000 MT of cement")
    assert qty == 1000.0
    assert unit == "METRIC_TONNE"

    qty2, unit2 = extract_quantity_and_unit("Require 500 tonnes of LC3")
    assert qty2 == 500.0
    assert unit2 == "METRIC_TONNE"

    qty3, unit3 = extract_quantity_and_unit("50 bags of mortar")
    assert qty3 == 50.0
    assert unit3 == "BAG_50KG"


def test_extract_quantity_and_unit_discrete_and_services():
    qty, unit = extract_quantity_and_unit("Need 25 bulker truckloads for dispatch")
    assert qty == 25.0
    assert unit == "TRUCKLOAD"

    qty2, unit2 = extract_quantity_and_unit("Looking for 10 containers")
    assert qty2 == 10.0
    assert unit2 == "CONTAINER"

    qty3, unit3 = extract_quantity_and_unit("Warehouse space of 25,000 sq ft")
    assert qty3 == 25000.0
    assert unit3 == "SQ_FT"


def test_extract_timeline():
    assert extract_timeline_days("need supply within 45 days") == 45
    assert extract_timeline_days("dispatch in 30 days") == 30
    assert extract_timeline_days("within 2 weeks") == 14
    assert extract_timeline_days("within 1 month") == 30
    assert extract_timeline_days("no timeline specified") is None


def test_extract_destination_city():
    assert extract_destination_city("need 1000 MT in Pune") == "Pune"
    assert extract_destination_city("transport to Mumbai terminal") == "Mumbai"
    assert extract_destination_city("site located at Nashik") == "Nashik"
    assert extract_destination_city("deliveries for Bengaluru metro project") == "Bengaluru"


def test_extract_taxonomy_and_item_materials():
    prod, grade, serv, item, inq = extract_taxonomy_and_item("LC3-50 Low Carbon cement")
    assert prod == "CALCINED_CLAY_LC3"
    assert grade == "LC3_50_STANDARD"
    assert serv is None
    assert inq == "RFQ_PRODUCT"

    prod2, grade2, serv2, item2, inq2 = extract_taxonomy_and_item("OPC 53 high early strength")
    assert prod2 == "ORDINARY_PORTLAND_CEMENT"
    assert grade2 == "OPC_53_IS_269"
    assert inq2 == "RFQ_PRODUCT"

    prod3, grade3, serv3, item3, inq3 = extract_taxonomy_and_item("Portland Pozzolana Cement PPC")
    assert prod3 == "PORTLAND_POZZOLANA_CEMENT"
    assert inq3 == "RFQ_PRODUCT"


def test_extract_taxonomy_and_item_services():
    prod, grade, serv, item, inq = extract_taxonomy_and_item("Dedicated bulker fleet haulage")
    assert serv == "CONSTRUCTION_LOGISTICS"
    assert inq == "RFI_SERVICE"

    prod2, grade2, serv2, item2, inq2 = extract_taxonomy_and_item("NABL accredited laboratory testing")
    assert serv2 == "MATERIAL_TESTING_NABL"
    assert inq2 == "RFI_SERVICE"


def test_full_parse_procurement_query():
    # Full Natural Language Query
    parsed = parse_procurement_query("Need 1000 MT LC3-50 cement in Pune within 45 days")
    assert parsed.matched_product_code == "CALCINED_CLAY_LC3"
    assert parsed.matched_grade_code == "LC3_50_STANDARD"
    assert parsed.quantity == 1000.0
    assert parsed.quantity_unit == "METRIC_TONNE"
    assert parsed.destination_city == "Pune"
    assert parsed.target_timeline_days == 45
    assert parsed.inquiry_type == "RFQ_PRODUCT"
    assert parsed.confidence >= 0.85

    # Logistics Fleet Query
    parsed2 = parse_procurement_query("Require 25 bulker truckloads for cement haulage to Mumbai within 30 days")
    assert parsed2.matched_service_code == "CONSTRUCTION_LOGISTICS"
    assert parsed2.quantity == 25.0
    assert parsed2.quantity_unit == "TRUCKLOAD"
    assert parsed2.destination_city == "Mumbai"
    assert parsed2.target_timeline_days == 30
    assert parsed2.inquiry_type == "RFI_SERVICE"

    # Exploratory Partnership Query (Anti-false-positive NABL check)
    parsed3 = parse_procurement_query("Exploring sustainable cement blends and potential commercial supply partnership for Western Maharashtra pipeline")
    assert parsed3.matched_product_code == "CALCINED_CLAY_LC3"
    assert parsed3.matched_grade_code == "LC3_50_STANDARD"
    assert parsed3.matched_service_code is None  # Must NOT be falsely matched as NABL testing lab
    assert parsed3.destination_city == "Western Maharashtra"
    assert parsed3.inquiry_type == "EXPLORATORY_COLLABORATION"
    assert "Limestone Calcined Clay" in parsed3.item_name


def test_regional_delivery_coverage_normalization():
    from app.services.business_matching import check_location_covered
    # Pune supplier covers Western Maharashtra query
    assert check_location_covered("Western Maharashtra", ["Pune", "Mumbai", "Nashik", "Kolhapur"]) is True
    # Western Maharashtra distributor covers Pune query
    assert check_location_covered("Pune", ["Western Maharashtra", "Satara"]) is True
    # Out of region
    assert check_location_covered("Chennai", ["Pune", "Nashik"]) is False
