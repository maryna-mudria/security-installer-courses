#!/usr/bin/env python3
"""Build the student site from 3-kurs/*.md into docs/ (static, relative links, works offline).

Usage: python3 build.py [--strict]
  --strict  fail if any [ЗАПОВНИТИ: ...] placeholder has no value in placeholders.json
"""
import html, json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "3-kurs"
OUT = ROOT / "docs"
STRICT = "--strict" in sys.argv
PH = json.loads((ROOT / "placeholders.json").read_text(encoding="utf-8")) if (ROOT / "placeholders.json").exists() else {}
PH_RE = re.compile(r"\[ЗАПОВНИТИ:\s*([^\]]+)\]")
missing = set()

COURSES = [
    ("course-1-basics", "Курс 1: Базовий інсталятор СБ"),
    ("course-2-sunell", "Курс 2: Обладнання Sunell"),
]
PART_NAMES = {"lesson": "Урок", "practice": "Практика", "checklist": "Чек-лист", "self-test": "Самотест", "next-steps": "Що далі"}
PART_ORDER = ["lesson", "practice", "checklist", "self-test", "next-steps"]
SHARED = ["glossary", "integration-pitfalls", "first-object-checklist", "portfolio-template", "certificate-template"]


def fill(text):
    def rep(m):
        key = m.group(1).strip()
        if PH.get(key):
            return PH[key]
        missing.add(key)
        return m.group(0)
    return PH_RE.sub(rep, text)


def pandoc(md):
    r = subprocess.run(["pandoc", "-f", "gfm", "-t", "html5", "--no-highlight"], input=md, capture_output=True, text=True, check=True)
    return r.stdout


def title_of(md, fallback):
    m = re.search(r"^#\s+(.+)$", md, re.M)
    return m.group(1).strip() if m else fallback


def fix_links(h):
    # relative .md links -> .html ; directory links are not used in student files
    return re.sub(r'href="([^":]+?)\.md(#[^"]*)?"', lambda m: f'href="{m.group(1)}.html{m.group(2) or ""}"', h)


def rel(frm, to):
    """relative url from page path `frm` (relative to OUT) to `to`."""
    up = "../" * (len(Path(frm).parts) - 1)
    return up + to


# ---------- collect pages ----------
pages = {}  # out_rel_path -> dict(title, body, section)
nav = []    # list of (heading, [(label, out_rel_path)])


def add_md(path, section):
    md = fill(path.read_text(encoding="utf-8"))
    out = str(path.relative_to(SRC).with_suffix(".html"))
    pages[out] = dict(title=title_of(md, path.stem), body=fix_links(pandoc(md)), md=md)
    return out


for cdir, cname in COURSES:
    items = []
    ov = SRC / cdir / "00-course-overview.md"
    items.append(("Огляд курсу", add_md(ov, cdir)))
    nav.append((cname, items, cdir))
    for mdir in sorted((SRC / cdir / "modules").iterdir()):
        if not mdir.is_dir():
            continue
        parts = []
        lesson_title = title_of((mdir / "lesson.md").read_text(encoding="utf-8"), mdir.name)
        for p in PART_ORDER:
            f = mdir / f"{p}.md"
            if f.exists():
                parts.append((PART_NAMES[p], add_md(f, cdir)))
        nav.append((lesson_title, parts, f"{cdir}/{mdir.name}"))

shared_items = []
for s in SHARED:
    f = SRC / "shared" / f"{s}.md"
    out = add_md(f, "shared")
    shared_items.append((pages[out]["title"], out))
nav.append(("Додаткові матеріали", shared_items, "shared"))

# emulators page
EMU = [
    ("camera-web-ui.html", "Камера Sunell", "Точна копія веб-інтерфейсу камери Sunell IPR57/20AKDN/T/Z2.7-12/13: усі 64 розділи зняті з живого пристрою."),
    ("router-web-ui.html", "Роутер", "Узагальнений роутер: прокидання портів, DHCP, безпека. Є перемикач сценарію провайдера."),
    ("nvr-web-ui.html", "Реєстратор (NVR)", "Узагальнений реєстратор. Це не копія реального пристрою: назви пунктів меню можуть відрізнятися."),
]
emu_body = "<h1>Емулятори</h1><p>Це інтерфейси пристроїв у браузері. Реальне обладнання не потрібне, зламати нічого не можна. Інтернет не потрібен.</p><ul class='emu'>"
for fn, name, desc in EMU:
    emu_body += f"<li><a href='emulators/{fn}' target='_blank' rel='noopener'><strong>{name}</strong></a><br><span>{desc}</span></li>"
emu_body += "</ul><p class='note'>Емулятор камери важкий (близько 2 МБ), перше відкриття може тривати кілька секунд. Емулятори відкриваються в новій вкладці, щоб урок залишався поруч.</p>"
pages["emulators.html"] = dict(title="Емулятори", body=emu_body)
nav.append(("Емулятори", [("Відкрити емулятори", "emulators.html")], "emulators"))

# index page
index_body = """<h1>Курси для інсталяторів систем безпеки</h1>
<p class="lead">Два безкоштовні курси: базова професія інсталятора систем безпеки і обладнання Sunell. Реальне обладнання не потрібне: уся практика проходить в емуляторах у браузері.</p>
<div class="cards">
 <a class="card" href="course-1-basics/00-course-overview.html"><h2>Курс 1</h2><p><strong>Базовий інсталятор СБ</strong></p><p>9 модулів, близько 8 годин, 2 тижні у своєму темпі. Відеоспостереження, мережі, СКД, домофонія, підсумковий проєкт.</p><span>Почати курс 1 →</span></a>
 <a class="card" href="course-2-sunell/00-course-overview.html"><h2>Курс 2</h2><p><strong>Обладнання Sunell</strong></p><p>8 модулів: камера, реєстратор, ПЗ і застосунок, смарт-функції, аналітика, СКД, практикум з несправностей.</p><span>Почати курс 2 →</span></a>
</div>
<h2>Як проходити</h2>
<ol>
<li>Відкрийте огляд курсу, прочитайте умови (2 хвилини).</li>
<li>Йдіть по модулях по порядку. У кожному три кроки: <strong>урок</strong>, <strong>практика</strong>, <strong>чек-лист</strong> самоперевірки.</li>
<li>Практику робіть в <a href="emulators.html">емуляторах</a>. Вони відкриваються у браузері, інтернет після завантаження не потрібен.</li>
<li>Незрозумілі слова шукайте в <a href="shared/glossary.html">глосарії</a>.</li>
</ol>
<p>Курси незалежні: курс 2 можна проходити без курсу 1, якщо ви вже працюєте інсталятором.</p>
<p class="note">Це версія для читання. Автоматична перевірка практик і форма здачі підсумкового проєкту в ній не працюють. Практику виконуйте за описом і звіряйтеся з чек-листом модуля.</p>
"""
pages["index.html"] = dict(title="Курси для інсталяторів систем безпеки", body=index_body)

# ---------- reading order for prev/next ----------
order = ["index.html"]
for _, items, _k in nav:
    for _, o in items:
        if o not in order:
            order.append(o)

CSS = """
:root{--bg:#fff;--fg:#1d2330;--mut:#5a6577;--bd:#e2e6ee;--side:#f5f7fb;--acc:#1b5fd1;--accbg:#e8f0fd;--note:#fff7e0;--code:#f1f3f8}
@media (prefers-color-scheme:dark){:root{--bg:#14171d;--fg:#e6e9f0;--mut:#9aa5b8;--bd:#2a303c;--side:#1a1e26;--acc:#7fb0ff;--accbg:#1f2b44;--note:#2b2614;--code:#1f242e}}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
a{color:var(--acc)}
.top{display:none;position:sticky;top:0;z-index:5;background:var(--side);border-bottom:1px solid var(--bd);padding:10px 16px;align-items:center;gap:12px}
.top button{font:inherit;background:var(--accbg);color:var(--acc);border:0;border-radius:8px;padding:6px 12px;cursor:pointer}
.layout{display:flex;min-height:100vh}
nav.side{width:310px;flex:none;background:var(--side);border-right:1px solid var(--bd);padding:18px 14px;position:sticky;top:0;height:100vh;overflow:auto;font-size:15px;line-height:1.4}
nav.side .home{display:block;font-weight:700;font-size:16px;text-decoration:none;margin-bottom:14px;color:var(--fg)}
nav.side details{margin:2px 0}
nav.side summary{cursor:pointer;padding:6px 8px;border-radius:8px;font-weight:600;list-style-position:inside}
nav.side summary:hover{background:var(--accbg)}
nav.side .grp{font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut);margin:16px 8px 4px}
nav.side ul{list-style:none;margin:0;padding:0 0 4px 14px}
nav.side li a{display:block;padding:4px 8px;border-radius:6px;text-decoration:none;color:var(--fg)}
nav.side li a:hover{background:var(--accbg)}
nav.side li a.cur{background:var(--accbg);color:var(--acc);font-weight:700}
main{flex:1;min-width:0;padding:32px 40px 80px}
article{max-width:780px;margin:0 auto}
h1{font-size:2rem;line-height:1.25;margin:.2em 0 .6em}h2{margin-top:2em;border-top:1px solid var(--bd);padding-top:1em}h3{margin-top:1.6em}
table{border-collapse:collapse;display:block;overflow-x:auto;margin:1em 0}th,td{border:1px solid var(--bd);padding:8px 12px;text-align:left;vertical-align:top}th{background:var(--side)}
blockquote{margin:1em 0;padding:.6em 1em;border-left:4px solid var(--acc);background:var(--accbg);border-radius:0 8px 8px 0}blockquote p{margin:.3em 0}
code{background:var(--code);padding:.1em .35em;border-radius:4px;font-size:.92em}pre{background:var(--code);padding:12px 14px;border-radius:8px;overflow:auto}pre code{padding:0;background:none}
img{max-width:100%}
.pager{display:flex;justify-content:space-between;gap:12px;margin-top:3em;padding-top:1.2em;border-top:1px solid var(--bd)}
.pager a{flex:1;border:1px solid var(--bd);border-radius:10px;padding:10px 14px;text-decoration:none;color:var(--fg);font-size:15px}
.pager a:hover{background:var(--accbg)}.pager small{display:block;color:var(--mut)}.pager .n{text-align:right}
.lead{font-size:1.15rem;color:var(--mut)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin:1.5em 0}
.card{display:block;border:1px solid var(--bd);border-radius:14px;padding:18px 20px;text-decoration:none;color:var(--fg);background:var(--side)}
.card:hover{border-color:var(--acc)}.card h2{margin:0;border:0;padding:0;font-size:1.1rem;color:var(--mut)}.card p{margin:.4em 0}.card span{color:var(--acc);font-weight:700}
.note{background:var(--note);border-radius:10px;padding:10px 14px;font-size:.95rem}
.emu{list-style:none;padding:0}.emu li{border:1px solid var(--bd);border-radius:12px;padding:14px 18px;margin:12px 0;background:var(--side)}.emu span{color:var(--mut)}
mark.todo{background:#ffd54a;color:#000;padding:0 .25em;border-radius:3px}
@media (max-width:900px){.top{display:flex}nav.side{position:fixed;left:0;top:0;z-index:10;transform:translateX(-100%);transition:transform .2s;width:min(86vw,320px)}body.open nav.side{transform:none;box-shadow:0 0 40px #0006}main{padding:20px 16px 60px}h1{font-size:1.6rem}}
@media print{nav.side,.top,.pager{display:none}main{padding:0}}
"""

JS = """
document.getElementById('menu').onclick=function(){document.body.classList.toggle('open')};
document.querySelector('main').addEventListener('click',function(){document.body.classList.remove('open')});
var c=document.querySelector('nav.side a.cur');if(c){c.scrollIntoView({block:'center'})}
"""


def build_nav(cur):
    h = [f'<a class="home" href="{rel(cur, "index.html")}">Курси для інсталяторів</a>']
    group_started = {}
    for label, items, key in nav:
        is_cur = any(o == cur for _, o in items)
        if key == "shared":
            h.append('<div class="grp">Для обох курсів</div>')
        if key == "emulators":
            pass
        # course headings
        if key in ("course-1-basics", "course-2-sunell"):
            h.append(f'<div class="grp">{html.escape(label)}</div>')
            lis = "".join(f'<li><a class="{"cur" if o == cur else ""}" href="{rel(cur, o)}">{html.escape(t)}</a></li>' for t, o in items)
            h.append(f"<ul style='padding-left:0'>{lis}</ul>")
            continue
        lis = "".join(f'<li><a class="{"cur" if o == cur else ""}" href="{rel(cur, o)}">{html.escape(t)}</a></li>' for t, o in items)
        h.append(f'<details{" open" if is_cur else ""}><summary>{html.escape(label)}</summary><ul>{lis}</ul></details>')
    return "\n".join(h)


def render(out, p):
    i = order.index(out)
    prev = order[i - 1] if i > 0 else None
    nxt = order[i + 1] if i + 1 < len(order) else None

    def t(o):
        return pages[o]["title"]

    pager = ""
    if prev or nxt:
        pager = '<div class="pager">'
        pager += f'<a href="{rel(out, prev)}"><small>← Назад</small>{html.escape(t(prev))}</a>' if prev else "<span></span>"
        pager += f'<a class="n" href="{rel(out, nxt)}"><small>Далі →</small>{html.escape(t(nxt))}</a>' if nxt else ""
        pager += "</div>"
    body = PH_RE.sub(lambda m: f'<mark class="todo">{m.group(0)}</mark>', p["body"])
    title = html.escape(p["title"])
    return f"""<!doctype html>
<html lang="uk"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | Курси для інсталяторів</title><style>{CSS}</style></head>
<body><div class="top"><button id="menu" aria-label="Меню">☰ Зміст</button><strong>{title}</strong></div>
<div class="layout"><nav class="side">{build_nav(out)}</nav>
<main><article>{body}{pager}</article></main></div><script>{JS}</script></body></html>"""


if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()
for out, p in pages.items():
    dest = OUT / out
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(render(out, p), encoding="utf-8")
shutil.copytree(SRC / "emulators", OUT / "emulators", ignore=shutil.ignore_patterns("_source*", ".DS_Store"))
(OUT / ".nojekyll").write_text("")

print(f"pages: {len(pages)}")
if missing:
    print("UNFILLED placeholders:")
    for k in sorted(missing):
        print("  -", k)
    if STRICT:
        sys.exit(1)
