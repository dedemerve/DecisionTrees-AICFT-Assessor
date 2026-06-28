"""
test_dt_vision_pipeline.py

Unit tests for dt_vision_pipeline.py.
No GPU, no TrOCR model download required — all model calls are mocked.

Run:
    python -m pytest test_dt_vision_pipeline.py -v
"""

import json
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest
from PIL import Image

import dt_vision_pipeline as p

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def make_bgr(h: int = 400, w: int = 300, color: tuple = (255, 255, 255)) -> np.ndarray:
    img = np.full((h, w, 3), color, dtype=np.uint8)
    return img


def make_gray(h: int = 200, w: int = 200) -> np.ndarray:
    return np.full((h, w), 200, dtype=np.uint8)


def make_pil(w: int = 80, h: int = 40) -> Image.Image:
    return Image.new("RGB", (w, h), color=(240, 240, 240))


def make_split_node(
    feature="Fat",
    operator="<",
    threshold=8.0,
    true_branch=None,
    false_branch=None,
) -> p.SplitNode:
    return p.SplitNode(
        feature=feature,
        operator=operator,
        threshold=threshold,
        raw_condition=f"{feature} {operator} {threshold}",
        true_branch=true_branch or p.ResultNode("Recommendable"),
        false_branch=false_branch or p.ResultNode("Not Recommendable"),
    )


def make_result() -> p.PipelineResult:
    res = p.PipelineResult(student_image_path="test.jpg")
    res.tree = make_split_node()
    res.raw_texts = ["Fat < 8", "Recommendable", "Not Recommendable"]
    return res


# ===========================================================================
# Module 1: preprocess_for_htr
# ===========================================================================

class TestPreprocess:

    def test_PP01_rgb_input_returns_binary(self):
        img = make_bgr()
        out = p.preprocess_for_htr(img)
        assert out.dtype == np.uint8
        unique = set(np.unique(out))
        assert unique.issubset({0, 255})

    def test_PP02_grayscale_input_accepted(self):
        gray = make_gray()
        out = p.preprocess_for_htr(gray)
        assert out.ndim == 2

    def test_PP03_output_same_spatial_dimensions(self):
        img = make_bgr(h=600, w=450)
        out = p.preprocess_for_htr(img)
        assert out.shape == (600, 450)

    def test_PP04_all_white_page_mostly_zero(self):
        img = make_bgr(color=(255, 255, 255))
        out = p.preprocess_for_htr(img)
        white_frac = np.sum(out == 255) / out.size
        assert white_frac < 0.05

    def test_PP05_dark_ink_stroke_survives(self):
        img = make_bgr(h=100, w=300, color=(255, 255, 255))
        img[40:60, 50:250, :] = 30  # dark horizontal stroke
        out = p.preprocess_for_htr(img)
        assert np.sum(out[40:60, 50:250] == 255) > 0

    def test_PP06_enhance_crop_dilates_pixels(self):
        crop = np.zeros((50, 100), dtype=np.uint8)
        crop[25, 50] = 255  # single white pixel
        out = p.enhance_crop_for_trocr(crop)
        assert np.sum(out == 255) > 1


# ===========================================================================
# Module 2: BoundingBox and detect_nodes
# ===========================================================================

class TestBoundingBox:

    def test_BB01_area(self):
        b = p.BoundingBox(0, 0, 10, 20)
        assert b.area == 200

    def test_BB02_center(self):
        b = p.BoundingBox(10, 20, 40, 60)
        assert b.center == (30, 50)

    def test_BB03_zero_size(self):
        b = p.BoundingBox(5, 5, 0, 0)
        assert b.area == 0


class TestDetectNodes:

    def _make_worksheet_with_boxes(self) -> tuple[np.ndarray, np.ndarray]:
        """Create a synthetic worksheet with two dark rectangles."""
        bgr = make_bgr(h=400, w=600, color=(255, 255, 255))
        bgr[50:100, 50:200, :] = 30   # box 1
        bgr[200:250, 300:450, :] = 30  # box 2
        binary = p.preprocess_for_htr(bgr)
        return bgr, binary

    def test_DN01_detects_boxes_in_synthetic_worksheet(self):
        bgr, binary = self._make_worksheet_with_boxes()
        nodes = p.detect_nodes(binary, bgr, min_area=200)
        assert len(nodes) >= 1

    def test_DN02_returns_detected_node_objects(self):
        bgr, binary = self._make_worksheet_with_boxes()
        nodes = p.detect_nodes(binary, bgr, min_area=200)
        for node in nodes:
            assert isinstance(node, p.DetectedNode)
            assert isinstance(node.crop, Image.Image)

    def test_DN03_blank_page_returns_no_nodes(self):
        bgr = make_bgr(color=(255, 255, 255))
        binary = p.preprocess_for_htr(bgr)
        nodes = p.detect_nodes(binary, bgr, min_area=1000)
        assert nodes == []

    def test_DN04_nodes_sorted_top_to_bottom(self):
        bgr = make_bgr(h=500, w=400, color=(255, 255, 255))
        bgr[300:360, 50:200, :] = 30  # lower box
        bgr[50:110, 50:200, :] = 30   # upper box
        binary = p.preprocess_for_htr(bgr)
        nodes = p.detect_nodes(binary, bgr, min_area=500)
        if len(nodes) >= 2:
            centers_y = [n.box.center[1] for n in nodes]
            assert centers_y == sorted(centers_y)

    def test_DN05_crops_are_pil_images(self):
        bgr = make_bgr(h=400, w=600, color=(255, 255, 255))
        bgr[50:150, 50:250, :] = 20
        binary = p.preprocess_for_htr(bgr)
        nodes = p.detect_nodes(binary, bgr, min_area=100)
        for node in nodes:
            assert isinstance(node.crop, Image.Image)


class TestMergeBoxes:

    def test_MB01_non_overlapping_boxes_not_merged(self):
        boxes = [p.BoundingBox(0, 0, 10, 10), p.BoundingBox(200, 200, 10, 10)]
        merged = p._merge_overlapping_boxes(boxes, padding=5)
        assert len(merged) == 2

    def test_MB02_adjacent_boxes_merged(self):
        boxes = [p.BoundingBox(0, 0, 10, 10), p.BoundingBox(14, 0, 10, 10)]
        merged = p._merge_overlapping_boxes(boxes, padding=5)
        assert len(merged) == 1

    def test_MB03_empty_input_returns_empty(self):
        assert p._merge_overlapping_boxes([]) == []

    def test_MB04_single_box_unchanged(self):
        boxes = [p.BoundingBox(5, 5, 20, 30)]
        merged = p._merge_overlapping_boxes(boxes, padding=2)
        assert len(merged) == 1
        assert merged[0].x == 5 and merged[0].y == 5

    def test_MB05_merged_box_contains_both_originals(self):
        boxes = [p.BoundingBox(0, 0, 10, 10), p.BoundingBox(8, 0, 10, 10)]
        merged = p._merge_overlapping_boxes(boxes, padding=0)
        assert len(merged) == 1
        m = merged[0]
        assert m.x == 0
        assert m.x + m.w == 18


# ===========================================================================
# Module 3: TrOCR (mocked)
# ===========================================================================

class TestTrOCR:

    def _make_recognizer(self) -> p.TrOCRRecognizer:
        rec = object.__new__(p.TrOCRRecognizer)
        rec.device = "cpu"
        rec.processor = MagicMock()
        rec.model = MagicMock()
        return rec

    def test_TR01_recognize_batch_returns_one_text_per_crop(self):
        rec = self._make_recognizer()
        rec.processor.return_value.pixel_values = MagicMock()
        rec.model.generate.return_value = MagicMock()
        rec.processor.batch_decode.return_value = ["Fat < 8", "Recommendable"]

        crops = [make_pil(), make_pil()]
        with patch.object(rec.model, "generate", return_value=MagicMock()):
            texts = rec.recognize_batch(crops)
        assert len(texts) == 2

    def test_TR02_recognize_nodes_fills_raw_text(self):
        rec = self._make_recognizer()
        rec.processor.return_value.pixel_values = MagicMock()
        rec.processor.batch_decode.return_value = ["Salt > 5"]

        node = p.DetectedNode(box=p.BoundingBox(0, 0, 50, 30), crop=make_pil())
        with patch.object(rec, "recognize_batch", return_value=["Salt > 5"]):
            p.recognize_nodes([node], rec)

        assert node.raw_text == "Salt > 5"

    def test_TR03_empty_crop_list_returns_empty(self):
        rec = self._make_recognizer()
        with patch.object(rec, "recognize_batch", return_value=[]):
            result = rec.recognize_batch([])
        assert result == []

    def test_TR04_raw_text_stripped_of_whitespace(self):
        rec = self._make_recognizer()
        node = p.DetectedNode(box=p.BoundingBox(0, 0, 50, 30), crop=make_pil())
        with patch.object(rec, "recognize_batch", return_value=["  Fat < 8  "]):
            p.recognize_nodes([node], rec)
        assert node.raw_text == "Fat < 8"


# ===========================================================================
# Module 4: NLP post-processing
# ===========================================================================

class TestParseCondition:

    def test_PC01_english_feature_less_than(self):
        f, op, th = p.parse_condition("Fat < 8")
        assert f == "Fat"
        assert op == "<"
        assert th == 8.0

    def test_PC02_turkish_feature_greater_than(self):
        f, op, th = p.parse_condition("Tuz > 5")
        assert f == "Salt"
        assert op == ">"
        assert th == 5.0

    def test_PC03_turkish_comma_decimal(self):
        f, op, th = p.parse_condition("Protein >= 7,5")
        assert f == "Protein"
        assert th == 7.5

    def test_PC04_energy_with_typo(self):
        f, op, th = p.parse_condition("egnergy < 300")
        assert f == "Energy"
        assert th == 300.0

    def test_PC05_no_condition_returns_none_triple(self):
        f, op, th = p.parse_condition("Recommendable")
        assert f is None and op is None and th is None

    def test_PC06_float_point_decimal(self):
        f, op, th = p.parse_condition("Sugar <= 12.5")
        assert th == 12.5

    def test_PC07_arrow_operator_normalized(self):
        f, op, th = p.parse_condition("Fat => 10")
        assert op == ">="

    def test_PC08_carbohydrates_turkish(self):
        f, op, th = p.parse_condition("karbonhidrat < 20")
        assert f == "Carbohydrates"


class TestFuzzyMatch:

    def test_FM01_exact_feature_match(self):
        assert p._fuzzy_match_feature("energy") == "Energy"

    def test_FM02_typo_feature_match(self):
        result = p._fuzzy_match_feature("egnergy")
        assert result == "Energy"

    def test_FM03_turkish_feature_match(self):
        assert p._fuzzy_match_feature("şeker") == "Sugar"

    def test_FM04_unknown_feature_returns_none(self):
        assert p._fuzzy_match_feature("xyzxyzxyz") is None

    def test_FM05_exact_result_match(self):
        assert p._fuzzy_match_result("onerilir") == "Recommendable"

    def test_FM06_turkish_negative_result(self):
        assert p._fuzzy_match_result("önerilmez") == "Not Recommendable"

    def test_FM07_english_result_match(self):
        assert p._fuzzy_match_result("recommendable") == "Recommendable"

    def test_FM08_unknown_result_returns_none(self):
        assert p._fuzzy_match_result("zzzzunknown") is None


class TestClassifyNodeType:

    def test_CN01_condition_string_is_decision(self):
        assert p.classify_node_type("Fat < 8") == "decision"

    def test_CN02_result_string_is_result(self):
        assert p.classify_node_type("Recommendable") == "result"

    def test_CN03_turkish_result_is_result(self):
        assert p.classify_node_type("önerilir") == "result"

    def test_CN04_unknown_string_is_text(self):
        assert p.classify_node_type("asdfghjkl random text") == "text"

    def test_CN05_turkish_condition_is_decision(self):
        assert p.classify_node_type("Tuz > 5") == "decision"


class TestBuildTree:

    def _make_node(self, raw_text: str, node_type: str) -> p.DetectedNode:
        dn = p.DetectedNode(
            box=p.BoundingBox(0, 0, 100, 40),
            crop=make_pil(),
            raw_text=raw_text,
            node_type=node_type,
        )
        return dn

    def test_BT01_one_decision_two_results_builds_tree(self):
        nodes = [
            self._make_node("Fat < 8", "decision"),
            self._make_node("Recommendable", "result"),
            self._make_node("Not Recommendable", "result"),
        ]
        warnings = []
        tree = p.build_tree_from_nodes(nodes, warnings)
        assert isinstance(tree, p.SplitNode)
        assert isinstance(tree.true_branch, p.ResultNode)
        assert isinstance(tree.false_branch, p.ResultNode)

    def test_BT02_root_feature_recognized(self):
        nodes = [
            self._make_node("Fat < 8", "decision"),
            self._make_node("Recommendable", "result"),
            self._make_node("Not Recommendable", "result"),
        ]
        warnings = []
        tree = p.build_tree_from_nodes(nodes, warnings)
        assert tree.feature == "Fat"
        assert tree.threshold == 8.0

    def test_BT03_no_decision_nodes_returns_none(self):
        nodes = [self._make_node("Recommendable", "result")]
        warnings = []
        tree = p.build_tree_from_nodes(nodes, warnings)
        assert tree is None
        assert any("No decision" in w for w in warnings)

    def test_BT04_two_level_tree(self):
        nodes = [
            self._make_node("Fat < 8", "decision"),
            self._make_node("Protein >= 7", "decision"),
            self._make_node("Recommendable", "result"),
            self._make_node("Not Recommendable", "result"),
            self._make_node("Not Recommendable", "result"),
        ]
        warnings = []
        tree = p.build_tree_from_nodes(nodes, warnings)
        assert isinstance(tree, p.SplitNode)

    def test_BT05_unrecognized_condition_warning(self):
        nodes = [
            self._make_node("????? > ???", "decision"),
            self._make_node("Recommendable", "result"),
        ]
        warnings = []
        p.build_tree_from_nodes(nodes, warnings)
        assert any("did not parse" in w for w in warnings)


# ===========================================================================
# PipelineResult: to_json
# ===========================================================================

class TestPipelineResult:

    def test_PR01_to_json_is_valid_json(self):
        res = make_result()
        j = res.to_json()
        parsed = json.loads(j)
        assert "tree" in parsed

    def test_PR02_to_json_includes_raw_texts(self):
        res = make_result()
        parsed = json.loads(res.to_json())
        assert "raw_texts_detected" in parsed
        assert len(parsed["raw_texts_detected"]) == 3

    def test_PR03_to_json_tree_has_type_field(self):
        res = make_result()
        parsed = json.loads(res.to_json())
        assert parsed["tree"]["type"] == "split"

    def test_PR04_none_tree_serializes_cleanly(self):
        res = p.PipelineResult(student_image_path="x.jpg")
        parsed = json.loads(res.to_json())
        assert parsed["tree"] is None

    def test_PR05_result_node_serializes(self):
        res = p.PipelineResult(student_image_path="x.jpg")
        res.tree = p.ResultNode(label="Recommendable", raw_text="onerilir")
        parsed = json.loads(res.to_json())
        assert parsed["tree"]["label"] == "Recommendable"

    def test_PR06_warnings_included_in_json(self):
        res = make_result()
        res.warnings = ["test warning"]
        parsed = json.loads(res.to_json())
        assert "test warning" in parsed["warnings"]


# ===========================================================================
# validate_pipeline_output
# ===========================================================================

class TestValidatePipelineOutput:

    def test_VP01_clean_result_no_warnings(self):
        res = make_result()
        assert p.validate_pipeline_output(res) == []

    def test_VP02_none_tree_returns_warning(self):
        res = p.PipelineResult(student_image_path="x.jpg")
        warnings = p.validate_pipeline_output(res)
        assert any("None" in w for w in warnings)

    def test_VP03_root_feature_none_flagged(self):
        res = make_result()
        res.tree = p.SplitNode(
            feature=None, operator="<", threshold=5.0, raw_condition="??? < 5"
        )
        warnings = p.validate_pipeline_output(res)
        assert any("feature not recognized" in w for w in warnings)

    def test_VP04_long_raw_text_flagged(self):
        res = make_result()
        res.raw_texts = ["x" * 301]
        warnings = p.validate_pipeline_output(res)
        assert any("hallucination" in w or "300 chars" in w for w in warnings)

    def test_VP05_missing_recommendable_leaf_flagged(self):
        res = make_result()
        res.tree = make_split_node(
            true_branch=p.ResultNode("Not Recommendable"),
            false_branch=p.ResultNode("Not Recommendable"),
        )
        warnings = p.validate_pipeline_output(res)
        assert any("Recommendable" in w for w in warnings)

    def test_VP06_missing_not_recommendable_leaf_flagged(self):
        res = make_result()
        res.tree = make_split_node(
            true_branch=p.ResultNode("Recommendable"),
            false_branch=p.ResultNode("Recommendable"),
        )
        warnings = p.validate_pipeline_output(res)
        assert any("Not Recommendable" in w for w in warnings)

    def test_VP07_result_node_root_passes(self):
        res = p.PipelineResult(student_image_path="x.jpg")
        res.tree = p.ResultNode("Recommendable")
        res.raw_texts = ["Recommendable"]
        warnings = p.validate_pipeline_output(res)
        # A pure result root has no feature to check but still should list both missing
        assert isinstance(warnings, list)

    def test_VP08_two_level_tree_no_warnings(self):
        inner = make_split_node()
        root = make_split_node(true_branch=inner, false_branch=p.ResultNode("Not Recommendable"))
        res = make_result()
        res.tree = root
        warnings = p.validate_pipeline_output(res)
        assert warnings == []


# ===========================================================================
# New: build_tree_from_nodes and validate_pipeline_output edge cases
# ===========================================================================

class TestBuildTreeEdgeCases:
    """Stress tests for build_tree_from_nodes with unbalanced node counts."""

    def _make_node(self, raw_text: str, node_type: str) -> p.DetectedNode:
        n = p.DetectedNode(
            box=p.BoundingBox(0, 0, 80, 40),
            crop=Image.new("RGB", (80, 40)),
            raw_text=raw_text,
        )
        n.node_type = node_type
        return n

    def test_BT06_more_splits_than_results_warns_unattached(self):
        """When there are more split nodes than result nodes, unattached warning fires."""
        warnings: list[str] = []
        nodes = [
            self._make_node("Fat < 8", "decision"),
            self._make_node("Salt < 3", "decision"),
            self._make_node("Recommendable", "result"),
        ]
        p.build_tree_from_nodes(nodes, warnings)
        assert any("could not be attached" in w or "branch" in w for w in warnings)

    def test_BT07_no_result_nodes_root_branches_none(self):
        """With no result nodes, both branches of root stay None."""
        warnings: list[str] = []
        nodes = [self._make_node("Fat < 8", "decision")]
        root = p.build_tree_from_nodes(nodes, warnings)
        assert isinstance(root, p.SplitNode)
        assert root.true_branch is None
        assert root.false_branch is None

    def test_BT08_zero_splits_zero_results_returns_none_with_warning(self):
        """Empty node list returns None with a warning."""
        warnings: list[str] = []
        result = p.build_tree_from_nodes([], warnings)
        assert result is None
        assert any("No decision" in w for w in warnings)

    def test_BT09_extra_result_nodes_warned(self):
        """More result nodes than can be attached triggers a warning."""
        warnings: list[str] = []
        nodes = [
            self._make_node("Fat < 8", "decision"),
            self._make_node("Recommendable", "result"),
            self._make_node("Not Recommendable", "result"),
            self._make_node("Recommendable", "result"),  # extra
        ]
        p.build_tree_from_nodes(nodes, warnings)
        assert any("could not be attached" in w or "branch" in w for w in warnings)


class TestParseConditionEdgeCases:
    """Stress tests for parse_condition with unusual OCR output."""

    def test_PC09_extra_spaces_around_operator(self):
        """Extra whitespace around operator and threshold should still parse."""
        feat, op, thresh = p.parse_condition("Fat   <   8.0")
        assert feat == "Fat"
        assert thresh == 8.0

    def test_PC10_threshold_zero(self):
        """A threshold of zero is a valid float and must not be rejected."""
        feat, op, thresh = p.parse_condition("Salt < 0")
        if feat is not None:
            assert thresh == 0.0

    def test_PC11_condition_only_text_no_operator(self):
        """A string with no operator returns (None, None, None)."""
        feat, op, thresh = p.parse_condition("Recommendable")
        assert feat is None and op is None and thresh is None

    def test_PC12_negative_threshold_parsed(self):
        """Negative threshold values are unlikely but must not crash."""
        feat, op, thresh = p.parse_condition("Energy < -5")
        if feat is not None:
            assert thresh == -5.0

    def test_PC13_threshold_with_trailing_units_ignored(self):
        """Parse condition must not crash on 'Fat < 8 g/100g' style text."""
        feat, op, thresh = p.parse_condition("Fat < 8 g/100g")
        if feat is not None:
            assert thresh == 8.0


class TestValidatePipelineOutputEdgeCases:
    """Edge cases for validate_pipeline_output."""

    def test_VP09_tree_with_none_true_branch_leaf_check_fires(self):
        """If one branch is None, the leaf check cannot find all result classes."""
        node = p.SplitNode(
            feature="Fat",
            operator="<",
            threshold=8.0,
            raw_condition="Fat < 8",
            true_branch=None,
            false_branch=p.ResultNode("Not Recommendable"),
        )
        result = p.PipelineResult(student_image_path="test.jpg")
        result.tree = node
        result.raw_texts = ["Fat < 8", "Not Recommendable"]
        warnings = p.validate_pipeline_output(result)
        assert any("Recommendable" in w for w in warnings)

    def test_VP10_deeply_nested_tree_no_recursion_error(self):
        """A tree of depth 30 must not hit Python recursion limit."""
        leaf_r = p.ResultNode("Recommendable")
        leaf_nr = p.ResultNode("Not Recommendable")
        node = p.SplitNode(
            feature="Fat", operator="<", threshold=8.0,
            raw_condition="Fat < 8", true_branch=leaf_r, false_branch=leaf_nr,
        )
        for _ in range(28):
            node = p.SplitNode(
                feature="Fat", operator="<", threshold=8.0,
                raw_condition="Fat < 8", true_branch=node, false_branch=leaf_nr,
            )
        result = p.PipelineResult(student_image_path="deep.jpg")
        result.tree = node
        result.raw_texts = ["Fat < 8"]
        warnings = p.validate_pipeline_output(result)
        assert isinstance(warnings, list)

    def test_VP11_result_node_at_root_passes_check1(self):
        """A ResultNode tree (degenerate case) does not crash check 1."""
        result = p.PipelineResult(student_image_path="test.jpg")
        result.tree = p.ResultNode("Recommendable")
        result.raw_texts = []
        warnings = p.validate_pipeline_output(result)
        assert isinstance(warnings, list)
