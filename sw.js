// Offline: rede primeiro (conteúdo sempre atualizado quando há internet),
// cache como reserva. A linha de dados/ e a VERSAO são atualizadas pelo
// ferramentas/importar.py; ao mudar app.js ou estilo.css, troque a VERSAO à mão.
const VERSAO = "cfg-2ea380b0";
const ARQUIVOS = [
  "./", "index.html", "estilo.css", "app.js", "manifest.webmanifest",
  "icones/icone.svg", "icones/icone-192.png", "icones/icone-512.png", "icones/icone-180.png",
  "dados/temas.json", "dados/tema1.json", "dados/tema2.json", "dados/tema3.json", "dados/tema4.json", "dados/tema5.json", "dados/tema6.json", "dados/tema7.json", "dados/tema8.json", "dados/tema9.json", "dados/tema10.json", "dados/tema11.json", "dados/tema12.json", "dados/manuais/revisao.json", "dados/audios.json",
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSAO).then(c => c.addAll(ARQUIVOS)).then(() => self.skipWaiting()));
});

// Áudios ficam num cache próprio, que só o botão "Baixar para o carro" preenche e
// que sobrevive às trocas de VERSAO (são dezenas de MB por tema).
const AUDIO = "cfg-audio";

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== VERSAO && k !== AUDIO).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  if (new URL(req.url).pathname.includes("/apostilas/audio/")) return e.respondWith(audio(req));
  e.respondWith(
    fetch(req).then(res => {
      if (res.ok) { const copia = res.clone(); caches.open(VERSAO).then(c => c.put(req, copia)); }
      return res;
    }).catch(() => caches.match(req, { ignoreSearch: true }).then(r => r || caches.match("index.html")))
  );
});

// Faixa baixada: responde do cache, inclusive pedidos parciais (Range), que é como
// o tocador pede o áudio ao pular para outro ponto. Sem cópia local, vai à rede.
async function audio(req) {
  const salvo = await caches.open(AUDIO).then(c => c.match(req.url));
  if (!salvo) return fetch(req);
  const range = req.headers.get("range");
  if (!range) return salvo;
  const buf = await salvo.arrayBuffer(), tam = buf.byteLength;
  const [, ini, fim] = /bytes=(\d*)-(\d*)/.exec(range) || [];
  const a = ini ? +ini : Math.max(0, tam - +fim), b = ini && fim ? Math.min(+fim, tam - 1) : tam - 1;
  return new Response(buf.slice(a, b + 1), { status: 206, headers: {
    "Content-Type": "audio/mpeg", "Content-Length": String(b - a + 1),
    "Content-Range": `bytes ${a}-${b}/${tam}`, "Accept-Ranges": "bytes" } });
}
