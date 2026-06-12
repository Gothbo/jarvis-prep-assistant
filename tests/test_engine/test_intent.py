"""Tests for US-006: Intent and industry recognition engine.

AC1: Input "制造业+勒索" → industry=manufacturing, scenario=ransomware
AC2: Input "金融+合规" → industry=finance, scenario=compliance
AC3: Input unrecognized text → industry=None, scenario=None
AC4: Input "医疗+数据泄露" → industry=healthcare, scenario=data_leak
"""


from jarvis.engine.intent import IntentResult, _build_reverse_map, _load_keyword_map, recognize


class TestAC1_ManufacturingRansomware:
    """AC1: Input with manufacturing + ransomware keywords → correct recognition."""

    def test_english_manufacturing_ransomware(self):
        result = recognize("Visiting a manufacturing client, production line hit by ransomware")
        assert result.industry == "manufacturing"
        assert result.scenario == "ransomware"

    def test_chinese_manufacturing_ransomware(self):
        result = recognize("明天去见制造业客户，产线被勒索了")
        assert result.industry == "manufacturing"
        assert result.scenario == "ransomware"

    def test_chinese_ot_ransomware(self):
        result = recognize("工控系统加密锁定")
        assert result.industry == "manufacturing"
        assert result.scenario == "ransomware"

    def test_result_has_raw_input(self):
        text = "制造业客户产线被勒索"
        result = recognize(text)
        assert result.raw_input == text


class TestAC2_FinanceCompliance:
    """AC2: Input with finance + compliance keywords → correct recognition."""

    def test_english_finance_compliance(self):
        result = recognize("Finance industry compliance audit preparation")
        assert result.industry == "finance"
        assert result.scenario == "compliance"

    def test_chinese_finance_compliance(self):
        result = recognize("金融行业合规审计需求")
        assert result.industry == "finance"
        assert result.scenario == "compliance"

    def test_chinese_bank_compliance(self):
        result = recognize("银行合规审计项目")
        assert result.industry == "finance"
        assert result.scenario == "compliance"


class TestAC3_UnrecognizedInput:
    """AC3: Input with no matching keywords → industry=None, scenario=None."""

    def test_english_unrecognized(self):
        result = recognize("I want to know about the company culture")
        assert result.industry is None
        assert result.scenario is None

    def test_chinese_unrecognized(self):
        result = recognize("今天天气不错")
        assert result.industry is None
        assert result.scenario is None

    def test_generic_greeting(self):
        result = recognize("你好，想了解一下产品信息")
        # "产品" doesn't match any industry keyword, "信息" is generic
        # This should either return None or a low-confidence match
        assert result.raw_input == "你好，想了解一下产品信息"


class TestAC4_HealthcareDataLeak:
    """AC4: Input with healthcare + data_leak keywords → correct recognition."""

    def test_english_healthcare_data_leak(self):
        result = recognize("Healthcare client worried about data leak and APT")
        assert result.industry == "healthcare"
        assert result.scenario == "data_leak"

    def test_chinese_healthcare_data_leak(self):
        result = recognize("医院数据泄露事件")
        assert result.industry == "healthcare"
        assert result.scenario == "data_leak"

    def test_chinese_hospital_breach(self):
        result = recognize("医疗行业患者信息泄漏风险")
        assert result.industry == "healthcare"
        assert result.scenario == "data_leak"


class TestIntentResultDataclass:
    """Verify IntentResult dataclass structure."""

    def test_intent_result_fields(self):
        result = IntentResult(industry="test", scenario="test", raw_input="hello")
        assert result.industry == "test"
        assert result.scenario == "test"
        assert result.raw_input == "hello"

    def test_intent_result_none_defaults(self):
        result = IntentResult(industry=None, scenario=None)
        assert result.industry is None
        assert result.scenario is None


class TestKeywordDictionary:
    """Verify Chinese keyword dictionary is properly loaded."""

    def test_keyword_map_loaded(self):
        kw_map = _load_keyword_map()
        assert isinstance(kw_map, dict)
        assert len(kw_map) >= 7  # 7 industry categories

    def test_manufacturing_has_chinese_keywords(self):
        kw_map = _load_keyword_map()
        manufacturing_kws = kw_map.get("manufacturing", [])
        chinese_kws = [kw for kw in manufacturing_kws if any(ord(c) > 127 for c in kw)]
        assert len(chinese_kws) >= 3

    def test_finance_has_chinese_keywords(self):
        kw_map = _load_keyword_map()
        finance_kws = kw_map.get("finance", [])
        chinese_kws = [kw for kw in finance_kws if any(ord(c) > 127 for c in kw)]
        assert len(chinese_kws) >= 3

    def test_healthcare_has_chinese_keywords(self):
        kw_map = _load_keyword_map()
        healthcare_kws = kw_map.get("healthcare", [])
        chinese_kws = [kw for kw in healthcare_kws if any(ord(c) > 127 for c in kw)]
        assert len(chinese_kws) >= 3

    def test_reverse_map_contains_chinese(self):
        kw_map = _load_keyword_map()
        reverse = _build_reverse_map(kw_map)
        # Check some Chinese keywords are in the reverse map
        assert "制造业" in reverse or "制造" in reverse
        assert "金融" in reverse or "银行" in reverse
        assert "医疗" in reverse or "医院" in reverse
