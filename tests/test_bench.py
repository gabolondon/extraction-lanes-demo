from bench import lanes as bench_lanes
from judge import cli


def test_lane_bench_layout_only(corpus, tmp_path, capsys):
    assert bench_lanes.main(["--corpus", str(corpus), "--out", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "layout" in out and "broken (4 pages)" in out and "fake backend" not in out
    assert (tmp_path / "lanes.json").exists() and (tmp_path / "lanes.md").exists()


def test_lane_bench_labels_fake_backends_on_every_line(corpus, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TEXT_BACKEND", "fake")
    bench_lanes.main(["--lanes", "text_llm", "--corpus", str(corpus), "--out", str(tmp_path)])
    rows = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("| text_llm")]
    assert len(rows) == 3 and all("(fake backend)" in ln for ln in rows)


def test_lane_bench_reports_missing_model_as_an_error_row(corpus, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("TEXT_BACKEND", raising=False)
    monkeypatch.delenv("TEXT_MODEL", raising=False)
    bench_lanes.main(["--lanes", "text_llm", "--corpus", str(corpus), "--out", str(tmp_path)])
    assert "TEXT_MODEL is required" in capsys.readouterr().out


def test_judge_bench_fake_is_labelled(corpus, tmp_path, capsys):
    cli.bench("fake", 4, 2, corpus, tmp_path)
    out = capsys.readouterr().out
    assert out.count("(fake backend)") >= 3
