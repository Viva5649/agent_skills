import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PACKAGE = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, PACKAGE / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load("check_diagram")
examples = load("render_examples")


def svg(content):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500">{content}</svg>'


def codes(content):
    return {i["code"] for i in checker.check(svg(content))["issues"]}


class DiagramChecks(unittest.TestCase):
    def test_crossing_return_channels_are_reported(self):
        source = '<path id="a" class="edge" d="M50,50 H300 V350 H50"/><path id="b" class="edge" d="M100,100 H400 V400 H100"/>'
        report = checker.check(svg(source))
        self.assertFalse(report["ok"])
        crossing = next(i for i in report["issues"] if i["code"] == "edge_crossing")
        self.assertEqual(crossing["point"], [300, 100])
        self.assertIn("#a", crossing["path"])
        self.assertTrue(crossing["fix"])

    def test_explicit_junction_endpoints_are_not_crossings(self):
        self.assertNotIn("edge_crossing", codes('<path class="edge" d="M0,50 H100"/><path class="edge" d="M200,50 H100"/><path class="edge" d="M100,50 V200"/>'))

    def test_overlapping_independent_routes_need_review(self):
        self.assertIn("edge_overlap", codes('<path class="edge" d="M20,50 H150"/><path class="edge" d="M80,50 H200"/>'))

    def test_short_final_elbow_is_flagged(self):
        source = '<defs><marker id="arrow"/></defs><path class="edge" d="M50,50 V200 H55" marker-end="url(#arrow)"/>'
        self.assertIn("short_entry", codes(source))

    def test_path_through_card_and_card_overlap_are_reported(self):
        source = '<rect id="card" class="card" x="100" y="100" width="100" height="80"/><rect class="card" x="150" y="100" width="100" height="80"/><path class="edge" d="M20,140 H300"/>'
        self.assertTrue({"edge_through_card", "card_overlap"} <= codes(source))
        self.assertNotIn("edge_through_card", codes('<rect class="card" x="100" y="100" width="100" height="80"/><path class="edge" d="M20,140 H100"/>'))
        grouped = '<g id="workflow"><rect class="card" x="100" y="100" width="100" height="80"/><rect class="card" x="150" y="100" width="100" height="80"/></g>'
        self.assertIn("card_overlap", codes(grouped))

    def test_label_distance_is_measured_against_its_own_edge(self):
        source = '<path id="a" class="edge" d="M20,100 H400"/><path id="b" class="edge" d="M20,300 H400"/><text class="edge-label" data-edge-label="a" x="200" y="285">读取配置</text>'
        self.assertIn("distant_label", codes(source))
        self.assertNotIn("distant_label", codes(source.replace('y="285"', 'y="85"')))

    def test_unbound_label_and_unsupported_geometry_are_disclosed(self):
        source = '<path class="edge" d="M20,100 Q100,20 200,100"/><g transform="translate(10 20)"><rect class="card" x="20" y="20" width="50" height="50"/></g><text class="edge-label" x="30" y="40">说明</text>'
        report = checker.check(svg(source))
        self.assertEqual(report["coverage"]["checked_edges"], 0)
        self.assertEqual(report["coverage"]["skipped"], 3)
        self.assertTrue({"unsupported_geometry", "unsupported_transform", "unbound_label"} <= {i["code"] for i in report["issues"]})
        self.assertTrue(report["manual_checks"])

    def test_references_and_duplicate_ids_across_figures(self):
        report = checker.check(svg('<path id="a" class="edge" d="M0,0 H50" marker-end="url(#missing)"/>') + svg('<text id="a"/>'))
        self.assertFalse(report["ok"])
        self.assertTrue({"missing_reference", "duplicate_id"} <= {i["code"] for i in report["issues"]})

    def test_bad_input_and_outside_geometry_are_visible(self):
        self.assertFalse(checker.check('<svg><broken></svg>')["ok"])
        self.assertIn("edge_outside", codes('<path class="edge" d="M20,20 H600"/>'))
        for coords in ('x2="nan" y2="30"', 'x2="100" y2="100"'):
            self.assertIn("unsupported_geometry", codes(f'<line class="edge" x1="0" y1="0" {coords}/>'))

    def test_examples_have_no_geometry_diagnostics(self):
        for layout in examples.LAYOUTS:
            with self.subTest(layout=layout):
                report = checker.check(examples.render(layout))
                self.assertTrue(report["ok"], report)
                self.assertEqual(report["issues"], [])
                self.assertGreater(report["coverage"]["checked_labels"], 0)

    def test_endpoints_and_label_candidate_follow_node_movement(self):
        for dx in (0, 80):
            start = examples.port((20 + dx, 20, 100, 80), "bottom")
            end = examples.port((20 + dx, 220, 100, 80), "top")
            markup = examples.edge("relation", start, end, label=("读取结果",))
            element = checker.ET.fromstring(svg(markup))
            path, label = list(element)
            self.assertEqual(checker.points(path), [(70 + dx, 100), (70 + dx, 220)])
            self.assertEqual(float(label.get("x")), 86 + dx)
            self.assertEqual(float(label.get("y")), 160)

    def test_label_candidate_uses_long_run_not_terminal_stub(self):
        self.assertEqual(examples.label_anchor([(20, 30), (20, 200), (250, 200), (250, 180)], 2), (135, 166, "middle"))

    def test_cli_reports_failure_and_generator_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            broken = target / "broken.svg"
            broken.write_text(svg('<path class="edge" d="M0,50 H200"/><path class="edge" d="M100,0 V100"/>'))
            result = subprocess.run([sys.executable, "-B", str(PACKAGE / "scripts/check_diagram.py"), str(broken)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('"edge_crossing"', result.stdout)
            command = [sys.executable, "-B", str(PACKAGE / "scripts/render_examples.py"), "--outdir", str(target)]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            first = (target / "layered.html").read_bytes()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual((target / "layered.html").read_bytes(), first)


if __name__ == "__main__":
    unittest.main()
