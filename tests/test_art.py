import csv

import pytest
from PIL import Image

from art.catalog import filter_paintings, load_catalog
from art.check import run_checks
from art.cli import main
from art.config import load_config


def make_project(root, rows, images):
    """rows: list of dicts (missing keys default); images: {relpath: (w_px, h_px)}."""
    (root / "paintings").mkdir()
    cols = ["file", "title", "medium", "width_in", "height_in", "year", "status", "price"]
    with (root / "paintings" / "catalog.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, cols)
        w.writeheader()
        for r in rows:
            w.writerow({"title": "T", "medium": "oil", "year": "2026", "status": "available", "price": "100", **r})
    for rel, size in images.items():
        path = root / "paintings" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", size, "red").save(path)


@pytest.fixture
def project(tmp_path):
    make_project(
        tmp_path,
        [
            {"file": "studio/big.jpg", "title": "Big", "width_in": "48", "height_in": "36"},
            {"file": "agh/small.png", "title": "Small", "width_in": "10", "height_in": "12", "status": "sold"},
        ],
        {"studio/big.jpg": (480, 360), "agh/small.png": (100, 120)},
    )
    return tmp_path


def test_filters_use_longest_side_inclusive(project):
    ps = load_catalog(project).paintings
    assert [p.title for p in filter_paintings(ps, min_size=48)] == ["Big"]
    assert [p.title for p in filter_paintings(ps, max_size=12)] == ["Small"]
    assert [p.title for p in filter_paintings(ps, location="AGH")] == ["Small"]
    assert [p.title for p in filter_paintings(ps, status="sold")] == ["Small"]


def test_check_clean(project):
    assert run_checks(load_catalog(project), load_config(project)) == []
    assert main(["--root", str(project), "check"]) == 0


def test_check_flags_mismatches(project):
    Image.new("RGB", (50, 50)).save(project / "paintings" / "studio" / "extra.jpg")
    (project / "paintings" / "agh" / "small.png").unlink()
    msgs = [f.message for f in run_checks(load_catalog(project), load_config(project))]
    assert any("studio/extra.jpg" in m and "not in CSV" in m for m in msgs)
    assert any("agh/small.png" in m and "no image on disk" in m for m in msgs)
    assert main(["--root", str(project), "check"]) == 1


def test_check_flags_case_and_aspect(tmp_path):
    make_project(
        tmp_path,
        [{"file": "studio/A.JPG", "width_in": "10", "height_in": "10"},
         {"file": "studio/b.jpg", "width_in": "10", "height_in": "20"}],
        {"studio/a.JPG": (100, 100), "studio/b.jpg": (200, 100)},
    )
    findings = run_checks(load_catalog(tmp_path), load_config(tmp_path))
    assert any(f.level == "error" and "case differs" in f.message for f in findings)
    assert any(f.level == "warning" and "ratio" in f.message for f in findings)
    assert not any("not in CSV" in f.message for f in findings)


def test_check_enforces_status_values(project):
    cat = load_catalog(project)
    bad = [p.__class__(**{**p.__dict__, "status": "Available"}) for p in cat.paintings[:1]]
    cat.paintings[:1] = bad
    assert any(f.level == "error" and "must be one of" in f.message for f in run_checks(cat, load_config(project)))


def test_bad_rows_are_reported_not_fatal(tmp_path):
    make_project(tmp_path, [{"file": "studio/x.jpg", "width_in": "abc", "height_in": "1"}], {})
    cat = load_catalog(tmp_path)
    assert cat.paintings == [] and "width_in" in cat.problems[0]


def test_list_output_and_price_flag(project, capsys):
    main(["--root", str(project), "list", "--max-size", "20"])
    out = capsys.readouterr().out
    assert "Small" in out and "Big" not in out and "$100" not in out
    main(["--root", str(project), "list", "--prices"])
    assert "$100" in capsys.readouterr().out


def test_pdf(project, tmp_path):
    out = tmp_path / "out.pdf"
    assert main(["--root", str(project), "list", "--min-size", "40", "--pdf", str(out)]) == 0
    assert out.read_bytes().startswith(b"%PDF")


def test_build(project):
    assert main(["--root", str(project), "build", "--prices"]) == 0
    dist = project / "dist"
    html = (dist / "index.html").read_text()
    assert "$100" in html and 'data-location="agh"' in html
    assert (dist / "img" / "studio-big.jpg").exists() and (dist / "thumb" / "agh-small.jpg").exists()
    assert (dist / ".nojekyll").exists()

    (project / "site.toml").write_text(
        'domain = "example.com"\ncontact_email = "me@example.org"\n')
    main(["--root", str(project), "build"])
    assert "$100" not in (dist / "index.html").read_text()  # prices hidden by default
    assert (dist / "CNAME").read_text().strip() == "example.com"
    html = (dist / "index.html").read_text()
    assert "me@example.org" not in html and "mailto:" not in html  # address is encoded, not in the HTML
    assert "bWVAZXhhbXBsZS5vcmc=" in html and "me [at] example [dot] org" in html


def test_local_config_overrides(tmp_path):
    (tmp_path / "site.toml").write_text('title = "A"\ncontact_email = ""\n')
    (tmp_path / "site.local.toml").write_text('contact_email = "me@example.org"\n')
    cfg = load_config(tmp_path)
    assert cfg.title == "A" and cfg.contact_email == "me@example.org"


def test_unknown_config_key(tmp_path):
    (tmp_path / "site.toml").write_text("titel = 'x'\n")
    with pytest.raises(Exception, match="unknown"):
        load_config(tmp_path)


def test_deploy_pushes_only_built_site(project, tmp_path):
    import subprocess

    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(project)], check=True)
    for args in (["remote", "add", "origin", str(bare)], ["config", "user.name", "T"], ["config", "user.email", "t@example.com"]):
        subprocess.run(["git", "-C", str(project), *args], check=True)
    assert main(["--root", str(project), "deploy"]) == 0
    files = subprocess.run(["git", "-C", str(bare), "ls-tree", "-r", "--name-only", "gh-pages"],
                           capture_output=True, text=True, check=True).stdout.split()
    assert "index.html" in files and "img/studio-big.jpg" in files
    assert not any(f.startswith("paintings/") for f in files)


def test_agh_link_only_on_available_agh_works(tmp_path):
    make_project(
        tmp_path,
        [{"file": "agh/a.png", "title": "A", "width_in": "10", "height_in": "10"},
         {"file": "agh/b.png", "title": "B", "width_in": "10", "height_in": "10", "status": "sold"},
         {"file": "studio/c.png", "title": "C", "width_in": "10", "height_in": "10"}],
        {"agh/a.png": (50, 50), "agh/b.png": (50, 50), "studio/c.png": (50, 50)},
    )
    (tmp_path / "site.toml").write_text(
        '[[categories]]\nkey = "agh"\nlink = "https://agh.example/c"\n[[categories]]\nkey = "studio"\n')
    main(["--root", str(tmp_path), "build"])
    html = (tmp_path / "dist" / "index.html").read_text()
    assert html.count("https://agh.example/c") == 1


def test_categories_default_to_folders_and_can_be_renamed(tmp_path):
    make_project(
        tmp_path,
        [{"file": "prints/a.png", "title": "A", "width_in": "8", "height_in": "10"},
         {"file": "drawings/b.png", "title": "B", "width_in": "8", "height_in": "10"}],
        {"prints/a.png": (80, 100), "drawings/b.png": (80, 100)},
    )
    assert [c.key for c in load_config(tmp_path).categories] == ["drawings", "prints"]
    assert main(["--root", str(tmp_path), "check"]) == 0

    (tmp_path / "site.toml").write_text(
        'category_label = "Type"\n[[categories]]\nkey = "prints"\nlabel = "Limited prints"\n'
        '[[categories]]\nkey = "drawings"\n')
    main(["--root", str(tmp_path), "build"])
    html = (tmp_path / "dist" / "index.html").read_text()
    assert "Limited prints" in html and ">Drawings<" in html and 'aria-label="Type"' in html

    # a folder that isn't a configured category is flagged by check
    (tmp_path / "site.toml").write_text('[[categories]]\nkey = "prints"\n')
    findings = run_checks(load_catalog(tmp_path), load_config(tmp_path))
    assert any("drawings/b.png" in f.message and f.level == "error" for f in findings)


def test_list_rejects_unknown_category(project, capsys):
    assert main(["--root", str(project), "list", "--category", "nope"]) == 2
    assert "studio" in capsys.readouterr().err


def test_logo_and_size_buckets(project):
    Image.new("RGBA", (300, 100), (200, 0, 0, 0)).save(project / "mylogo.png")
    (project / "site.toml").write_text(
        'logo = "mylogo.png"\nlogo_width = 200\n[[size_buckets]]\nlabel = "Tiny"\nmax = 11\n')
    main(["--root", str(project), "build"])
    html = (project / "dist" / "index.html").read_text()
    assert 'src="assets/logo.png"' in html and "min(200px" in html and 'width="300" height="100"' in html
    assert (project / "dist" / "assets" / "logo.png").exists()
    assert ">Tiny<" in html and "Small (up to 24 in)" not in html


def test_no_logo_shows_title_text(project):
    main(["--root", str(project), "build"])
    html = (project / "dist" / "index.html").read_text()
    assert "<h1>Gord Bond</h1>" in html and "<img class=\"logo\"" not in html


def test_missing_logo_is_a_config_error(tmp_path):
    (tmp_path / "site.toml").write_text('logo = "nope.png"\n')
    with pytest.raises(Exception, match="logo file not found"):
        load_config(tmp_path)
