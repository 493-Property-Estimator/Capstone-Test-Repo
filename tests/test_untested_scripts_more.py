from __future__ import annotations

import json
import sqlite3
import sys
import types
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from scripts import bed_bath as bed
from scripts import clean_realtor_cards as clean
from scripts import edmonton_neighbourhood_census_builder as census
from scripts import manual_bed_bath as manual
from scripts import run_bedbath_shadow_proof as shadow


def test_manual_helpers_and_progress_files(tmp_path: Path, monkeypatch, capsys) -> None:
    assert manual.clean_text("  a\n b  ") == "a b"
    assert manual.clean_text(None) == ""
    assert manual.unique_keep_order(["a", "b", "a"]) == ["a", "b"]
    assert manual.is_probably_residential("Industrial Park") is False
    assert manual.is_probably_residential("Downtown") is True

    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return [{"name_mixed": "Downtown"}, {"name": "Industrial Area"}]

    monkeypatch.setattr(manual.requests, "get", lambda *_a, **_k: Resp())
    assert manual.fetch_edmonton_neighbourhoods() == ["Downtown"]

    csv_path = tmp_path / "x.csv"
    manual.ensure_csv_exists(csv_path)
    rows = [{"neighbourhood": "Downtown", "listing_url": "u", "address": "a", "price": "", "beds": "", "baths": "", "sqft": "", "raw_text": ""}]
    manual.append_rows(csv_path, rows)
    assert len(manual.load_existing_rows(csv_path)) == 1
    keys = manual.load_existing_keys(csv_path)
    assert ("Downtown", "u", "a") in keys
    manual.rewrite_csv_without_neighbourhoods(csv_path, {"Downtown"})
    assert manual.load_existing_rows(csv_path) == []

    progress = tmp_path / "p.txt"
    assert manual.load_completed_progress(progress) == set()
    manual.write_completed_progress(progress, {"B", "A"})
    assert manual.load_completed_progress(progress) == {"A", "B"}
    manual.append_completed_progress(progress, "C")
    assert "C" in progress.read_text(encoding="utf-8")

    price, address, beds_v, baths_v, sqft = manual.parse_card_text("$100\n123 Main St\n2 beds 1 baths 900 sqft")
    assert price and address == "123 Main St" and beds_v == "2" and baths_v == "1" and sqft == "900"

    rem = manual.build_remaining_list(["A", "B", "C"], {"A"}, "B", set())
    assert rem == ["B", "C"]
    rem2 = manual.build_remaining_list(["A", "B"], set(), "Z", set())
    assert rem2 == ["A", "B"]
    assert "START_FROM 'Z'" in capsys.readouterr().out


def test_manual_main_force_redo_branch(monkeypatch, tmp_path: Path) -> None:
    out_csv = tmp_path / "manual.csv"
    progress = tmp_path / "progress.txt"
    out_csv.write_text(
        "neighbourhood,price,address,beds,baths,sqft,listing_url,raw_text\nN1,$1,A,1,1,100,u,t\n",
        encoding="utf-8",
    )
    progress.write_text("N1\n", encoding="utf-8")
    monkeypatch.setattr(manual, "OUT_CSV", str(out_csv))
    monkeypatch.setattr(manual, "PROGRESS_FILE", str(progress))
    monkeypatch.setattr(manual, "FORCE_REDO", {"N1"})
    monkeypatch.setattr(manual, "START_FROM", "")
    monkeypatch.setattr(manual, "fetch_edmonton_neighbourhoods", lambda: ["N1"])
    monkeypatch.setattr(manual, "extract_rows_from_current_page", lambda *_a, **_k: [])
    monkeypatch.setattr("builtins.input", lambda _p: "q")

    class MPage:
        url = "http://x"

        def title(self):
            return "t"

    class MContext:
        pages = [MPage()]

    class MBrowser:
        contexts = [MContext()]

    class MPlay:
        chromium = types.SimpleNamespace(connect_over_cdp=lambda _u: MBrowser())

    class MCM:
        def __enter__(self):
            return MPlay()

        def __exit__(self, *_a):
            return None

    monkeypatch.setattr(manual, "sync_playwright", lambda: MCM())
    manual.main()
    assert "N1" not in progress.read_text(encoding="utf-8")


def test_manual_extract_rows_from_current_page(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(manual, "DEBUG_HTML", str(tmp_path / "dbg.html"))

    class Card:
        def __init__(self, text: str, links: list[str]):
            self._text = text
            self._links = links

        def inner_text(self, timeout=1000):
            if self._text == "ERR":
                raise RuntimeError("x")
            return self._text

        def locator(self, _sel):
            return types.SimpleNamespace(evaluate_all=lambda _js: self._links)

    class DivFilter:
        def all(self):
            return [
                Card("$100\n123 Main", ["https://www.realtor.ca/real-estate/1"]),
                Card("$100\n123 Main", ["https://www.realtor.ca/real-estate/1"]),  # duplicate
                Card("no money", []),
                Card("ERR", []),
            ]

    class Page:
        def content(self):
            return "<html>ok</html>"

        def locator(self, _sel):
            return types.SimpleNamespace(filter=lambda **_k: DivFilter())

    out = manual.extract_rows_from_current_page(Page(), "Downtown")
    assert len(out) == 1
    assert out[0]["listing_url"].endswith("/1")


def test_bed_bath_helpers_and_scrape(monkeypatch, tmp_path: Path) -> None:
    assert bed.slugify("Wîhkwêntôwin") == "wihkwentowin"
    assert bed.safe_get({"a": {"b": 1}}, "a", "b") == 1
    assert bed.safe_get({"a": 1}, "a", "b", default=2) == 2
    assert bed.unique_keep_order(["x", "x", "y"]) == ["x", "y"]
    assert bed.extract_beds_baths_from_text("3 bedrooms and 2 baths") == ("3", "2")
    assert bed.extract_listing_links_from_html('<a href="/real-estate/123/x"></a><a href="/other"></a>') == [
        "https://www.realtor.ca/real-estate/123/x"
    ]
    assert len(bed.extract_json_ld('<script type="application/ld+json">{"@type":"House"}</script>')) == 1
    assert bed.is_probably_residential("Big Lake") is False

    html = """
    <html><head><title>123 Main - REALTOR.ca</title>
    <script type="application/ld+json">{"@type":"House","numberOfBedrooms":3,"numberOfBathroomsTotal":2,"offers":{"price":"123000"}}</script>
    </head><body>$123,000 3 bedrooms 2 bathrooms</body></html>
    """
    row = bed.extract_listing_details(html, "https://www.realtor.ca/real-estate/1")
    assert row.price in {"123000", "$123,000"}
    assert row.beds == "3" and row.baths == "2"

    class FakePage:
        def __init__(self, html_text):
            self._html = html_text
            self.calls = []

        def goto(self, url, **_kwargs):
            self.calls.append(url)

        def wait_for_timeout(self, _ms):
            return None

        def content(self):
            return self._html

    monkeypatch.setattr(bed, "find_neighbourhood_page_via_search", lambda _n: "https://www.realtor.ca/ab/edmonton/downtown/real-estate")
    page = FakePage((('"/real-estate/111" "https://www.realtor.ca/real-estate/222/" ') * 300))
    links = bed.get_listing_links_for_neighbourhood(page, "Downtown")
    assert links and links[0].startswith("https://www.realtor.ca/real-estate/")

    monkeypatch.setattr(bed.requests, "get", lambda *_a, **_k: types.SimpleNamespace(text="https://www.realtor.ca/ab/edmonton/downtown/real-estate"))
    assert bed.find_neighbourhood_page_via_search("Downtown") is not None

    class TimeoutPage:
        def goto(self, *_a, **_k):
            raise bed.PlaywrightTimeoutError("x")

        def wait_for_timeout(self, *_a, **_k):
            return None

        def content(self):
            return ""

    assert bed.scrape_listing(TimeoutPage(), "u") is None


def test_bed_bath_more_branches(monkeypatch) -> None:
    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return [{"name_mixed": "Downtown"}, {"name_mixed": "Industrial Park"}]

    monkeypatch.setattr(bed.requests, "get", lambda *_a, **_k: Resp())
    out = bed.fetch_edmonton_neighbourhoods()
    assert "Downtown" in out and "Industrial Park" in out

    assert bed.extract_json_ld(
        '<script type="application/ld+json">[{"@type":"House"}, {"x":1}]</script>'
        '<script type="application/ld+json">{bad json</script>'
    )
    assert bed.extract_listing_links_from_html('<a href="/real-estate/123"></a>')

    monkeypatch.setattr(bed.requests, "get", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("x")))
    assert bed.find_neighbourhood_page_via_search("X") is None

    class BadParsePage:
        def goto(self, *_a, **_k):
            return None

        def wait_for_timeout(self, *_a, **_k):
            return None

        def content(self):
            return "<html>"

    monkeypatch.setattr(bed, "extract_listing_details", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("bad")))
    assert bed.scrape_listing(BadParsePage(), "u") is None

    # Hit cleaned.append branch in search fallback parser (escaped dots form).
    monkeypatch.setattr(
        bed.requests,
        "get",
        lambda *_a, **_k: types.SimpleNamespace(text=r"https://www\.realtor\.ca/ab/edmonton/downtown/real-estate"),
    )
    assert bed.find_neighbourhood_page_via_search("Downtown") is not None


def test_clean_realtor_helper_paths(tmp_path: Path, monkeypatch) -> None:
    variants = clean.generate_address_variants("#251 6079 MAYNARD WY NW")
    assert any("MAYNARD WAY NW" in v for v in variants)
    assert clean.base_address_key("") == ""
    assert "EDMONTON" not in clean.normalize_address_key("123 x, Edmonton Alberta")
    assert clean.clean_price("Price $123,456 CAD") == "$123,456"
    assert clean.parse_address("x", "https://www.realtor.ca/real-estate/1/123-main-edmonton-downtown", "") == "123 MAIN"
    assert clean.parse_price("now $1,000", "") == "$1,000"
    assert clean.parse_beds_baths_sqft("2 beds 1 baths 900 sqft", "", "", "") == ("2", "1", "900")

    r1 = clean.CleanRow("a", "", "", "", "", "", "", "", "")
    r2 = clean.CleanRow("a", "2", "", "", "", "u", "", "", "")
    assert clean.pick_better_row(r1, r2) == r2

    house, street = clean.split_house_and_street("#251 6079 MAYNARD WY NW")
    assert house == "6079" and "MAYNARD" in street
    assert clean.normalize_street_for_match("MAYNARD WY NW").endswith("WAY NW")

    db = sqlite3.connect(tmp_path / "addr.db")
    db.execute("CREATE TABLE property_locations_prod (house_number TEXT, street_name TEXT, lat REAL, lon REAL)")
    db.execute("INSERT INTO property_locations_prod VALUES ('6079','MAYNARD WAY NW',53.1,-113.1)")
    db.commit()
    lat, lon, status = clean.resolve_address_sqlite("6079 MAYNARD WY NW", db)
    assert lat == 53.1 and lon == -113.1 and status.startswith("sqlite:")
    assert clean.resolve_address_sqlite("not civic", db)[2] == "not_a_civic_address"
    db.close()

    monkeypatch.setattr(clean, "http_get_json", lambda *_a, **_k: [{"lat": "53.5", "lon": "-113.5"}])
    assert clean.geocode_address("a", "http://x?q={query}", 1.0, 0) == (53.5, -113.5)
    monkeypatch.setattr(clean, "http_get_json", lambda *_a, **_k: {"location": {"coordinates": {"lat": 1, "lng": 2}}})
    assert clean.resolve_address_local("a", "http://x?q={query}", 1.0, 0) == (1.0, 2.0)
    monkeypatch.setattr(clean, "http_get_json", lambda *_a, **_k: {"waypoints": [{"location": [-113.4, 53.5]}]})
    assert clean.snap_with_osrm(0.0, 0.0, "http://x/{lat}/{lon}", 1.0, 0) == (53.5, -113.4)
    monkeypatch.setattr(clean, "http_get_json", lambda *_a, **_k: {"address": {"neighbourhood": "Downtown"}})
    assert clean.reverse_neighborhood(0.0, 0.0, "http://x/{lat}/{lon}", 1.0, 0) == "Downtown"
    monkeypatch.setattr(clean, "http_get_json", lambda *_a, **_k: {"address": {}})
    assert clean.reverse_neighborhood(0.0, 0.0, "http://x/{lat}/{lon}", 1.0, 0) == ""

    csv_path = tmp_path / "rows.csv"
    clean.write_rows(csv_path, [clean.CleanRow("A", "1", "1", "100", "$1", "u", "n", "1", "2")])
    assert len(clean.read_rows(csv_path)) == 1
    assert len(clean.read_clean_rows(csv_path)) == 1
    fail_path = tmp_path / "fails.csv"
    clean.write_failures(fail_path, [{"address": "A", "normalized_address": "A"}])
    assert clean.load_failure_address_keys(fail_path) == {"A"}
    assert clean.load_failure_address_keys(tmp_path / "missing.csv") == set()

    # Address resolver fuzzy/no-match branches.
    db2 = sqlite3.connect(tmp_path / "fuzzy.db")
    db2.execute("CREATE TABLE property_locations_prod (house_number TEXT, street_name TEXT, lat REAL, lon REAL)")
    db2.execute("INSERT INTO property_locations_prod VALUES ('6079','MAYNARD WAY NW',53.2,-113.2)")
    db2.commit()
    lat, lon, status = clean.resolve_address_sqlite("6079 MAYNARD WY", db2)
    assert status.startswith("sqlite:") and lat is not None and lon is not None
    assert clean.resolve_address_sqlite("9999 NOWHERE ST", db2)[2] in {"sqlite:no_match", "not_a_civic_address"}
    db2.close()

    # Geocode/local resolver branch coverage for non-float payloads.
    monkeypatch.setattr(clean, "http_get_json", lambda *_a, **_k: [{"lat": "x", "lon": "y"}])
    assert clean.geocode_address("a", "http://x?q={query}", 1.0, 0) == (None, None)
    monkeypatch.setattr(clean, "http_get_json", lambda *_a, **_k: {"candidates": [{"coordinates": {"lat": "x", "lng": "y"}}]})
    assert clean.resolve_address_local("a", "http://x?q={query}", 1.0, 0) == (None, None)


def test_clean_run_parse_minimal(tmp_path: Path) -> None:
    in_csv = tmp_path / "in.csv"
    in_csv.write_text(
        "neighbourhood,listing_url,address,price,beds,baths,sqft,raw_text\n"
        "Downtown,https://www.realtor.ca/real-estate/1,123 MAIN ST,,2,1,900,'$100 2 beds 1 baths 900 sqft 123 Main, Edmonton, Alberta'\n",
        encoding="utf-8",
    )
    out_csv = tmp_path / "out.csv"
    code, total, kept = clean.run_parse([in_csv], out_csv)
    assert code == 0 and total == 1 and kept == 1


def test_clean_build_parser_and_main_dispatch(monkeypatch, tmp_path: Path) -> None:
    parser = clean.build_parser()
    args = parser.parse_args(["parse", "--input", "a.csv", "--output", "b.csv"])
    assert args.command == "parse"
    args2 = parser.parse_args(["enrich", "--input", "a.csv", "--output", "b.csv"])
    assert args2.command == "enrich"

    monkeypatch.setattr(clean, "run_parse", lambda *_a, **_k: (0, 1, 1))
    monkeypatch.setattr(clean, "run_enrich", lambda **_k: 0)
    monkeypatch.setattr(sys, "argv", ["clean_realtor_cards.py", "parse", "--input", str(tmp_path / "x.csv"), "--output", str(tmp_path / "y.csv")])
    assert clean.main() == 0

    monkeypatch.setattr(sys, "argv", ["clean_realtor_cards.py", "enrich", "--input", str(tmp_path / "x.csv"), "--output", str(tmp_path / "y.csv")])
    assert clean.main() == 0

    monkeypatch.setattr(sys, "argv", ["clean_realtor_cards.py"])
    assert clean.main() == 0

    class FakeParser:
        def parse_args(self, _argv):
            return types.SimpleNamespace(command="weird")

    monkeypatch.setattr(clean, "build_parser", lambda: FakeParser())
    monkeypatch.setattr(sys, "argv", ["clean_realtor_cards.py", "weird"])
    assert clean.main() == 1


def test_clean_http_get_json_error_paths(monkeypatch) -> None:
    class Resp:
        def read(self):
            return b'{"ok":1}'

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return None

    monkeypatch.setattr(clean, "urlopen", lambda *_a, **_k: Resp())
    out = clean.http_get_json("http://x", timeout=1, retries=0)
    assert out == {"ok": 1}

    class E429(clean.HTTPError):
        def __init__(self):
            super().__init__("http://x", 429, "rate", hdrs={"Retry-After": "0"}, fp=None)

    calls = {"n": 0}

    def raise_then_success(*_a, **_k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise E429()
        return Resp()

    monkeypatch.setattr(clean, "urlopen", raise_then_success)
    monkeypatch.setattr(clean.time, "sleep", lambda _s: None)
    assert clean.http_get_json("http://x", timeout=1, retries=1) == {"ok": 1}

    monkeypatch.setattr(clean, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(clean.URLError("down")))
    assert clean.http_get_json("http://x", timeout=1, retries=0) is None

    monkeypatch.setattr(clean, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")))
    assert clean.http_get_json("http://x", timeout=1, retries=0) is None


def test_clean_run_enrich_missing_input_and_interrupt(tmp_path: Path, monkeypatch) -> None:
    missing = clean.run_enrich(
        input_path=tmp_path / "missing.csv",
        output_path=tmp_path / "out.csv",
        local_db_path=str(tmp_path / "db.sqlite"),
        skip_local_db_resolver=True,
        skip_external_geocoder=True,
        skip_geocode_fallback=True,
        resolve_url_template="",
        geocode_url_template="",
        reverse_url_template="",
        osrm_nearest_url_template="",
        request_delay_seconds=0.0,
        timeout_seconds=0.1,
        max_enrich=0,
        no_neighborhood_update=True,
        save_every=0,
        resume=False,
        http_retries=0,
        geocode_failures_output="",
        retry_failures_from="",
    )
    assert missing == 1

    in_csv = tmp_path / "in.csv"
    clean.write_rows(in_csv, [clean.CleanRow("1 MAIN ST", "", "", "", "", "", "", "", "")])
    monkeypatch.setattr(clean, "generate_address_variants", lambda _a: (_ for _ in ()).throw(KeyboardInterrupt()))
    code = clean.run_enrich(
        input_path=in_csv,
        output_path=tmp_path / "out.csv",
        local_db_path=str(tmp_path / "db.sqlite"),
        skip_local_db_resolver=True,
        skip_external_geocoder=True,
        skip_geocode_fallback=True,
        resolve_url_template="",
        geocode_url_template="",
        reverse_url_template="",
        osrm_nearest_url_template="",
        request_delay_seconds=0.0,
        timeout_seconds=0.1,
        max_enrich=0,
        no_neighborhood_update=True,
        save_every=0,
        resume=False,
        http_retries=0,
        geocode_failures_output="",
        retry_failures_from="",
    )
    assert code == 130


def test_clean_main_all_parse_failure(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(clean, "run_parse", lambda *_a, **_k: (1, 0, 0))
    monkeypatch.setattr(clean, "run_enrich", lambda **_k: 0)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clean_realtor_cards.py",
            "all",
            "--input",
            str(tmp_path / "a.csv"),
            "--parsed-output",
            str(tmp_path / "p.csv"),
            "--output",
            str(tmp_path / "o.csv"),
        ],
    )
    assert clean.main() == 1


def test_clean_run_enrich_paths(tmp_path: Path, monkeypatch) -> None:
    in_csv = tmp_path / "in.csv"
    out_csv = tmp_path / "out.csv"
    clean.write_rows(
        in_csv,
        [
            clean.CleanRow("100 MAIN ST", "", "", "", "", "", "Old", "53.5000000", "-113.5000000"),
            clean.CleanRow("100 MAIN ST", "", "", "", "", "", "", "", ""),
            clean.CleanRow("200 MAIN ST", "", "", "", "", "", "", "", ""),
        ],
    )

    # Imputation-only path.
    code = clean.run_enrich(
        input_path=in_csv,
        output_path=out_csv,
        local_db_path=str(tmp_path / "missing.db"),
        skip_local_db_resolver=True,
        skip_external_geocoder=True,
        skip_geocode_fallback=True,
        resolve_url_template="",
        geocode_url_template="http://x/{query}",
        reverse_url_template="http://x/{lat}/{lon}",
        osrm_nearest_url_template="",
        request_delay_seconds=0.0,
        timeout_seconds=0.1,
        max_enrich=2,
        no_neighborhood_update=True,
        save_every=1,
        resume=False,
        http_retries=0,
        geocode_failures_output="",
        retry_failures_from="",
    )
    assert code == 0
    rows = clean.read_clean_rows(out_csv)
    assert rows[1].lat and rows[1].long

    # Resolver/geocoder failure path.
    monkeypatch.setattr(clean, "resolve_address_local", lambda *_a, **_k: (None, None))
    monkeypatch.setattr(clean, "geocode_address", lambda *_a, **_k: (None, None))
    code2 = clean.run_enrich(
        input_path=in_csv,
        output_path=out_csv,
        local_db_path=str(tmp_path / "missing.db"),
        skip_local_db_resolver=False,
        skip_external_geocoder=False,
        skip_geocode_fallback=False,
        resolve_url_template="http://resolver/{query}",
        geocode_url_template="http://geo/{query}",
        reverse_url_template="http://rev/{lat}/{lon}",
        osrm_nearest_url_template="",
        request_delay_seconds=0.0,
        timeout_seconds=0.1,
        max_enrich=1,
        no_neighborhood_update=False,
        save_every=0,
        resume=True,
        http_retries=0,
        geocode_failures_output=str(tmp_path / "fails.csv"),
        retry_failures_from="",
    )
    assert code2 == 0
    assert (tmp_path / "fails.csv").exists()

    # Success path with snap + reverse.
    monkeypatch.setattr(clean, "resolve_address_local", lambda *_a, **_k: (53.0, -113.0))
    monkeypatch.setattr(clean, "snap_with_osrm", lambda *_a, **_k: (53.1, -113.1))
    monkeypatch.setattr(clean, "reverse_neighborhood", lambda *_a, **_k: "Downtown")
    retry_csv = tmp_path / "retry.csv"
    retry_csv.write_text(
        "address,normalized_address,db_error,resolver_error,geocode_error,error,attempted_queries\n"
        "200 MAIN ST,200 MAIN ST,,,,,\n",
        encoding="utf-8",
    )
    code3 = clean.run_enrich(
        input_path=in_csv,
        output_path=out_csv,
        local_db_path=str(tmp_path / "missing.db"),
        skip_local_db_resolver=True,
        skip_external_geocoder=False,
        skip_geocode_fallback=True,
        resolve_url_template="http://resolver/{query}",
        geocode_url_template="http://geo/{query}",
        reverse_url_template="http://rev/{lat}/{lon}",
        osrm_nearest_url_template="http://osrm/{lat}/{lon}",
        request_delay_seconds=0.0,
        timeout_seconds=0.1,
        max_enrich=1,
        no_neighborhood_update=False,
        save_every=0,
        resume=False,
        http_retries=0,
        geocode_failures_output="",
        retry_failures_from=str(retry_csv),
    )
    assert code3 == 0
    rows2 = clean.read_clean_rows(out_csv)
    assert any(r.neighborhood == "Downtown" for r in rows2)

    # Retry file missing branch.
    code4 = clean.run_enrich(
        input_path=in_csv,
        output_path=out_csv,
        local_db_path=str(tmp_path / "missing.db"),
        skip_local_db_resolver=True,
        skip_external_geocoder=True,
        skip_geocode_fallback=True,
        resolve_url_template="",
        geocode_url_template="",
        reverse_url_template="",
        osrm_nearest_url_template="",
        request_delay_seconds=0.0,
        timeout_seconds=0.1,
        max_enrich=0,
        no_neighborhood_update=True,
        save_every=0,
        resume=False,
        http_retries=0,
        geocode_failures_output="",
        retry_failures_from=str(tmp_path / "nope.csv"),
    )
    assert code4 == 1


def test_clean_run_enrich_db_and_failure_branches(tmp_path: Path, monkeypatch, capsys) -> None:
    in_csv = tmp_path / "in2.csv"
    out_csv = tmp_path / "out2.csv"
    clean.write_rows(in_csv, [clean.CleanRow("500 FOO RD", "", "", "", "", "", "", "", "")])

    db_file = tmp_path / "local.db"
    sqlite3.connect(db_file).close()
    monkeypatch.setattr(clean, "resolve_address_sqlite", lambda *_a, **_k: (None, None, "sqlite:no_match"))
    monkeypatch.setattr(clean, "resolve_address_local", lambda *_a, **_k: (None, None))
    monkeypatch.setattr(clean, "geocode_address", lambda *_a, **_k: (None, None))
    clean.LAST_HTTP_ERROR = "forced error"
    code = clean.run_enrich(
        input_path=in_csv,
        output_path=out_csv,
        local_db_path=str(db_file),
        skip_local_db_resolver=False,
        skip_external_geocoder=False,
        skip_geocode_fallback=False,
        resolve_url_template="http://resolver/{query}",
        geocode_url_template="http://geo/{query}",
        reverse_url_template="http://rev/{lat}/{lon}",
        osrm_nearest_url_template="",
        request_delay_seconds=0.0,
        timeout_seconds=0.1,
        max_enrich=0,
        no_neighborhood_update=False,
        save_every=0,
        resume=False,
        http_retries=0,
        geocode_failures_output=str(tmp_path / "fails2.csv"),
        retry_failures_from="",
    )
    assert code == 0
    assert "First geocode error:" in capsys.readouterr().out
    assert "forced error" in (tmp_path / "fails2.csv").read_text(encoding="utf-8")

    # Success path where periodic checkpoint save branch executes.
    monkeypatch.setattr(clean, "resolve_address_local", lambda *_a, **_k: (53.2, -113.2))
    monkeypatch.setattr(clean, "snap_with_osrm", lambda *_a, **_k: (53.3, -113.3))
    monkeypatch.setattr(clean, "reverse_neighborhood", lambda *_a, **_k: "")
    code2 = clean.run_enrich(
        input_path=in_csv,
        output_path=out_csv,
        local_db_path=str(db_file),
        skip_local_db_resolver=True,
        skip_external_geocoder=False,
        skip_geocode_fallback=True,
        resolve_url_template="http://resolver/{query}",
        geocode_url_template="http://geo/{query}",
        reverse_url_template="http://rev/{lat}/{lon}",
        osrm_nearest_url_template="http://osrm/{lat}/{lon}",
        request_delay_seconds=0.0,
        timeout_seconds=0.1,
        max_enrich=0,
        no_neighborhood_update=False,
        save_every=1,
        resume=False,
        http_retries=0,
        geocode_failures_output="",
        retry_failures_from="",
    )
    assert code2 == 0
    assert clean.read_clean_rows(out_csv)[0].lat

    # DB-success branch where external resolvers are skipped by satisfied lat/lon.
    monkeypatch.setattr(clean, "resolve_address_sqlite", lambda *_a, **_k: (53.4, -113.4, "sqlite:exact"))
    code3 = clean.run_enrich(
        input_path=in_csv,
        output_path=out_csv,
        local_db_path=str(db_file),
        skip_local_db_resolver=False,
        skip_external_geocoder=False,
        skip_geocode_fallback=False,
        resolve_url_template="http://resolver/{query}",
        geocode_url_template="http://geo/{query}",
        reverse_url_template="http://rev/{lat}/{lon}",
        osrm_nearest_url_template="",
        request_delay_seconds=0.0,
        timeout_seconds=0.1,
        max_enrich=0,
        no_neighborhood_update=True,
        save_every=0,
        resume=False,
        http_retries=0,
        geocode_failures_output="",
        retry_failures_from="",
    )
    assert code3 == 0


def test_census_helper_functions_and_main(monkeypatch, tmp_path: Path, capsys) -> None:
    assert census.normalize_text(" A  B ") == "a b"
    df = pd.DataFrame({"A": ["1"]})
    assert census.first_existing_column(df, ["a"]) == "A"
    assert census.to_numeric(pd.DataFrame({"x": ["2"]}), ["x"])["x"].iloc[0] == 2
    assert census._ring_area_m2([[0, 0], [0, 1], [1, 1], [1, 0]]) > 0
    assert census._polygon_area_m2([]) == 0.0
    assert census._approx_geojson_area_m2({"type": "Unknown", "coordinates": [1]}) == 0.0

    pop = pd.DataFrame(
        {
            "neighbourhood_number": [1],
            "neighbourhood": ["Downtown"],
            "ward": ["1"],
            "characteristic": ["Population, 2021"],
            "question_type": ["Population"],
            "gender": ["Total"],
            "value": [100],
        }
    )
    hh = pd.DataFrame(
        {
            "neighbourhood_number": [1, 1],
            "neighbourhood": ["Downtown", "Downtown"],
            "ward": ["1", "1"],
            "question_type": ["Household size", "Household size"],
            "characteristic": ["1 person", "2 persons"],
            "value": [10, 20],
        }
    )
    assert not census.choose_population(pop).empty
    assert not census.choose_households(hh).empty
    pop_income = pd.DataFrame(
        {
            "neighbourhood_number": [1],
            "neighbourhood": ["Downtown"],
            "ward": ["1"],
            "characteristic": ["Median household income"],
            "question_type": ["Income"],
            "gender": ["Total"],
            "value": [50000],
        }
    )
    income, helper = census.choose_income(pop_income)
    assert not income.empty and not helper.empty

    boundaries = pd.DataFrame(
        {
            "neighbourhood_number": [1],
            "neighbourhood": ["Downtown"],
            "the_geom": [{"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0]]]}],
        }
    )
    assert not census.compute_area_sq_km(boundaries).empty

    current = pd.DataFrame({"name": ["Downtown"], "neighbourhood_number": [1], "civic_ward_name": ["1"]})
    seq = [pop, hh, boundaries, current]
    monkeypatch.setattr(census, "fetch_socrata_all", lambda *_a, **_k: seq.pop(0))
    out = tmp_path / "out.csv"
    helper_out = tmp_path / "helper.csv"
    monkeypatch.setattr(sys, "argv", ["builder.py", "--out", str(out), "--income-helper", str(helper_out)])
    census.main()
    assert out.exists() and helper_out.exists()
    printed = capsys.readouterr().out
    assert "Wrote" in printed


def test_census_fetch_and_fallback_branches(monkeypatch, tmp_path: Path, capsys) -> None:
    batches = [[{"a": 1}], []]

    class R:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    monkeypatch.setattr(census.session, "get", lambda *_a, **_k: R(batches.pop(0)))
    out = census.fetch_socrata_all("x")
    assert len(out) == 1
    batches2 = [[{"a": 1}], []]
    monkeypatch.setattr(census.session, "get", lambda *_a, **_k: R(batches2.pop(0)))
    out2 = census.fetch_socrata_all("x", select="a", where="a is not null")
    assert len(out2) == 1

    # choose_* branches for missing columns.
    assert census.choose_population(pd.DataFrame({"x": [1]})).empty
    assert census.choose_households(pd.DataFrame({"x": [1]})).empty
    income, helper = census.choose_income(pd.DataFrame({"x": [1]}))
    assert income.empty and helper.empty
    assert census.compute_area_sq_km(pd.DataFrame({"x": [1]})).empty
    assert census._ring_area_m2([[0, 0], [1, 1]]) == 0.0

    # main() no-area/no-income notice branches
    pop = pd.DataFrame({"neighbourhood_number": [1], "neighbourhood": ["D"], "ward": ["1"], "characteristic": ["Population"], "question_type": ["Population"], "gender": ["Total"], "value": [1]})
    hh = pd.DataFrame({"x": [1]})
    boundaries = pd.DataFrame({"x": [1]})
    current = pd.DataFrame({"name": ["D"], "neighbourhood_number": [1], "civic_ward_name": ["1"]})
    seq = [pop, hh, boundaries, current]
    monkeypatch.setattr(census, "fetch_socrata_all", lambda *_a, **_k: seq.pop(0))
    monkeypatch.setattr(
        census,
        "choose_income",
        lambda _df: (
            pd.DataFrame({"neighbourhood_number": [1], "median_household_income_2020_cad": [float("nan")], "income_characteristic": [None]}),
            pd.DataFrame({"question_type": [], "characteristic": []}),
        ),
    )
    monkeypatch.setattr(
        census,
        "compute_area_sq_km",
        lambda _df: pd.DataFrame({"neighbourhood_number": [1], "area_sq_km": [float("nan")]}),
    )
    monkeypatch.setattr(sys, "argv", ["builder.py", "--out", str(tmp_path / "o.csv"), "--income-helper", str(tmp_path / "h.csv")])
    census.main()
    txt = capsys.readouterr().out
    assert "Area could not be calculated" in txt
    assert "No income rows were auto-selected" in txt


def test_census_choose_population_and_households_fallback_paths() -> None:
    pop_df = pd.DataFrame(
        {
            "neighbourhood_number": [1],
            "neighbourhood": ["D"],
            "ward": ["1"],
            "total_population": [123],
        }
    )
    out = census.choose_population(pop_df)
    assert out.iloc[0]["population_2021"] == 123

    hh_df = pd.DataFrame(
        {
            "neighbourhood_number": [1],
            "neighbourhood": ["D"],
            "ward": ["1"],
            "question_type": ["Households"],
            "characteristic": ["Private households"],
            "gender": ["Total"],
            "value": [50],
        }
    )
    out2 = census.choose_households(hh_df)
    assert out2.iloc[0]["households_2021"] == 50


def test_census_compute_area_with_fake_projection_modules(monkeypatch) -> None:
    class FakeGeom:
        area = 10_000.0

    class FakeTransformer:
        @staticmethod
        def from_crs(*_a, **_k):
            return types.SimpleNamespace(transform=lambda x, y: (x, y))

    fake_shape_mod = types.SimpleNamespace(shape=lambda _g: FakeGeom())
    fake_ops_mod = types.SimpleNamespace(transform=lambda _fn, geom: geom)
    fake_pyproj = types.SimpleNamespace(Transformer=FakeTransformer)

    monkeypatch.setitem(sys.modules, "shapely", types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "shapely.geometry", fake_shape_mod)
    monkeypatch.setitem(sys.modules, "shapely.ops", fake_ops_mod)
    monkeypatch.setitem(sys.modules, "pyproj", fake_pyproj)

    boundaries = pd.DataFrame(
        {
            "neighbourhood_number": [1],
            "neighbourhood": ["D"],
            "the_geom": [{"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0]]]}],
        }
    )
    out = census.compute_area_sq_km(boundaries)
    assert not out.empty


def test_clean_and_census_main_guards_via_run_module(monkeypatch, tmp_path: Path) -> None:
    import runpy
    import requests

    monkeypatch.chdir(tmp_path)

    # clean_realtor_cards __main__
    in_csv = tmp_path / "cards.csv"
    in_csv.write_text(
        "neighbourhood,listing_url,address,price,beds,baths,sqft,raw_text\n"
        "N,https://www.realtor.ca/real-estate/1,123 MAIN ST,$1,1,1,100,t\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clean_realtor_cards.py",
            "parse",
            "--input",
            str(in_csv),
            "--output",
            str(tmp_path / "parsed.csv"),
        ],
    )
    sys.modules.pop("scripts.clean_realtor_cards", None)
    with pytest.raises(SystemExit):
        runpy.run_module("scripts.clean_realtor_cards", run_name="__main__")

    # census builder __main__
    pop = [{"neighbourhood_number": 1, "neighbourhood": "D", "ward": "1", "characteristic": "Population", "question_type": "Population", "gender": "Total", "value": 1}]
    hh = [{"x": 1}]
    bounds = [{"x": 1}]
    current = [{"name": "D", "neighbourhood_number": 1, "civic_ward_name": "1"}]

    class Resp:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def fake_get(self, _url, params=None, timeout=None):  # noqa: ARG001
        params = params or {}
        if int(params.get("$offset", 0) or 0) > 0:
            payload = []
        elif "eg3i-f4bj" in _url:
            payload = pop
        elif "xgkv-ii9t" in _url:
            payload = hh
        elif "5bk4-5txu" in _url:
            payload = bounds
        elif "65fr-66s6" in _url:
            payload = current
        else:
            payload = []
        return Resp(payload)

    monkeypatch.setattr(requests.Session, "get", fake_get)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "edmonton_neighbourhood_census_builder.py",
            "--out",
            str(tmp_path / "census.csv"),
            "--income-helper",
            str(tmp_path / "income.csv"),
        ],
    )
    sys.modules.pop("scripts.edmonton_neighbourhood_census_builder", None)
    runpy.run_module("scripts.edmonton_neighbourhood_census_builder", run_name="__main__")
    assert (tmp_path / "census.csv").exists()


def test_shadow_script_helpers_and_main(monkeypatch, tmp_path: Path, capsys) -> None:
    row = shadow._property_row(1, house_number="1000", street_name="MAIN ST")
    assert row["canonical_location_id"] == "loc-0001"

    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    assert len(shadow._read_csv_sample(csv_path, limit=1)) == 1

    monkeypatch.setattr(shadow, "_seed_db", lambda: None)
    monkeypatch.setattr(shadow, "DB_PATH", tmp_path / "db.sqlite")
    monkeypatch.setattr(shadow, "LISTINGS_PATH", tmp_path / "listings.json")
    monkeypatch.setattr(shadow, "PERMITS_PATH", tmp_path / "permits.json")
    monkeypatch.setattr(shadow, "AMBIGUOUS_PATH", tmp_path / "amb.csv")
    monkeypatch.setattr(shadow, "SUMMARY_PATH", tmp_path / "summary.json")
    monkeypatch.setattr(shadow, "ROOT", tmp_path)

    review_a = tmp_path / "a.csv"
    review_b = tmp_path / "b.csv"
    review_a.write_text("x,y\n1,2\n", encoding="utf-8")
    review_b.write_text("x,y\n3,4\n", encoding="utf-8")

    run_payload = {
        "run_id": "r1",
        "promotion": {"promotion_disabled": True},
        "report": {
            "shadow_run_summary": {"ok": True},
            "real_feed_readiness_checklist": [],
            "review_exports": {"a": str(review_a), "b": str(review_b)},
        },
    }

    monkeypatch.setattr(
        shadow.subprocess,
        "run",
        lambda *_a, **_k: types.SimpleNamespace(stdout=json.dumps(run_payload)),
    )

    class FakeConn:
        def execute(self, sql, params=None):
            if "property_attributes_prod" in sql:
                return types.SimpleNamespace(fetchone=lambda: [0])
            if "property_attributes_shadow" in sql:
                return types.SimpleNamespace(fetchone=lambda: [1])
            return types.SimpleNamespace(fetchone=lambda: [2])

        def close(self):
            return None

    monkeypatch.setattr(shadow, "connect", lambda _p: FakeConn())
    shadow.main()
    out = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert out["run_id"] == "r1"
    assert "promotion_confirmation" in out
    assert '"run_id": "r1"' in capsys.readouterr().out


def test_shadow_seed_db_creates_artifacts(monkeypatch, tmp_path: Path) -> None:
    proof = tmp_path / "proof"
    monkeypatch.setattr(shadow, "PROOF_DIR", proof)
    monkeypatch.setattr(shadow, "INPUT_DIR", proof / "input")
    monkeypatch.setattr(shadow, "REVIEW_DIR", proof / "review")
    monkeypatch.setattr(shadow, "DB_PATH", proof / "shadow.db")
    monkeypatch.setattr(shadow, "LISTINGS_PATH", proof / "input" / "listings.json")
    monkeypatch.setattr(shadow, "PERMITS_PATH", proof / "input" / "permits.json")
    monkeypatch.setattr(shadow, "AMBIGUOUS_PATH", proof / "amb.csv")
    shadow._seed_db()
    assert (proof / "shadow.db").exists()
    assert (proof / "input" / "listings.json").exists()
    assert (proof / "input" / "permits.json").exists()


def test_shadow_seed_db_existing_dir_and_main_guard(monkeypatch, tmp_path: Path) -> None:
    proof = tmp_path / "proof2"
    proof.mkdir()
    (proof / "old.txt").write_text("x", encoding="utf-8")
    monkeypatch.setattr(shadow, "PROOF_DIR", proof)
    monkeypatch.setattr(shadow, "INPUT_DIR", proof / "input")
    monkeypatch.setattr(shadow, "REVIEW_DIR", proof / "review")
    monkeypatch.setattr(shadow, "DB_PATH", proof / "shadow.db")
    monkeypatch.setattr(shadow, "LISTINGS_PATH", proof / "input" / "listings.json")
    monkeypatch.setattr(shadow, "PERMITS_PATH", proof / "input" / "permits.json")
    monkeypatch.setattr(shadow, "AMBIGUOUS_PATH", proof / "amb.csv")
    shadow._seed_db()
    assert not (proof / "old.txt").exists()


def test_bed_bath_main_and_manual_main(monkeypatch, tmp_path: Path) -> None:
    # bed_bath main
    out_csv = tmp_path / "bed.csv"
    monkeypatch.setattr(bed, "OUTPUT_CSV", str(out_csv))
    monkeypatch.setattr(bed, "fetch_edmonton_neighbourhoods", lambda: ["A", "B"])
    monkeypatch.setattr(
        bed,
        "get_listing_links_for_neighbourhood",
        lambda _p, n: ["https://www.realtor.ca/real-estate/1"] if n != "Downtown" else (_ for _ in ()).throw(RuntimeError("x")),
    )
    monkeypatch.setattr(
        bed,
        "scrape_listing",
        lambda _p, _u: bed.ListingRow(neighbourhood="", listing_url=_u, address="A", price="$1", beds="1", baths="1"),
    )
    monkeypatch.setattr(bed.time, "sleep", lambda _s: None)

    class BedPage:
        def set_extra_http_headers(self, _h):
            return None

    class BedContext:
        def new_page(self):
            return BedPage()

        def close(self):
            return None

    class BedBrowser:
        def new_context(self, **_k):
            return BedContext()

        def close(self):
            return None

    class BedPlay:
        chromium = types.SimpleNamespace(launch=lambda **_k: BedBrowser())

    class BedCM:
        def __enter__(self):
            return BedPlay()

        def __exit__(self, *_a):
            return None

    monkeypatch.setattr(bed, "sync_playwright", lambda: BedCM())
    bed.main()
    assert out_csv.exists()

    # manual_bed_bath main
    m_out = tmp_path / "manual.csv"
    m_prog = tmp_path / "progress.txt"
    monkeypatch.setattr(manual, "OUT_CSV", str(m_out))
    monkeypatch.setattr(manual, "PROGRESS_FILE", str(m_prog))
    monkeypatch.setattr(manual, "FORCE_REDO", set())
    monkeypatch.setattr(manual, "START_FROM", "")
    monkeypatch.setattr(manual, "fetch_edmonton_neighbourhoods", lambda: ["N1", "N2", "N3"])
    monkeypatch.setattr(
        manual,
        "extract_rows_from_current_page",
        lambda _p, n: [{"neighbourhood": n, "price": "$1", "address": f"{n} A", "beds": "1", "baths": "1", "sqft": "100", "listing_url": f"https://x/{n}", "raw_text": "t"}],
    )
    inputs = iter(["", "s", "q"])
    monkeypatch.setattr("builtins.input", lambda _p: next(inputs))

    class MPage:
        url = "http://x"

        def title(self):
            return "t"

        def wait_for_timeout(self, _ms):
            return None

    class MContext:
        pages = [MPage()]

        def new_page(self):
            return MPage()

    class MBrowser:
        contexts = [MContext()]

    class MPlay:
        chromium = types.SimpleNamespace(connect_over_cdp=lambda _u: MBrowser())

    class MCM:
        def __enter__(self):
            return MPlay()

        def __exit__(self, *_a):
            return None

    monkeypatch.setattr(manual, "sync_playwright", lambda: MCM())
    manual.main()
    assert m_out.exists()
    assert m_prog.exists()


def test_script_main_guards_via_run_module(monkeypatch, tmp_path: Path) -> None:
    import runpy
    import playwright.sync_api as ps

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", [p for p in sys.path if p != str(ROOT)])

    # bed_bath main guard
    class RespData:
        def __init__(self, is_data: bool):
            self._is_data = is_data
            self.text = ""

        def raise_for_status(self):
            return None

        def json(self):
            if self._is_data:
                return [{"name_mixed": "Downtown"}]
            return []

    call_counter = {"n": 0}

    def fake_requests_get(url, *_a, **_k):
        call_counter["n"] += 1
        return RespData("3b6m-fezs" in url)

    monkeypatch.setattr("requests.get", fake_requests_get)
    monkeypatch.setattr("time.sleep", lambda _s: None)

    class BPage:
        def goto(self, *_a, **_k):
            return None

        def wait_for_timeout(self, *_a, **_k):
            return None

        def set_extra_http_headers(self, *_a, **_k):
            return None

        def content(self):
            return ('"/real-estate/111" ' * 400)

    class BCtx:
        def new_page(self):
            return BPage()

        def close(self):
            return None

    class BBrowser:
        def new_context(self, **_k):
            return BCtx()

        def close(self):
            return None

    class BPlay:
        chromium = types.SimpleNamespace(launch=lambda **_k: BBrowser())

    class BCM:
        def __enter__(self):
            return BPlay()

        def __exit__(self, *_a):
            return None

    monkeypatch.setattr(ps, "sync_playwright", lambda: BCM())
    sys.modules.pop("scripts.bed_bath", None)
    runpy.run_module("scripts.bed_bath", run_name="__main__")

    # manual_bed_bath main guard
    monkeypatch.setattr("builtins.input", lambda _p: "q")

    class MPage:
        url = "http://x"

        def title(self):
            return "t"

    class MContext:
        pages = [MPage()]

        def new_page(self):
            return MPage()

    class MBrowser:
        contexts = [MContext()]

    class MPlay:
        chromium = types.SimpleNamespace(connect_over_cdp=lambda _u: MBrowser())

    class MCM:
        def __enter__(self):
            return MPlay()

        def __exit__(self, *_a):
            return None

    monkeypatch.setattr(ps, "sync_playwright", lambda: MCM())
    sys.modules.pop("scripts.manual_bed_bath", None)
    runpy.run_module("scripts.manual_bed_bath", run_name="__main__")

    # run_bedbath_shadow_proof main guard
    fake_result = {
        "run_id": "rg",
        "promotion": {"promotion_disabled": True},
        "report": {
            "shadow_run_summary": {},
            "real_feed_readiness_checklist": [],
            "review_exports": {},
        },
    }
    monkeypatch.setattr(
        "subprocess.run",
        lambda *_a, **_k: types.SimpleNamespace(stdout=json.dumps(fake_result)),
    )
    sys.modules.pop("scripts.run_bedbath_shadow_proof", None)
    runpy.run_module("scripts.run_bedbath_shadow_proof", run_name="__main__")
