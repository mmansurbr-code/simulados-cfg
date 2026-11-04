"""Gera EPUBs para Kindle a partir das apostilas HTML da CFG.

Uso: python gerar_epub.py <saida_dir> <tema.html> [<tema.html> ...]
Cada HTML vira um livro (apostila + simulado + gabarito). Também sai um volume
único com todos os temas.
"""
import html, json, re, sys, uuid, zipfile
from html.parser import HTMLParser
from pathlib import Path

VOID = {"br", "hr", "img", "meta", "link", "input", "col", "wbr"}

CSS = """
body{font-family:serif;line-height:1.5;margin:0 .3em}
h1{font-size:1.6em;margin:.6em 0 .3em}
h2{font-size:1.35em;margin:1em 0 .3em;page-break-after:avoid}
h3{font-size:1.1em;margin:1.1em 0 .3em;page-break-after:avoid}
.num,.eyebrow{font-family:sans-serif;font-size:.8em;letter-spacing:.08em;text-transform:uppercase;color:#555}
.why,.lede{font-style:italic;color:#444}
.meta span{display:block;font-size:.85em}
table{border-collapse:collapse;width:100%;font-size:.85em;margin:.6em 0}
th,td{border:1px solid #888;padding:.25em .4em;text-align:left;vertical-align:top}
th{background:#e6e6e6}
.formula{border:1px solid #999;background:#f2f2f2;padding:.5em .7em;margin:.7em 0;font-family:monospace;font-size:.9em}
.formula .lbl,.ex .lbl{display:block;font-family:sans-serif;font-weight:bold;font-size:.75em;text-transform:uppercase}
.ex{border-left:3px solid #555;padding-left:.7em;margin:.7em 0}
.pegadinha{border:2px solid #333;padding:.5em .7em;margin:.7em 0}
.pegadinha b:first-child{display:block;text-transform:uppercase;font-size:.8em}
.q{margin:1.2em 0;page-break-inside:avoid}
.q .st{font-family:sans-serif;font-size:.75em;color:#555}
.q ol{list-style-type:upper-alpha;margin:.3em 0}
.go{font-size:.85em}
.ans{margin:1em 0;padding-bottom:.6em;border-bottom:1px solid #bbb}
"""


class XHTML(HTMLParser):
    """Reserializa HTML solto como XHTML bem formado (o EPUB exige XML)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.stack = [], []

    def _attrs(self, attrs):
        return "".join(f' {k}="{html.escape(v or k, quote=True)}"' for k, v in attrs)

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            self.out.append(f"<{tag}{self._attrs(attrs)}/>")
        else:
            self.out.append(f"<{tag}{self._attrs(attrs)}>")
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.out.append(f"<{tag}{self._attrs(attrs)}/>")

    def handle_endtag(self, tag):
        if tag in VOID or tag not in self.stack:
            return
        while self.stack:
            t = self.stack.pop()
            self.out.append(f"</{t}>")
            if t == tag:
                break

    def handle_data(self, data):
        self.out.append(html.escape(data, quote=False))

    def result(self):
        while self.stack:
            self.out.append(f"</{self.stack.pop()}>")
        return "".join(self.out)


def xhtml(fragment):
    p = XHTML()
    p.feed(fragment)
    p.close()
    return p.result()


def parse_questions(src):
    i = src.index("const Q")
    body = src[src.index("[", i): src.index("];", i) + 1]
    if "{s:" in body:  # formato de objeto com chaves sem aspas: põe aspas só fora das strings
        parts = re.split(r'("(?:[^"\\]|\\.)*")', body)
        body = "".join(p if k % 2 else re.sub(r'([{,]\s*)([A-Za-z_]\w*):', r'\1"\2":', p)
                       for k, p in enumerate(parts))
        return [(d["s"], d["q"], d["o"], d["a"], d["e"]) for d in json.loads(body)]
    return [tuple(x) for x in json.loads(body)]


def parse_tema(path):
    src = Path(path).read_text(encoding="utf-8")
    title = re.search(r"<title>(.*?)</title>", src, re.S).group(1).strip()
    hero = re.search(r'<header class="hero">(.*?)</header>', src, re.S).group(1)
    topics = []
    for m in re.finditer(r'<section class="topic" id="(\w+)">(.*?)</section>', src, re.S):
        sec = m.group(2)
        num = re.search(r'<div class="num">(.*?)</div>', sec).group(1)
        h2 = re.sub(r"<[^>]+>", "", re.search(r"<h2>(.*?)</h2>", sec, re.S).group(1))
        topics.append((m.group(1), f"{num} {html.unescape(h2)}", sec))
    qs = parse_questions(src) if "const Q" in src else []
    tema = re.search(r"Tema (\d+)", title).group(1)
    return {"title": html.unescape(title), "tema": tema, "hero": hero, "topics": topics, "qs": qs}


def page(title, body):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
            f'lang="pt-BR" xml:lang="pt-BR"><head><meta charset="utf-8"/><title>{html.escape(title)}</title>'
            '<link rel="stylesheet" href="style.css"/></head><body>' + body + "</body></html>")


def tema_pages(t):
    """Devolve [(arquivo, titulo_no_indice, xhtml)] de um tema."""
    n = t["tema"]
    pages = [(f"t{n}_capa.xhtml", t["title"], page(t["title"], xhtml(t["hero"])))]
    for sid, label, sec in t["topics"]:
        pages.append((f"t{n}_{sid}.xhtml", label, page(label, xhtml(sec))))
    if t["qs"]:
        qf, gf = f"t{n}_simulado.xhtml", f"t{n}_gabarito.xhtml"
        q_html = [f"<h2>Simulado · Tema {n}</h2><p class='why'>{len(t['qs'])} questões. "
                  "Responda de cabeça e toque em “ver resposta” para conferir o gabarito comentado.</p>"]
        g_html = [f"<h2>Gabarito comentado · Tema {n}</h2>"]
        for k, (sub, q, opts, a, exp) in enumerate(t["qs"], 1):
            lis = "".join(f"<li>{html.escape(o)}</li>" for o in opts)
            q_html.append(f'<div class="q" id="q{k}"><p class="st">Questão {k} · {sub}</p>'
                          f"<p><b>{html.escape(q)}</b></p><ol>{lis}</ol>"
                          f'<p class="go"><a href="{gf}#g{k}">ver resposta</a></p></div>')
            g_html.append(f'<div class="ans" id="g{k}"><p><b>{k}. Resposta: {"ABCDE"[a]}</b> · '
                          f"{html.escape(opts[a])}</p><p>{html.escape(exp)}</p>"
                          f'<p class="go"><a href="{qf}#q{k + 1 if k < len(t["qs"]) else 1}">próxima questão</a></p></div>')
        pages.append((qf, f"Simulado ({len(t['qs'])} questões)", page("Simulado", "".join(q_html))))
        pages.append((gf, "Gabarito comentado", page("Gabarito", "".join(g_html))))
    return pages


def build(out, book_title, temas):
    uid = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, book_title)}"
    chapters = []  # (tema_title, [(file, label, content)])
    for t in temas:
        chapters.append((t["title"], tema_pages(t)))
    files = [p for _, ps in chapters for p in ps]

    nav_items = []
    for tt, ps in chapters:
        sub = "".join(f'<li><a href="{f}">{html.escape(l)}</a></li>' for f, l, _ in ps[1:])
        nav_items.append(f'<li><a href="{ps[0][0]}">{html.escape(tt)}</a><ol>{sub}</ol></li>')
    nav = page("Sumário", f'<nav epub:type="toc" id="toc"><h1>Sumário</h1><ol>{"".join(nav_items)}</ol></nav>')

    # toc.ncx: o Kindle ainda usa para o menu "Ir para".
    pts, order = [], 1
    for tt, ps in chapters:
        inner = ""
        for f, l, _ in ps[1:]:
            order += 1
            inner += (f'<navPoint id="n{order}" playOrder="{order}"><navLabel><text>{html.escape(l)}</text>'
                      f'</navLabel><content src="{f}"/></navPoint>')
        pts.append(f'<navPoint id="c{ps[0][0]}" playOrder="{order}"><navLabel><text>{html.escape(tt)}</text>'
                   f'</navLabel><content src="{ps[0][0]}"/>{inner}</navPoint>')
        order += 1
    # playOrder precisa ser sequencial na ordem de leitura: renumera.
    ncx_body = "".join(pts)
    counter = iter(range(1, 10000))
    ncx_body = re.sub(r'playOrder="\d+"', lambda m: f'playOrder="{next(counter)}"', ncx_body)
    ncx = ('<?xml version="1.0" encoding="utf-8"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
           f'<head><meta name="dtb:uid" content="{uid}"/></head><docTitle><text>{html.escape(book_title)}</text></docTitle>'
           f"<navMap>{ncx_body}</navMap></ncx>")

    manifest = "".join(f'<item id="p{i}" href="{f}" media-type="application/xhtml+xml"/>' for i, (f, _, _) in enumerate(files))
    spine = "".join(f'<itemref idref="p{i}"/>' for i in range(len(files)))
    opf = ('<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
           f'<dc:identifier id="uid">{uid}</dc:identifier><dc:title>{html.escape(book_title)}</dc:title>'
           '<dc:language>pt-BR</dc:language><dc:creator>Material de estudo CFG</dc:creator>'
           '<meta property="dcterms:modified">2026-10-21T00:00:00Z</meta></metadata><manifest>'
           '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
           '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
           '<item id="css" href="style.css" media-type="text/css"/>'
           f'{manifest}</manifest><spine toc="ncx"><itemref idref="nav"/>{spine}</spine></package>')
    container = ('<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                 '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
                 "</rootfiles></container>")

    with zipfile.ZipFile(out, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container, compress_type=zipfile.ZIP_DEFLATED)
        for name, data in [("content.opf", opf), ("toc.ncx", ncx), ("nav.xhtml", nav), ("style.css", CSS)] + \
                          [(f, c) for f, _, c in files]:
            z.writestr(f"OEBPS/{name}", data, compress_type=zipfile.ZIP_DEFLATED)
    return out


def main():
    out_dir = Path(sys.argv[1])
    temas = sorted((parse_tema(p) for p in sys.argv[2:]), key=lambda t: int(t["tema"]))
    for t in temas:
        name = re.sub(r'[\\/:*?"<>|·]', "-", t["title"]).replace("  ", " ")
        print(build(out_dir / f"{name}.epub", t["title"], [t]), len(t["topics"]), "tópicos,", len(t["qs"]), "questões")
    if len(temas) > 1:
        nums = ", ".join(t["tema"] for t in temas)
        print(build(out_dir / "CFG - Material de estudo (todos os temas).epub", f"CFG · Temas {nums}", temas))


if __name__ == "__main__":
    main()
