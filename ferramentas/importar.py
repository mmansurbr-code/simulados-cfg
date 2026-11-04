"""Converte as apostilas da pasta CFG em dados do app.

Uso (a partir da pasta simulados-cfg):
    python ferramentas/importar.py

Lê as apostilas HTML (apostilas/html/CFG Tema N - ... .html) e, para temas cujo
HTML não traz o simulado, as questões do EPUB "todos os temas" de
apostilas/kindle. Gera:
    dados/temas.json          índice dos temas
    dados/tema<N>.json        tópicos (HTML) e questões de cada tema
e atualiza em sw.js a lista de arquivos guardados para uso offline e a VERSAO.
"""
import hashlib, html, json, re, sys, zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "ferramentas"))
import gerar_epub  # noqa: E402  (reaproveita o leitor de apostilas do Kindle)

ORIGEM = RAIZ / "apostilas"
DADOS = RAIZ / "dados"
TXT = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def questoes_do_epub(n):
    """Lê simulado + gabarito do tema n no EPUB (ordem original das alternativas)."""
    epub = ORIGEM / "kindle" / "CFG - Material de estudo (todos os temas).epub"
    z = zipfile.ZipFile(epub)
    try:
        s = z.read(f"OEBPS/t{n}_simulado.xhtml").decode("utf-8")
        g = z.read(f"OEBPS/t{n}_gabarito.xhtml").decode("utf-8")
    except KeyError:
        return []
    gab = {k: b for k, b in re.findall(r'<div class="ans" id="g(\d+)">(.*?)</div>', g, re.S)}
    out = []
    for k, b in re.findall(r'<div class="q" id="q(\d+)">(.*?)</div>', s, re.S):
        sub = TXT(re.search(r'<p class="st">(.*?)</p>', b).group(1)).split("·")[-1].strip()
        q = TXT(re.search(r"<p><b>(.*?)</b></p>", b, re.S).group(1))
        opts = [TXT(o) for o in re.findall(r"<li>(.*?)</li>", b, re.S)]
        ps = re.findall(r"<p>(.*?)</p>", gab[k], re.S)
        a = "ABCDE".index(re.search(r"Resposta: ([A-E])", ps[0]).group(1))
        out.append((sub, q, opts, a, TXT(ps[1])))
    return out


def fixa(opts):
    """Alternativas que citam outras ("todas as anteriores", "A e B") não podem ser embaralhadas."""
    return any(re.search(r"anteriores|\b[A-E] e [A-E]\b|nenhuma das", o, re.I) for o in opts)


def main():
    DADOS.mkdir(exist_ok=True)
    indice = []
    for p in sorted((ORIGEM / "html").glob("CFG Tema *.html"), key=lambda p: int(re.search(r"Tema (\d+)", p.name).group(1))):
        t = gerar_epub.parse_tema(p)
        n = t["tema"]
        src = p.read_text(encoding="utf-8")
        fixas = set()
        if t["qs"]:
            # no HTML, f:1 marca questão com alternativas em ordem fixa
            corpo = src[src.index("const Q"):]
            fixas = {i for i, linha in enumerate(re.findall(r"^\{s:.*$", corpo, re.M)) if ",f:1," in linha}
        qs = t["qs"] or questoes_do_epub(n)
        titulo = TXT(re.search(r"<h1>(.*?)</h1>", t["hero"], re.S).group(1))
        lede = re.search(r'<p class="lede">(.*?)</p>', t["hero"], re.S)
        tema = {
            "id": f"t{n}",
            "numero": int(n),
            "titulo": titulo,
            # a frase sobre o simulado embutido na apostila não vale no app
            "resumo": re.sub(r"\s*O simulado[^.]*\.", "", TXT(lede.group(1))) if lede else "",
            "topicos": [{"id": sid, "rotulo": rot, "html": sec.strip()} for sid, rot, sec in t["topics"]],
            "questoes": [
                {"id": f"t{n}-{i + 1}", "subtema": sub, "enunciado": q, "alternativas": o,
                 "correta": a, "explicacao": e, **({"fixa": True} if i in fixas or fixa(o) else {})}
                for i, (sub, q, o, a, e) in enumerate(qs)
            ],
        }
        (DADOS / f"tema{n}.json").write_text(json.dumps(tema, ensure_ascii=False, indent=1), encoding="utf-8")
        indice.append({"id": tema["id"], "numero": tema["numero"], "titulo": titulo, "resumo": tema["resumo"],
                       "arquivo": f"tema{n}.json", "topicos": len(tema["topicos"]), "questoes": len(tema["questoes"])})
        print(f"Tema {n}: {len(tema['topicos'])} tópicos, {len(tema['questoes'])} questões")
    # temas escritos à mão (sem apostila de origem) entram no índice como estão
    for p in sorted((DADOS / "manuais").glob("*.json")):
        tema = json.loads(p.read_text(encoding="utf-8"))
        indice.append({"id": tema["id"], "numero": tema["numero"], "titulo": tema["titulo"], "resumo": tema["resumo"],
                       "arquivo": f"manuais/{p.name}", "topicos": len(tema["topicos"]), "questoes": len(tema["questoes"])})
        print(f"{tema['titulo']}: {len(tema['questoes'])} questões")
    (DADOS / "temas.json").write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
    extras = ["dados/audios.json"] if (DADOS / "audios.json").exists() else []
    atualiza_sw([f"dados/{t['arquivo']}" for t in indice] + extras)


def atualiza_sw(arquivos):
    """Põe todos os temas no cache offline e troca a VERSAO quando o conteúdo muda."""
    sw = RAIZ / "sw.js"
    src = sw.read_text(encoding="utf-8")
    linha = ", ".join(f'"{a}"' for a in ["dados/temas.json"] + arquivos) + ","
    src = re.sub(r'^  "dados/.*$', lambda m: "  " + linha, src, flags=re.M)
    h = hashlib.sha1(b"".join((RAIZ / a).read_bytes() for a in ["dados/temas.json"] + arquivos)).hexdigest()[:8]
    src = re.sub(r'const VERSAO = "[^"]*";', f'const VERSAO = "cfg-{h}";', src)
    sw.write_text(src, encoding="utf-8")


if __name__ == "__main__":
    main()
