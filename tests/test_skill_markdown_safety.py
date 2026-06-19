import subprocess
from pathlib import Path


def test_skill_markdown_sanitizer_removes_executable_html():
    module_path = Path("site/src/lib/sanitize-skill-html.mjs").resolve()
    script = f"""
        import {{ sanitizeSkillHtml }} from {module_path.as_uri()!r};
        const unsafe = '<h1>Skill</h1><script>alert(1)</script><img src="x" onerror="alert(2)"><p onclick="alert(3)">Use it</p>';
        const safe = sanitizeSkillHtml(unsafe);
        if (safe.includes('<script') || safe.includes('onerror') || safe.includes('onclick')) {{
          throw new Error(safe);
        }}
        if (!safe.includes('<h1>Skill</h1>') || !safe.includes('<p>Use it</p>')) {{
          throw new Error(safe);
        }}
    """

    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr

