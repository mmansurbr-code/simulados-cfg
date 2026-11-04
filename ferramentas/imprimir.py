"""Gera a versão para imprimir (.docx e .pdf) de cada apostila.

Uso (a partir da pasta simulados-cfg):
    python ferramentas/imprimir.py apostilas/html/"CFG Tema 6 - ... .html" [...]

Monta um HTML de impressão no molde das apostilas já impressas (apostila,
simulado em página nova com alternativas embaralhadas e gabarito comentado em
tabela no fim) e pede ao Word (Windows) para salvar em .docx e .pdf na pasta
apostilas/impressao. Sem Word, fica só o HTML de impressão.
"""
import html, random, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gerar_epub  # noqa: E402  (mesmo leitor de apostilas do EPUB)

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "apostilas" / "impressao"

CSS = """
@page{size:A4;margin:2.5cm 3cm}
body{font-family:Calibri,Arial,sans-serif;font-size:11pt;line-height:1.35;color:#000}
h1{font-family:Cambria,Georgia,serif;font-size:22pt;margin:4pt 0 6pt}
h2{font-family:Cambria,Georgia,serif;font-size:16pt;margin:18pt 0 4pt;page-break-after:avoid}
h3{font-size:12pt;margin:12pt 0 4pt;page-break-after:avoid}
.eyebrow,.num{font-size:8.5pt;letter-spacing:1pt;text-transform:uppercase;color:#0f6b64}
p.why{font-style:italic;color:#444}
table{border-collapse:collapse;width:100%;font-size:9.5pt;margin:6pt 0}
th,td{border:1px solid #999;padding:3pt 5pt;text-align:left;vertical-align:top}
th{background:#e2f0ee}
.formula{border:1px solid #c9a227;background:#fff6e0;padding:6pt 8pt;margin:6pt 0;font-family:Consolas,monospace;font-size:9.5pt}
.ex{border-left:3px solid #0f6b64;padding-left:8pt;margin:6pt 0}
.pegadinha{border:1px solid #b3261e;padding:6pt 8pt;margin:6pt 0}
.lbl{display:block;font-weight:bold;font-size:8.5pt;text-transform:uppercase}
.pegadinha b:first-child{display:block;color:#b3261e;font-size:8.5pt;text-transform:uppercase}
p.q{font-weight:bold;margin:12pt 0 3pt;page-break-after:avoid}
p.opt{margin:1pt 0 1pt 14pt;page-break-after:avoid}
.quebra{page-break-before:always}
"""


def limpa_secao(sec):
    """Adapta um tópico da apostila ao que o Word sabe renderizar."""
    sec = re.sub(r'<div class="tbl">(.*?)</div>', r"\1", sec, flags=re.S)
    # o Word ignora display:block em <span> e <b>; os rótulos ganham quebra de linha explícita
    sec = re.sub(r'(<div class="pegadinha"><b>.*?</b>)', r"\1<br>", sec, flags=re.S)
    return re.sub(r'<span class="lbl">(.*?)</span>', r'<b class="lbl">\1</b><br>', sec, flags=re.S)


def prova(qs, n, semente):
    """Alternativas embaralhadas como no app (exceto as fixas), mas reproduzíveis."""
    rnd = random.Random(semente)
    out = []
    for k, (sub, q, opts, a, exp, fixa) in enumerate(qs, 1):
        ordem = list(range(len(opts)))
        if not fixa:
            rnd.shuffle(ordem)
        out.append((k, sub, q, [opts[i] for i in ordem], ordem.index(a), exp))
    return out


def questoes(src, t):
    """(sub, q, opts, a, exp, fixa) — 'fixa' vem do f:1 do array Q."""
    corpo = src[src.index("const Q"):] if "const Q" in src else ""
    fixas = {i for i, l in enumerate(re.findall(r"^\{s:.*$", corpo, re.M)) if ",f:1," in l}
    anteriores = re.compile(r"anteriores|\b[A-E] e [A-E]\b|nenhuma das", re.I)
    return [(*x, i in fixas or any(anteriores.search(o) for o in x[2])) for i, x in enumerate(t["qs"])]


def html_impressao(path):
    src = Path(path).read_text(encoding="utf-8")
    t = gerar_epub.parse_tema(path)
    n = t["tema"]
    titulo = html.unescape(re.sub(r"<[^>]+>", "", re.search(r"<h1>(.*?)</h1>", t["hero"], re.S).group(1)))
    peso = re.search(r"Peso <b>(.*?)</b>", t["hero"])
    peso = peso.group(1).replace("–", "% a ") if peso else ""
    qs = prova(questoes(src, t), n, int(n))
    esc = html.escape

    partes = [f'<p class="eyebrow">CFG · Certificação ANBIMA de Fundamentos em Gestão</p>',
              f"<h1>Tema {n} · {esc(titulo)}</h1>",
              f'<p class="why">Apostila e simulado de {len(qs)} questões. Peso na prova: {peso}. '
              f"Base: Orientações de Estudo CFG (ANBIMA).</p>"]
    for _, rotulo, sec in t["topics"]:
        partes.append(limpa_secao(sec))
    partes.append(f'<h2 class="quebra">Simulado · {len(qs)} questões</h2>')
    for k, sub, q, opts, _, _ in qs:
        partes.append(f'<p class="q">{k}. [{esc(sub)}] {esc(q)}</p>')
        partes += [f'<p class="opt">{"ABCDE"[j]}) {esc(o)}</p>' for j, o in enumerate(opts)]
    partes.append('<h2 class="quebra">Gabarito comentado</h2><table>'
                  '<tr><th style="width:9%">Questão</th><th style="width:10%">Resposta</th><th>Comentário</th></tr>')
    partes += [f'<tr><td>{k}</td><td><b>{"ABCDE"[a]}</b></td><td>{esc(e)}</td></tr>' for k, _, _, _, a, e in qs]
    partes.append("</table>")
    doc = (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>CFG Tema {n} · {esc(titulo)}</title>'
           f"<style>{CSS}</style></head><body>{''.join(partes)}</body></html>")
    return doc, len(qs)


def word(entrada, docx, pdf):
    """Converte com o Word via COM (PowerShell). Devolve False se o Word não estiver disponível."""
    ps = (f"$w=New-Object -ComObject Word.Application;$w.Visible=$false;"
          f"$d=$w.Documents.Open('{entrada}');$d.SaveAs2('{docx}',16);$d.SaveAs2('{pdf}',17);"
          f"$d.Close($false);$w.Quit()")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    return r.returncode == 0 and Path(docx).exists()


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    for p in map(Path, sys.argv[1:]):
        doc, nq = html_impressao(p)
        base = SAIDA / p.stem
        tmp = base.with_suffix(".impressao.html")
        tmp.write_text(doc, encoding="utf-8")
        ok = word(str(tmp.resolve()), str(base.with_suffix(".docx").resolve()), str(base.with_suffix(".pdf").resolve()))
        if ok:
            tmp.unlink()
        print(f"{p.stem}: {nq} questões -> {'docx + pdf' if ok else tmp.name + ' (sem Word)'}")


if __name__ == "__main__":
    main()
