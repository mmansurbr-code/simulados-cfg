"use strict";
// CFG · Estudo e Simulados — app de uma página com rotas por hash:
//   #/                início (temas e progresso)
//   #/tema/<id>       tópicos de um tema
//   #/tema/<id>/<top> leitura de um tópico da apostila
//   #/praticar        montar um treino ou simulado
//   #/quiz            questão em andamento (só existe enquanto há sessão)
//   #/mais            backup do progresso e banco de questões extra

const L = "ABCDE";
const APROVA = 70; // % de acertos para aprovação na prova

// ---------- armazenamento local ----------
const KEY = "cfg-estudo-v1";
let store = {
  cfg: { temas: null, filtro: "todas", qtd: 10, modo: "treino", emb: true },
  hist: [],   // {data, modo, tot, ac, temas}
  q: {},      // id -> {v: vezes respondida, a: acertos, ok: acertou na última}
  lido: {},   // "<tema>/<topico>" -> data em que marcou como lido
  extras: [], // questões importadas de pacotes .json
};
try { const s = JSON.parse(localStorage.getItem(KEY) || "null"); if (s) store = Object.assign(store, s); } catch (e) {}
function save() { try { localStorage.setItem(KEY, JSON.stringify(store)); } catch (e) {} }

// ---------- dados ----------
let TEMAS = [];      // índice, na ordem de dados/temas.json
const DADOS = {};    // id -> tema completo (topicos, questoes)

async function carregar() {
  TEMAS = await (await fetch("dados/temas.json")).json();
  await Promise.all(TEMAS.map(async t => {
    DADOS[t.id] = await (await fetch("dados/" + t.arquivo)).json();
    DADOS[t.id].questoes.forEach(q => { q.tema = t.id; });
  }));
}
function temaExtras() {
  // questões importadas viram um tema próprio por nome de tema do pacote
  const porNome = {};
  (store.extras || []).forEach(q => { (porNome[q.tema] = porNome[q.tema] || []).push(q); });
  return Object.entries(porNome).map(([nome, qs], i) => ({ id: "x" + i, titulo: nome, resumo: "Questões importadas neste aparelho.", topicos: [], extra: true,
    questoes: qs.map(q => Object.assign({}, q, { tema: "x" + i, subtema: q.subtema || nome })) }));
}
function todosTemas() { return TEMAS.map(t => DADOS[t.id]).concat(temaExtras()); }
function tema(id) { return todosTemas().find(t => t.id === id); }
function todasQuestoes() { return todosTemas().flatMap(t => t.questoes); }
function subDoTopico(top) { return top.rotulo.split(" ")[0]; }

// ---------- utilidades ----------
const $ = id => document.getElementById(id);
function el(tag, attrs, ...filhos) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const f of filhos.flat()) if (f != null && f !== false) e.append(f instanceof Node ? f : String(f));
  return e;
}
function shuffle(a) { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
function pct(a, b) { return b ? Math.round(a / b * 100) : 0; }
function barra(p, cor) { const i = el("i"); i.style.width = p + "%"; if (cor) i.style.background = cor; return el("div", { class: "barra" }, i); }
function statsDe(qs) {
  let vistas = 0, ac = 0, resp = 0;
  qs.forEach(q => { const s = store.q[q.id]; if (s) { vistas++; ac += s.a; resp += s.v; } });
  return { vistas, total: qs.length, acerto: resp ? pct(ac, resp) : null };
}
function aviso(texto, acao, rotulo) {
  const a = $("aviso"); a.innerHTML = ""; a.append(el("span", null, texto));
  if (acao) a.append(el("button", { type: "button", onclick: acao }, rotulo));
  a.hidden = false; clearTimeout(aviso.t);
  if (!acao) aviso.t = setTimeout(() => { a.hidden = true; }, 3500);
}
function render(...nos) {
  const t = $("tela"); t.innerHTML = ""; t.append(...nos);
  window.scrollTo(0, 0);
}
function marcarAba(aba) {
  document.querySelectorAll(".abas a").forEach(a => {
    if (a.dataset.aba === aba) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  document.body.classList.toggle("em-quiz", aba === "quiz");
}

// ---------- rotas ----------
function rota() {
  const p = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  if (p[0] !== "quiz" && S) pararSessao();
  if (!p.length) return telaInicio();
  if (p[0] === "tema" && p[2]) return telaTopico(p[1], p[2]);
  if (p[0] === "tema") return telaTema(p[1]);
  if (p[0] === "praticar") return telaPraticar();
  if (p[0] === "mais") return telaMais();
  if (p[0] === "quiz") return S ? telaQuestao() : (location.hash = "#/praticar");
  location.hash = "#/";
}
window.addEventListener("hashchange", rota);

// ---------- início ----------
function telaInicio() {
  marcarAba("inicio");
  const qs = todasQuestoes(), g = statsDe(qs);
  const sims = store.hist.length;
  const cards = todosTemas().map(t => {
    const s = statsDe(t.questoes);
    const lidos = t.topicos.filter(tp => store.lido[t.id + "/" + tp.id]).length;
    return el("article", { class: "painel tema-card" },
      el("span", { class: "eyebrow" }, t.numero && t.numero < 99 ? "Tema " + t.numero : t.extra ? "Importado" : "Extra"),
      el("h3", null, t.titulo),
      t.resumo && el("p", { class: "resumo" }, t.resumo),
      el("div", { class: "prog" },
        el("span", null, t.topicos.length ? `${lidos} de ${t.topicos.length} tópicos lidos · ${s.vistas} de ${s.total} questões feitas` : `${s.vistas} de ${s.total} questões feitas`),
        el("span", { class: "mono" }, s.acerto == null ? "–" : s.acerto + "%"),
        barra(pct(s.vistas, s.total))),
      el("div", { class: t.topicos.length ? "duas" : "pilha" },
        t.topicos.length > 0 && el("a", { class: "btn leve", href: "#/tema/" + t.id }, "Estudar"),
        el("button", { class: "btn", type: "button", onclick: () => iniciar(shuffle(t.questoes), "treino") }, "Praticar")));
  });
  render(
    el("div", { class: "pilha" }, el("span", { class: "eyebrow" }, "Certificação ANBIMA"), el("h1", { class: "titulo" }, "Seu estudo para a CFG"),
      el("p", { class: "muted" }, "Leia a apostila de cada tema e pratique com questões comentadas. Tudo funciona sem internet depois do primeiro acesso.")),
    el("section", { class: "painel" }, el("div", { class: "nums" },
      el("div", { class: "num-b" }, el("b", null, g.vistas + "/" + g.total), el("span", null, "questões feitas")),
      el("div", { class: "num-b" }, el("b", null, g.acerto == null ? "–" : g.acerto + "%"), el("span", null, "acerto geral")),
      el("div", { class: "num-b" }, el("b", null, sims), el("span", null, "treinos e simulados")))),
    ...cards
  );
}

// ---------- tema e tópicos ----------
function telaTema(id) {
  const t = tema(id); if (!t) return (location.hash = "#/");
  marcarAba("inicio");
  const itens = t.topicos.map(tp => {
    const sub = subDoTopico(tp), qs = t.questoes.filter(q => q.subtema === sub), s = statsDe(qs);
    const lido = store.lido[t.id + "/" + tp.id];
    return el("li", null, el("a", { href: `#/tema/${t.id}/${tp.id}` },
      el("span", { class: "n" }, sub),
      el("span", null, tp.rotulo.slice(sub.length + 1), lido && el("span", { class: "marca-ok" }, "  ✓")),
      el("span", { class: "st" }, qs.length ? `${s.vistas}/${qs.length}` + (s.acerto == null ? "" : ` · ${s.acerto}%`) : "")));
  });
  render(
    el("a", { href: "#/", class: "nota" }, "← Início"),
    el("div", { class: "pilha" }, el("span", { class: "eyebrow" }, "Tema " + t.numero), el("h1", { class: "titulo" }, t.titulo), el("p", { class: "muted" }, t.resumo)),
    el("ul", { class: "topicos" }, itens),
    el("p", { class: "nota" }, "À direita: questões feitas do subtema e o seu acerto."),
    el("button", { class: "btn cheio", type: "button", onclick: () => iniciar(shuffle(t.questoes), "treino") }, `Praticar o tema inteiro (${t.questoes.length} questões)`)
  );
}

function telaTopico(tid, topid) {
  const t = tema(tid); if (!t) return (location.hash = "#/");
  const i = t.topicos.findIndex(x => x.id === topid); if (i < 0) return (location.hash = "#/tema/" + tid);
  marcarAba("inicio");
  const tp = t.topicos[i], sub = subDoTopico(tp), qs = t.questoes.filter(q => q.subtema === sub);
  const chave = t.id + "/" + tp.id;
  const corpo = el("article", { class: "apostila" }); corpo.innerHTML = tp.html; // HTML das apostilas, conteúdo próprio
  const ant = t.topicos[i - 1], prox = t.topicos[i + 1];
  const btLido = el("button", { class: "btn leve", type: "button", onclick: () => {
    if (store.lido[chave]) delete store.lido[chave]; else store.lido[chave] = Date.now();
    save(); btLido.textContent = store.lido[chave] ? "✓ Lido" : "Marcar como lido";
  } }, store.lido[chave] ? "✓ Lido" : "Marcar como lido");
  render(
    el("a", { href: "#/tema/" + t.id, class: "nota" }, "← Tema " + t.numero + " · " + t.titulo),
    corpo,
    el("div", { class: qs.length ? "duas" : "pilha" }, btLido,
      qs.length > 0 && el("button", { class: "btn", type: "button", onclick: () => { store.lido[chave] = store.lido[chave] || Date.now(); save(); iniciar(shuffle(qs), "treino"); } }, `Praticar ${sub} (${qs.length})`)),
    el("nav", { class: "paginacao", "aria-label": "Tópicos" },
      ant && el("a", { href: `#/tema/${t.id}/${ant.id}` }, el("small", null, "← Anterior"), ant.rotulo),
      prox && el("a", { class: "prox", href: `#/tema/${t.id}/${prox.id}` }, el("small", null, "Próximo →"), prox.rotulo))
  );
}

// ---------- praticar (configuração) ----------
function filtrar(qs, filtro) {
  if (filtro === "novas") return qs.filter(q => !store.q[q.id]);
  if (filtro === "erradas") return qs.filter(q => store.q[q.id] && !store.q[q.id].ok);
  return qs;
}
function telaPraticar() {
  marcarAba("praticar");
  const ts = todosTemas(), c = store.cfg;
  if (!c.temas) c.temas = ts.map(t => t.id);
  c.temas = c.temas.filter(id => ts.some(t => t.id === id));
  const pool = () => filtrar(ts.filter(t => c.temas.includes(t.id)).flatMap(t => t.questoes), c.filtro);
  const redraw = () => { save(); telaPraticar(); };
  const chip = (rot, sm, on, fn) => el("button", { class: "chip", type: "button", "aria-pressed": String(on), onclick: fn }, rot, sm != null && el("small", null, sm));
  const n = pool().length;
  const msg = el("p", { class: "msg bad", hidden: true });
  render(
    el("div", { class: "pilha" }, el("span", { class: "eyebrow" }, "Praticar"), el("h1", { class: "titulo" }, "Monte seu treino")),
    el("section", { class: "painel" }, el("h2", { class: "sub" }, "Temas"),
      el("div", { class: "chips" }, ts.map(t => chip(t.numero && t.numero < 99 ? `Tema ${t.numero} · ${t.titulo}` : t.titulo, t.questoes.length, c.temas.includes(t.id), () => {
        const k = c.temas.indexOf(t.id); k >= 0 ? c.temas.splice(k, 1) : c.temas.push(t.id); redraw();
      }))),
      el("h2", { class: "sub" }, "Quais questões"),
      el("div", { class: "seg" },
        [["todas", "Todas", "do banco"], ["novas", "Novas", "que nunca fiz"], ["erradas", "Que errei", "na última vez"]].map(([v, r, s]) =>
          el("button", { class: "chip", type: "button", "aria-pressed": String(c.filtro === v), onclick: () => { c.filtro = v; redraw(); } }, r, el("small", null, s)))),
      el("p", { class: "nota" }, n + " questões disponíveis com essa seleção.")),
    el("section", { class: "painel" }, el("h2", { class: "sub" }, "Modo"),
      el("div", { class: "seg" },
        el("button", { class: "chip", type: "button", "aria-pressed": String(c.modo === "treino"), onclick: () => { c.modo = "treino"; redraw(); } }, "Treino", el("small", null, "corrige a cada questão")),
        el("button", { class: "chip", type: "button", "aria-pressed": String(c.modo === "simulado"), onclick: () => { c.modo = "simulado"; redraw(); } }, "Simulado", el("small", null, "corrige no fim, com tempo"))),
      el("h2", { class: "sub" }, "Quantidade"),
      el("div", { class: "chips" }, [5, 10, 20, 60].map(q => chip(q === 60 ? "60 (prova)" : String(q), null, c.qtd === q, () => { c.qtd = q; redraw(); }))),
      el("label", { class: "toggle" }, el("input", { type: "checkbox", checked: c.emb, onchange: e => { c.emb = e.target.checked; save(); } }), "Embaralhar alternativas"),
      el("p", { class: "nota" }, "No simulado são 3 minutos por questão, como na prova (60 questões em 3 horas). Aprovação com " + APROVA + "%.")),
    el("button", { class: "btn cheio", type: "button", disabled: !n, onclick: () => {
      const p = pool(); if (!p.length) { msg.hidden = false; msg.textContent = "Nenhuma questão com essa seleção."; return; }
      iniciar(shuffle(p).slice(0, c.qtd), c.modo);
    } }, "Começar"),
    msg,
    historico()
  );
}
function historico() {
  const h = store.hist; if (!h.length) return null;
  return el("section", { class: "painel" }, el("h2", { class: "sub" }, "Últimos treinos"),
    el("ul", { class: "hist" }, h.slice(-8).reverse().map(x => el("li", null,
      el("span", null, new Date(x.data).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) + " · " + (x.modo === "simulado" ? "Simulado" : "Treino")),
      el("span", { class: "mono" }, `${x.ac}/${x.tot} · ${pct(x.ac, x.tot)}%`)))));
}

// ---------- sessão de questões ----------
let S = null, tick = null;
function iniciar(lista, modo) {
  if (!lista.length) return;
  const emb = store.cfg.emb;
  S = { modo, i: 0, sel: null, conf: false,
    qs: lista.map(q => ({ q, ordem: emb && !q.fixa ? shuffle(q.alternativas.map((_, k) => k)) : q.alternativas.map((_, k) => k), resp: null })) };
  if (modo === "simulado") { S.fim = Date.now() + S.qs.length * 180000; tick = setInterval(timer, 1000); }
  if (location.hash === "#/quiz") telaQuestao(); else location.hash = "#/quiz";
}
function pararSessao() { clearInterval(tick); S = null; }
function timer() {
  const t = $("q-timer"); if (!S || !t) return;
  const r = Math.max(0, S.fim - Date.now());
  t.textContent = String(Math.floor(r / 60000)).padStart(2, "0") + ":" + String(Math.floor(r % 60000 / 1000)).padStart(2, "0");
  t.classList.toggle("pouco", r < 60000);
  if (r <= 0) fim();
}
function registrar(it) {
  const ok = it.resp === it.q.correta, s = store.q[it.q.id] || { v: 0, a: 0 };
  s.v++; if (ok) s.a++; s.ok = ok; store.q[it.q.id] = s;
}
function linkApostila(q) {
  const t = tema(q.tema), tp = t && t.topicos.find(x => subDoTopico(x) === q.subtema);
  return tp ? el("a", { href: `#/tema/${t.id}/${tp.id}` }, `Rever ${q.subtema} na apostila →`) : null;
}
function telaQuestao() {
  marcarAba("quiz");
  const it = S.qs[S.i]; S.sel = null; S.conf = false;
  const act = el("button", { class: "btn cheio", type: "button", disabled: true }, "Confirmar");
  const opts = el("div", { class: "opts" });
  const fb = el("div", { hidden: true });
  it.ordem.forEach((orig, pos) => {
    opts.append(el("button", { class: "opt", type: "button", "data-orig": orig, onclick: () => {
      if (S.conf) return; S.sel = orig;
      opts.querySelectorAll(".opt").forEach(o => o.classList.toggle("sel", +o.dataset.orig === orig));
      act.disabled = false;
    } }, el("span", { class: "l" }, L[pos]), el("span", null, it.q.alternativas[orig])));
  });
  const sair = el("div", { class: "confirma", hidden: true }, el("span", null, "Sair e descartar este treino?"),
    el("button", { class: "btn peq perigo", type: "button", onclick: () => { pararSessao(); history.back(); } }, "Sair"),
    el("button", { class: "btn peq leve", type: "button", onclick: () => { sair.hidden = true; } }, "Continuar"));
  const t = tema(it.q.tema);
  act.onclick = () => {
    if (!S.conf) {
      if (S.sel == null) return;
      it.resp = S.sel;
      if (S.modo === "treino") {
        S.conf = true; registrar(it); save();
        const ok = it.resp === it.q.correta;
        opts.querySelectorAll(".opt").forEach(o => {
          const v = +o.dataset.orig; o.disabled = true; o.classList.remove("sel");
          if (v === it.q.correta) o.classList.add("ok"); else if (v === it.resp) o.classList.add("bad");
        });
        fb.hidden = false; fb.className = "fb " + (ok ? "ok" : "bad"); fb.innerHTML = "";
        fb.append(el("strong", null, ok ? "Correto!" : "Incorreto. A resposta é a " + L[it.ordem.indexOf(it.q.correta)] + "."),
          el("p", null, it.q.explicacao));
        act.textContent = S.i < S.qs.length - 1 ? "Próxima" : "Ver resultado";
        fb.scrollIntoView({ block: "nearest", behavior: "smooth" });
        return;
      }
    }
    if (S.i < S.qs.length - 1) { S.i++; telaQuestao(); } else fim();
  };
  render(
    el("div", { class: "q-topo" },
      el("button", { class: "btn peq leve", type: "button", onclick: () => { sair.hidden = false; } }, "Sair"),
      el("span", { class: "cont" }, `${S.i + 1} de ${S.qs.length}`),
      el("span", { class: "timer", id: "q-timer" })),
    barra(S.i / S.qs.length * 100),
    sair,
    el("section", { class: "painel" },
      el("span", null, el("span", { class: "tag" }, (t && t.numero && t.numero < 99 ? `Tema ${t.numero} · ` : "") + it.q.subtema)),
      el("p", { class: "q-texto" }, it.q.enunciado), opts, fb),
    act
  );
  if (S.modo === "simulado") timer();
}

// ---------- resultado ----------
function fim() {
  clearInterval(tick);
  const R = S; S = null;
  if (R.modo === "simulado") R.qs.filter(x => x.resp != null).forEach(registrar);
  const tot = R.qs.length, ac = R.qs.filter(x => x.resp === x.q.correta).length, p = pct(ac, tot);
  store.hist.push({ data: Date.now(), modo: R.modo, tot, ac, temas: [...new Set(R.qs.map(x => x.q.tema))] });
  if (store.hist.length > 300) store.hist.shift();
  save();
  marcarAba("praticar");
  const nao = R.qs.filter(x => x.resp == null).length;
  const subs = [...new Set(R.qs.map(x => x.q.tema + "|" + x.q.subtema))];
  const erradas = R.qs.filter(x => x.resp !== x.q.correta).map(x => x.q);
  render(
    el("section", { class: "painel" },
      el("span", { class: "eyebrow" }, (R.modo === "simulado" ? "Simulado" : "Treino") + " concluído"),
      el("div", { class: "linha entre" }, el("span", { class: "placar" }, p + "%"),
        el("span", { class: "veredito " + (p >= APROVA ? "ok" : "bad") }, p >= APROVA ? "Aprovado" : "Abaixo de " + APROVA + "%")),
      el("p", { class: "muted" }, `${ac} ${ac === 1 ? "acerto" : "acertos"} em ${tot} ${tot === 1 ? "questão" : "questões"}` + (nao ? ` · ${nao} sem resposta (tempo esgotado)` : "") + ". Na prova, são 42 de 60.")),
    el("section", { class: "painel" }, el("h2", { class: "sub" }, "Por subtema"),
      el("div", { class: "pilha" }, subs.map(k => {
        const [tid, sub] = k.split("|"), g = R.qs.filter(x => x.q.tema === tid && x.q.subtema === sub), a = g.filter(x => x.resp === x.q.correta).length, pp = pct(a, g.length);
        return el("div", { class: "por-sub" }, el("span", null, sub), el("span", { class: "mono" }, `${a}/${g.length}`), barra(pp, pp >= APROVA ? "var(--ok)" : "var(--bad)"),
          pp < APROVA && linkApostila(g[0].q));
      }))),
    el("div", { class: erradas.length ? "duas" : "pilha" },
      el("a", { class: "btn leve", href: "#/praticar" }, "Novo treino"),
      erradas.length > 0 && el("button", { class: "btn", type: "button", onclick: () => iniciar(shuffle(erradas), R.modo) }, "Refazer as erradas")),
    el("section", { class: "painel" }, el("h2", { class: "sub" }, "Correção comentada"),
      R.qs.map((x, n) => {
        const ok = x.resp === x.q.correta;
        return el("div", { class: "revisao" },
          el("p", null, el("span", { class: "m " + (ok ? "ok" : "bad") }, (ok ? "✓ " : "✗ ") + (n + 1) + ". "), x.q.enunciado),
          !ok && el("p", { class: "muted" }, "Sua resposta: " + (x.resp == null ? "sem resposta" : x.q.alternativas[x.resp])),
          el("p", null, "Correta: " + x.q.alternativas[x.q.correta]),
          el("p", { class: "muted" }, x.q.explicacao));
      }))
  );
}

// ---------- mais: backup e pacotes ----------
function telaMais() {
  marcarAba("mais");
  const msgB = el("p", { class: "msg", hidden: true }), msgI = el("p", { class: "msg", hidden: true });
  const lerArquivo = (input, fn) => { const f = input.files[0]; if (!f) return; const r = new FileReader(); r.onload = () => { fn(r.result); input.value = ""; }; r.readAsText(f); };
  const mostra = (m, ok, t) => { m.hidden = false; m.className = "msg " + (ok ? "ok" : "bad"); m.textContent = t; };
  const limpar = el("button", { class: "btn peq perigo", type: "button", hidden: true, onclick: () => {
    store.q = {}; store.hist = []; store.lido = {}; save(); mostra(msgB, true, "Progresso apagado neste aparelho."); limpar.hidden = true;
  } }, "Confirmar: apagar progresso");
  const nQ = Object.keys(store.q).length;
  render(
    el("div", { class: "pilha" }, el("span", { class: "eyebrow" }, "Mais"), el("h1", { class: "titulo" }, "Progresso e questões")),
    el("section", { class: "painel" }, el("h2", { class: "sub" }, "Levar o progresso para outro aparelho"),
      el("p", { class: "nota" }, `O progresso fica salvo só neste aparelho (${nQ} questões respondidas, ${store.hist.length} treinos). Para continuar no celular ou no computador, salve o arquivo aqui e carregue lá.`),
      el("div", { class: "duas" },
        el("button", { class: "btn", type: "button", onclick: () => {
          const blob = new Blob([JSON.stringify({ app: "cfg-estudo", v: 1, salvo: new Date().toISOString(), q: store.q, hist: store.hist, lido: store.lido }, null, 1)], { type: "application/json" });
          const a = el("a", { href: URL.createObjectURL(blob), download: "progresso-cfg-" + new Date().toISOString().slice(0, 10) + ".json" });
          document.body.append(a); a.click(); a.remove();
        } }, "Salvar arquivo"),
        el("label", { class: "btn leve" }, "Carregar arquivo", el("input", { type: "file", accept: ".json,application/json", hidden: true, onchange: e => lerArquivo(e.target, txt => {
          try {
            const d = JSON.parse(txt); if (d.app !== "cfg-estudo") throw 0;
            // junta com o que já existe: por questão, fica o registro com mais tentativas
            // (carregar o mesmo arquivo duas vezes não duplica nada)
            for (const [id, s] of Object.entries(d.q || {})) { const m = store.q[id]; if (!m || s.v > m.v) store.q[id] = s; }
            const vistos = new Set(store.hist.map(h => h.data));
            store.hist = store.hist.concat((d.hist || []).filter(h => !vistos.has(h.data))).sort((a, b) => a.data - b.data);
            Object.assign(store.lido, d.lido || {}); save();
            mostra(msgB, true, "Progresso carregado e somado ao deste aparelho.");
          } catch (err) { mostra(msgB, false, "Esse arquivo não é um progresso salvo por este app."); }
        }) }))),
      msgB,
      el("div", { class: "linha" }, el("button", { class: "btn peq leve", type: "button", onclick: () => { limpar.hidden = false; } }, "Apagar progresso"), limpar)),
    el("section", { class: "painel" }, el("h2", { class: "sub" }, "Adicionar questões"),
      el("p", { class: "nota" }, "Carregue um pacote de questões (.json) para adicionar um tema extra. Fica salvo neste aparelho."),
      el("input", { type: "file", accept: ".json,application/json", onchange: e => lerArquivo(e.target, txt => {
        try {
          let arr = JSON.parse(txt); if (!Array.isArray(arr)) arr = arr.questoes || [];
          let ok = 0, bad = 0;
          arr.forEach((q, i) => {
            let c = q && q.correta; if (typeof c === "string") c = L.indexOf(c.trim().toUpperCase());
            if (q && q.tema && q.enunciado && Array.isArray(q.alternativas) && q.alternativas.length >= 2 && q.alternativas.length <= 5 && c >= 0 && c < q.alternativas.length) {
              store.extras.push({ id: "x" + Date.now() + "-" + i, tema: String(q.tema), subtema: q.subtema ? String(q.subtema) : undefined, enunciado: String(q.enunciado),
                alternativas: q.alternativas.map(String), correta: c, explicacao: String(q.explicacao || "") }); ok++;
            } else bad++;
          });
          save(); store.cfg.temas = null;
          mostra(msgI, !!ok, ok ? `${ok} questões importadas` + (bad ? ` (${bad} ignoradas por formato inválido)` : "") + "." : "Nenhuma questão válida no arquivo. Confira o formato abaixo.");
        } catch (err) { mostra(msgI, false, "Não consegui ler o arquivo. Ele precisa ser um JSON no formato abaixo."); }
      }) }),
      msgI,
      store.extras.length > 0 && el("button", { class: "btn peq leve", type: "button", onclick: () => { store.extras = []; store.cfg.temas = null; save(); mostra(msgI, true, "Questões importadas removidas."); } }, "Remover questões importadas"),
      el("details", null, el("summary", null, "Formato do pacote"),
        el("pre", null, '[\n  {\n    "tema": "Renda Fixa",\n    "subtema": "6.2",\n    "enunciado": "Texto da questão",\n    "alternativas": ["A", "B", "C", "D"],\n    "correta": 1,\n    "explicacao": "Por que a B está certa"\n  }\n]'),
        el("p", { class: "nota" }, "\"correta\" é a posição da alternativa certa, começando em 0 (ou a letra: \"B\"). \"subtema\" é opcional."))),
    el("section", { class: "painel" }, el("h2", { class: "sub" }, "Instalar no celular"),
      el("p", { class: "nota" }, "Android (Chrome): menu ⋮ → Adicionar à tela inicial / Instalar app. iPhone (Safari): botão Compartilhar → Adicionar à Tela de Início. Depois do primeiro acesso, abre sem internet.")),
    el("p", { class: "nota" }, "Material de estudo próprio, baseado no programa da certificação CFG da ANBIMA. Não é material oficial da ANBIMA.")
  );
}

// ---------- offline e atualizações ----------
if ("serviceWorker" in navigator && location.protocol !== "file:") {
  navigator.serviceWorker.register("sw.js").then(reg => {
    reg.addEventListener("updatefound", () => {
      const w = reg.installing;
      w && w.addEventListener("statechange", () => {
        if (w.state === "installed" && navigator.serviceWorker.controller) aviso("Há uma versão nova do conteúdo.", () => location.reload(), "Atualizar");
      });
    });
  }).catch(() => {});
}

carregar().then(rota).catch(err => {
  render(el("section", { class: "painel" }, el("h2", { class: "sub" }, "Não consegui carregar o conteúdo"),
    el("p", { class: "muted" }, "Confira a conexão e abra de novo. Depois do primeiro acesso, o app funciona sem internet."),
    el("button", { class: "btn", type: "button", onclick: () => location.reload() }, "Tentar de novo")));
  console.error(err);
});
