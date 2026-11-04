"""Gera os áudios de estudo (MP3) de cada subtema, para ouvir sem ler.

Uso (a partir da pasta simulados-cfg):
    python ferramentas/audio.py            # todos os temas com roteiro
    python ferramentas/audio.py 6 11       # só alguns temas

Por subtema saem duas faixas, como nos áudios antigos do 5.1:
    Faixa 1 - Conteudo     roteiro falado de apostilas/audio/roteiros/temaN.json
    Faixa 2 - Perguntas    questões de dados/temaN.json: enunciado e alternativas,
                           pausa para pensar, resposta e explicação
                           (em partes de até POR_PARTE questões)

Voz neural pt-BR da Microsoft (edge-tts, precisa de internet) e ffmpeg do
pacote imageio-ffmpeg:  pip install edge-tts imageio-ffmpeg
Os trechos já sintetizados ficam em apostilas/audio/.cache (fora do git),
então rodar de novo só sintetiza o que mudou. Ao final, grava
dados/audios.json, a lista que o app usa na aba Ouvir.
"""
import asyncio, hashlib, json, re, subprocess, sys, unicodedata, unicodedata
from pathlib import Path

import edge_tts
import imageio_ffmpeg

RAIZ = Path(__file__).resolve().parent.parent
AUDIO = RAIZ / "apostilas" / "audio"
CACHE = AUDIO / ".cache"
VOZ = "pt-BR-FranciscaNeural"
POR_PARTE = 15          # questões por faixa de perguntas
PAUSA_PENSAR = 4.0      # segundos entre as alternativas e a resposta
PAUSA_PARAGRAFO = 0.7
PAUSA_QUESTAO = 1.5
SIMULTANEOS = 6         # pedidos de síntese em paralelo
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# símbolos que a voz lê mal ou não lê; aplicado só às questões (os roteiros já vêm falados)
TROCAS = [
    ("×", " vezes "), ("÷", " dividido por "), ("√", " raiz quadrada de "),
    ("²", " ao quadrado"), ("³", " ao cubo"), ("≥", " maior ou igual a "), ("≤", " menor ou igual a "),
    ("≠", " diferente de "), ("≈", " aproximadamente "), ("→", ", então "), ("±", " mais ou menos "),
    ("σ", " sigma "), ("β", " beta "), ("α", " alfa "), ("ρ", " rô "), ("μ", " mi "), ("π", " pi "),
    ("Δ", " variação de "), ("λ", " lambda "), ("χ", " qui "), ("§", " parágrafo "),
    ("−", " menos "), ("p.p.", " pontos percentuais"), ("a.a.", " ao ano"), ("a.m.", " ao mês"),
    ("₀", " zero"), ("₁", " um"), ("₂", " dois"), ("₃", " três"), ("ₜ", " t"), ("ᵢ", " i"),
]


def falado(txt):
    for a, b in TROCAS:
        txt = txt.replace(a, b)
    txt = re.sub(r"\s/\s", " dividido por ", txt)  # "150 / 600"; siglas como PLD/FT ficam
    return re.sub(r"\s+", " ", txt).strip()


def nome_arquivo(s):
    """Sem acentos: o nome vira URL no app e pasta no GitHub."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r'[\\/:*?"<>|]', "-", s)


# ---------- síntese com cache ----------
def trecho(texto):
    return CACHE / (hashlib.sha1(f"{VOZ}|{texto}".encode()).hexdigest()[:16] + ".mp3")


async def sintetiza(textos):
    faltam = sorted({t for t in textos if not trecho(t).exists()})
    sem = asyncio.Semaphore(SIMULTANEOS)
    feitos = 0

    async def um(t):
        nonlocal feitos
        async with sem:
            for tentativa in range(4):
                try:
                    tmp = trecho(t).with_suffix(".part")
                    await edge_tts.Communicate(t, VOZ).save(str(tmp))
                    tmp.replace(trecho(t))
                    break
                except Exception as e:  # rede instável: tenta de novo com espera
                    if tentativa == 3:
                        raise RuntimeError(f"falhou: {t[:60]!r}") from e
                    await asyncio.sleep(2 * (tentativa + 1))
            feitos += 1
            if feitos % 50 == 0 or feitos == len(faltam):
                print(f"  síntese {feitos}/{len(faltam)}", flush=True)

    await asyncio.gather(*(um(t) for t in faltam))


def silencio(seg):
    f = CACHE / f"silencio-{seg:.1f}.mp3"
    if not f.exists():
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                        "-t", str(seg), "-c:a", "libmp3lame", "-b:a", "48k", str(f)], check=True)
    return f


def monta(partes, saida, titulo, album, faixa):
    """partes: lista de textos (str) e pausas (float, em segundos)."""
    saida.parent.mkdir(parents=True, exist_ok=True)
    lista = saida.with_suffix(".txt")
    linhas = [f"file '{(silencio(p) if isinstance(p, float) else trecho(p)).as_posix()}'" for p in partes]
    lista.write_text("\n".join(linhas), encoding="utf-8")
    # reencoda para um MP3 contínuo com etiquetas, que tocadores de carro leem bem
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista),
                    "-c:a", "libmp3lame", "-b:a", "48k", "-ar", "24000", "-ac", "1",
                    "-metadata", f"title={titulo}", "-metadata", f"album={album}",
                    "-metadata", "artist=CFG · Estudo e Simulados", "-metadata", f"track={faixa}",
                    str(saida)], check=True)
    lista.unlink()
    r = subprocess.run([FFMPEG, "-i", str(saida)], capture_output=True, encoding="utf-8", errors="replace")
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr).groups()
    return round(int(h) * 3600 + int(m) * 60 + float(s))


# ---------- roteiros das faixas ----------
def faixa_conteudo(sub):
    partes = []
    for p in [p.strip() for p in sub["texto"].split("\n\n") if p.strip()]:
        partes += [p, PAUSA_PARAGRAFO]
    return partes


def faixa_perguntas(qs, rotulo, parte, total):
    cab = f"Perguntas do subtema {rotulo}" + (f", parte {parte} de {total}" if total > 1 else "") + \
          ". Depois das alternativas há uma pausa para você pensar antes da resposta."
    partes = [cab, PAUSA_QUESTAO]
    for k, q in qs:
        alts = " ".join(f"Alternativa {'ABCD'[i]}: {falado(o)}." for i, o in enumerate(q["alternativas"]))
        partes += [f"Questão {k}. {falado(q['enunciado'])} {alts}", PAUSA_PENSAR,
                   f"Resposta: letra {'ABCD'[q['correta']]}. {falado(q['alternativas'][q['correta']])}. {falado(q['explicacao'])}",
                   PAUSA_QUESTAO]
    return partes


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    pedidos = {int(a) for a in sys.argv[1:]}
    lista_app = json.loads((RAIZ / "dados" / "audios.json").read_text(encoding="utf-8")) \
        if (RAIZ / "dados" / "audios.json").exists() else []
    lista_app = {x["numero"]: x for x in lista_app}

    for rot in sorted((AUDIO / "roteiros").glob("tema*.json"), key=lambda p: int(re.sub(r"\D", "", p.stem))):
        r = json.loads(rot.read_text(encoding="utf-8"))
        n = int(r["tema"])
        if pedidos and n not in pedidos:
            continue
        dados = json.loads((RAIZ / "dados" / f"tema{n}.json").read_text(encoding="utf-8"))
        pasta = AUDIO / f"Tema {n:02d} - {nome_arquivo(r['titulo'])}"
        album = f"CFG Tema {n} · {r['titulo']}"
        faixas = []  # (sub, rótulo, arquivo, partes)
        for s in r["subtemas"]:
            sid = s["id"]
            faixas.append((sid, "Conteúdo", pasta / f"CFG {sid} - Faixa 1 - Conteudo.mp3", faixa_conteudo(s)))
            qs = [(k + 1, q) for k, q in enumerate(q for q in dados["questoes"] if q["subtema"] == sid)]
            blocos = [qs[i:i + POR_PARTE] for i in range(0, len(qs), POR_PARTE)]
            for j, b in enumerate(blocos, 1):
                sufixo = f" (parte {j} de {len(blocos)})" if len(blocos) > 1 else ""
                faixas.append((sid, "Perguntas" + sufixo,
                               pasta / f"CFG {sid} - Faixa 2 - Perguntas{sufixo}.mp3",
                               faixa_perguntas(b, sid, j, len(blocos))))
        print(f"Tema {n}: {len(faixas)} faixas", flush=True)
        asyncio.run(sintetiza([p for *_, ps in faixas for p in ps if isinstance(p, str)]))
        itens = []
        for k, (sid, rotulo, arq, ps) in enumerate(faixas, 1):
            titulo = f"{sid} · {rotulo} · {next(s['titulo'] for s in r['subtemas'] if s['id'] == sid)}"
            seg = monta(ps, arq, titulo, album, k)
            itens.append({"sub": sid, "rotulo": rotulo, "titulo": titulo,
                          "arquivo": arq.relative_to(RAIZ).as_posix(), "seg": seg, "bytes": arq.stat().st_size})
        lista_app[n] = {"tema": f"t{n}", "numero": n, "titulo": r["titulo"], "faixas": itens}
        print(f"Tema {n}: {sum(i['seg'] for i in itens) // 60} min de áudio", flush=True)

    (RAIZ / "dados" / "audios.json").write_text(
        json.dumps([lista_app[k] for k in sorted(lista_app)], ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
