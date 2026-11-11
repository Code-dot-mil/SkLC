import subprocess

from skill_exchange.build_info import site_version


def test_version_distinguishes_release_development_and_installed_kit(tmp_path):
    def git(*args):
        subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", *args],
                       cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    source = tmp_path / "source.txt"
    source.write_text("Released source")
    git("add", "source.txt")
    git("commit", "-qm", "Release")
    git("tag", "v1.2.0")
    assert site_version(tmp_path) == "1.2.0"
    git("commit", "--allow-empty", "-qm", "Next change")
    assert site_version(tmp_path) == "1.2.0+dev.1"
    source.write_text("Uncommitted change")
    assert site_version(tmp_path) == "1.2.0+dev.1.dirty"
    # Customer history does not redefine the installed kit's upstream identity.
    (tmp_path / "VERSION").write_text("1.2.0+dev.4\n")
    assert site_version(tmp_path) == "1.2.0+dev.4"
