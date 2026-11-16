"""Finding the Logisim installations in tools/ that the headless tests run on."""
from verify.logisim_run import Engine, engines


def _touch(p):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"")
    return p


def test_finds_classic_jar_and_both_kinds_of_evolution(tmp_path):
    jar271 = _touch(tmp_path / "logisim-generic-2.7.1.jar")
    jar38 = _touch(tmp_path / "evolution-3.8.0" / "logisim-evolution-3.8.0-all.jar")
    exe50 = _touch(tmp_path / "evolution-5.0.0" / "extracted" / "logisim-evolution.exe")
    _touch(tmp_path / "evolution-5.0.0" / "extracted" / "app" / "logisim-evolution-5.0.0-all.jar")
    java = _touch(tmp_path / "jdk" / "bin" / "java.exe")

    found = engines(tmp_path, {"JAVA_HOME": str(tmp_path / "jdk")})

    assert found == [
        Engine("2.7.1", ("java", "-jar", str(jar271)), "2.7.1"),
        Engine("evolution-3.8.0", (str(java), "-jar", str(jar38)), "evolution"),
        # a packaged build brings its own Java, so its launcher is used
        Engine("evolution-5.0.0", (str(exe50),), "evolution"),
    ]


def test_evolution_jar_needs_a_java(tmp_path):
    _touch(tmp_path / "evolution-3.8.0" / "logisim-evolution-3.8.0-all.jar")
    assert engines(tmp_path, {}) == []
    java = _touch(tmp_path / "java17" / "java.exe")
    found = engines(tmp_path, {"LOGISIM_EVOLUTION_JAVA": str(java)})
    assert [e.command[0] for e in found] == [str(java)]


def test_nothing_installed(tmp_path):
    assert engines(tmp_path, {}) == []
