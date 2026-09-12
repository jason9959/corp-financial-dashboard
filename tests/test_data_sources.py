from data_sources import Company, search_companies


def test_search_prioritizes_exact_symbol():
    companies = [
        Company("Apple Hospitality", "APLE", "미국", "SEC EDGAR", "1"),
        Company("Apple Inc.", "AAPL", "미국", "SEC EDGAR", "2"),
    ]
    assert search_companies(companies, "AAPL")[0].name == "Apple Inc."


def test_search_supports_korean_company_name():
    companies = [Company("삼성전자", "005930", "한국", "DART", "00126380")]
    assert search_companies(companies, "삼성 전자")[0].symbol == "005930"


def test_blank_query_has_no_results():
    assert search_companies([], "  ") == []


def test_duplicate_ranked_matches_do_not_compare_company_objects():
    companies = [
        Company("Google Inc.", "GOOG", "미국", "SEC EDGAR", "1"),
        Company("Google Inc.", "GOOG", "미국", "SEC EDGAR", "2"),
    ]
    assert len(search_companies(companies, "GOOG")) == 2
