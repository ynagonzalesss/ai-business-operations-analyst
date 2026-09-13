from app.tools import analyze_trends, calculate_kpis, compare_properties, query_data


def test_query_data_returns_june_revenue_for_property_2():
    result = query_data(2, "2025-06", "2025-06", ["revenue"])
    assert result["success"] and result["data"]["row_count"] == 1
    assert result["data"]["rows"][0]["revenue"] > 0


def test_kpis_are_deterministic_and_valid():
    result = calculate_kpis(2, "2025-06", "2025-06")
    kpis = result["data"]["kpis"][0]
    assert result["success"] and 0 < kpis["occupancy"] <= 1
    assert kpis["revpar"] == round(kpis["revenue"] / kpis["available_nights"], 2)


def test_comparison_returns_benchmark():
    result = compare_properties([3, 8])
    assert result["success"] and len(result["data"]["properties"]) == 2
    assert result["data"]["portfolio_benchmark"]["revpar"] > 0


def test_trend_handles_supported_metric():
    result = analyze_trends(4, "occupancy", "2025-07", "2025-12")
    assert result["success"] and len(result["data"]["monthly_values"]) == 6


def test_rejects_invalid_and_missing_inputs():
    assert not query_data(999)["success"]
    assert not analyze_trends(1, "guest_satisfaction")["success"]
    assert not compare_properties([1])["success"]
