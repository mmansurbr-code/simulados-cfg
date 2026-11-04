// Offline: rede primeiro (conteúdo sempre atualizado quando há internet),
// cache como reserva. A linha de dados/ e a VERSAO são atualizadas pelo
// ferramentas/importar.py; ao mudar app.js ou estilo.css, troque a VERSAO à mão.
const VERSAO = "cfg-cad35668";
const ARQUIVOS = [
  "./", "index.html", "estilo.css", "app.js", "manifest.webmanifest",
  "icones/icone.svg", "icones/icone-192.png", "icones/icone-512.png", "icones/icone-180.png",
  "dados/temas.json", "dados/tema1.json", "dados/tema2.json", "dados/tema3.json", "dados/tema4.json", "dados/tema5.json", "dados/tema6.json", "dados/tema7.json", "dados/tema8.json", "dados/tema9.json", "dados/tema10.json", "dados/tema11.json", "dados/tema12.json", "dados/manuais/revisao.json",
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSAO).then(c => c.addAll(ARQUIVOS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== VERSAO).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  e.respondWith(
    fetch(req).then(res => {
      if (res.ok) { const copia = res.clone(); caches.open(VERSAO).then(c => c.put(req, copia)); }
      return res;
    }).catch(() => caches.match(req, { ignoreSearch: true }).then(r => r || caches.match("index.html")))
  );
});
