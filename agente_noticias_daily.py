""" Agente de Notícias Diárias - versão inicial Arquivo: agente_noticias_daily.py Descrição:

Agrega notícias (RSS + APIs) por tópicos: tecnologia, bélica, IA, medicina, carros, esportes, jurídico.

Foca em regiões: Índia, China, Japão, EUA, Europa, e Brasil (menor prioridade para mercados brasileiros).

Agrega métricas de mercado (ações, bitcoin, ouro) e detecta grandes movimentações.

Tenta detectar/alertar possíveis fake news cruzando com fact-checkers e checando corroboração em múltiplas fontes.

Gera um resumo diário e pode enviar por canais (email/telegram/arquivo).


OBS:

Este código é um esqueleto arquitetural e contém TODOs para inserir chaves de API e adaptar endpoints.

Requer bibliotecas externas (requests, feedparser, yfinance, etc.). Veja o bloco REQUIREMENTS abaixo.


REQUIREMENTS (instalar via pip): pip install requests feedparser beautifulsoup4 python-dateutil pydantic yfinance newspaper3k

Opcional: openai, alphavantage, coinmarketcap, python-telegram-bot

USO: preencher as chaves em CONFIG, ajustar fontes RSS/APIs e rodar python agente_noticias_daily.py.

"""

from dataclasses import dataclass, field from typing import List, Dict, Any, Optional import time import requests import feedparser import yfinance as yf from datetime import datetime, timedelta from urllib.parse import urlparse import hashlib import logging

---------- CONFIG ----------

API_KEYS = { 'NEWSAPI': 'YOUR_NEWSAPI_KEY',                # opcional, https://newsapi.org/ 'ALPHA_VANTAGE': 'YOUR_ALPHA_VANTAGE_KEY',    # para ouro (XAU) ou series financeiras 'OPENAI': 'YOUR_OPENAI_API_KEY',              # opcional, se quiser sumarização via OpenAI 'FACTCHECKTOOLS': 'YOUR_GOOGLE_API_KEY',      # opcional, Google Fact Check Tools # Adicione outras chaves: COINGECKO não precisa de chave }

Fontes recomendadas (RSS/APIs) - personalize conforme preferência

RSS_SOURCES = { 'global_tech': [ 'https://www.theverge.com/rss/index.xml', 'https://feeds.arstechnica.com/arstechnica/index', ], 'china_media': [ 'https://www.scmp.com/rss/91/feed', ], 'india_media': [ 'https://www.hindustantimes.com/rss/topnews/rssfeed.xml', ], 'japan_media': [ 'https://www.japantimes.co.jp/feed/', ], 'us_media': [ 'https://www.reuters.com/rssFeed/topNews', ], 'europe_media': [ 'https://www.ft.com/?format=rss', ], 'brazil_media': [ 'https://g1.globo.com/rss/g1/', 'https://feeds.folha.uol.com.br/emcimadahora/rss091.xml' ], 'cars_global': [ 'https://www.autocar.co.uk/rss.xml', 'https://www.motor1.com/rss/all.xml' ], 'sports_football': [ 'https://www.espn.com/espn/rss/football/news', ] }

Domínios de alta confiança e fact-checkers para consulta

FACT_CHECK_DOMAINS = [ 'snopes.com', 'factcheck.org', 'reuters.com', 'apnews.com', 'fullfact.org', 'aosfatos.org.br' ]

Países de interesse (prioridade)

PRIORITY_REGIONS = ['India', 'China', 'Japan', 'USA', 'Europe', 'Brazil']

Configurações de alerta de mercado

MARKET_THRESHOLDS = { 'stock_move_pct': 5.0,   # alerta se ação subir/baixar >= 5% no dia 'crypto_move_pct': 8.0,  # alerta para criptos 'gold_move_pct': 2.0, }

Palavras-chave geopolíticas que indicam ação na "3ª guerra fria" (EUA x China)\C

COLD_WAR_KEYWORDS = [ 'sanction', 'sanctions', 'tariff', 'military exercise', 'no-fly zone', 'blockade', 'export control', 'technology ban', 'chip ban', 'espionage', 'spy', 'diplomatic', 'consulate' ]

Principais investidores para monitorar menções (

MAJOR_INVESTORS = ['BlackRock', 'Berkshire Hathaway', 'SoftBank', 'Vanguard', 'China Investment Corporation']

---------- UTILIDADES ----------

logging.basicConfig(level=logging.INFO)

def normalize_url(url: str) -> str: return url.split('?')[0].rstrip('/')

def article_id(url: str) -> str: return hashlib.sha1(normalize_url(url).encode('utf-8')).hexdigest()

---------- COLETA DE NOTÍCIAS (RSS + NewsAPI opcional) ----------

def fetch_rss_feed(url: str, max_items: int = 10) -> List[Dict[str, Any]]: logging.info(f'Fetching RSS: {url}') try: parsed = feedparser.parse(url) except Exception as e: logging.warning(f'Erro ao parsear {url}: {e}') return []

items = []
for entry in parsed.entries[:max_items]:
    items.append({
        'title': entry.get('title'),
        'link': entry.get('link'),
        'published': entry.get('published', ''),
        'summary': entry.get('summary', ''),
        'id': article_id(entry.get('link', ''))
    })
return items

def aggregate_rss(sources: Dict[str, List[str]], per_source: int = 5) -> List[Dict[str, Any]]: articles = [] for key, urls in sources.items(): for u in urls: articles += fetch_rss_feed(u, max_items=per_source) # deduplicate by id seen = set() dedup = [] for a in articles: if a['id'] not in seen: dedup.append(a); seen.add(a['id']) return dedup

---------- Sumarização (Placeholder para LLM) ----------

def summarize_text_with_openai(text: str, max_tokens: int = 200) -> str: """ Função placeholder: se desejar usar OpenAI, implemente o request à API aqui. Por enquanto, faz um corte simples. """ # TODO: implementar chamada ao OpenAI ChatCompletion (ou outro LLM) com prompt de resumo snippet = text.strip() return (snippet[:800] + '...') if len(snippet) > 800 else snippet

---------- DETECÇÃO SIMPLES DE 'FAKE NEWS' ----------

def is_from_factcheck(url: str) -> bool: parsed = urlparse(url) domain = parsed.netloc.lower() return any(d in domain for d in FACT_CHECK_DOMAINS)

def check_fake_by_corroboration(article: Dict[str, Any], all_articles: List[Dict[str, Any]]) -> Dict[str, Any]: """ Estratégia simples: - procura por outras fontes cobrindo o mesmo título/assunto (mesmas palavras-chave no título) - se só existe em fontes obscuras -> marcar como 'possible_fake' - se aparece em fact-checkers -> retornar veredito """ title = (article.get('title') or '').lower() matches = [a for a in all_articles if a is not article and (a.get('title') or '').lower().split()[:5] == title.split()[:5]]

result = {'article_id': article.get('id'), 'corroboration_count': len(matches), 'likely_fake': False, 'notes': ''}

if any(is_from_factcheck(a['link']) for a in matches):
    result['likely_fake'] = False
    result['notes'] = 'Found in fact-check sources (may be addressed by fact-checker).'
    return result

if len(matches) == 0:
    # check domain credibility
    domain = urlparse(article.get('link')).netloc.lower()
    if domain.endswith('.com') and 'news' in domain:
        result['likely_fake'] = False
        result['notes'] = 'Single-source but domain looks like news site.'
    else:
        result['likely_fake'] = True
        result['notes'] = 'Single-source + no corroboration detected (possible low reliability).'
else:
    result['notes'] = f'Corroborated by {len(matches)} sources.'
return result

---------- MERCADO: AÇÕES, CRYPTO, OURO ----------

def fetch_stock_price(ticker: str) -> Optional[Dict[str, Any]]: try: t = yf.Ticker(ticker) hist = t.history(period='2d') if hist.empty: return None last = hist['Close'].iloc[-1] prev = hist['Close'].iloc[-2] pct = (last - prev) / prev * 100 return {'ticker': ticker, 'last': float(last), 'prev': float(prev), 'pct': float(pct)} except Exception as e: logging.warning(f'Erro fetch_stock_price {ticker}: {e}') return None

def fetch_crypto_coinmarket(coin_id: str = 'bitcoin') -> Optional[Dict[str, Any]]: try: url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=2' resp = requests.get(url, timeout=10).json() prices = resp.get('prices', []) if len(prices) < 2: return None last = prices[-1][1] prev = prices[0][1] pct = (last - prev) / prev * 100 return {'coin': coin_id, 'last': last, 'prev': prev, 'pct': pct} except Exception as e: logging.warning(f'Erro fetch_crypto: {e}') return None

def fetch_gold_price_alpha(symbol: str = 'XAUUSD') -> Optional[Dict[str, Any]]: # TODO: implementar com AlphaVantage (TIME_SERIES_DAILY) ou outra fonte return None

---------- AGENTE PRINCIPAL ----------

@dataclass class NewsAgentConfig: regions: List[str] = field(default_factory=lambda: PRIORITY_REGIONS) rss_sources: Dict[str, List[str]] = field(default_factory=lambda: RSS_SOURCES) market_thresholds: Dict[str, float] = field(default_factory=lambda: MARKET_THRESHOLDS) major_investors: List[str] = field(default_factory=lambda: MAJOR_INVESTORS) cold_war_keywords: List[str] = field(default_factory=lambda: COLD_WAR_KEYWORDS)

class NewsAgent: def init(self, config: NewsAgentConfig): self.config = config self.articles = []

def collect(self):
    logging.info('Coletando artigos RSS...')
    self.articles = aggregate_rss(self.config.rss_sources, per_source=5)
    logging.info(f'Artigos coletados: {len(self.articles)}')

def analyze_fake_news(self):
    results = []
    for a in self.articles:
        r = check_fake_by_corroboration(a, self.articles)
        results.append(r)
    return results

def market_snapshot(self):
    snapshot = {}
    # Exemplo: SP500 (usando ticker '^GSPC' via yfinance)
    sp500 = fetch_stock_price('^GSPC')
    if sp500: snapshot['sp500'] = sp500
    btc = fetch_crypto_coinmarket('bitcoin')
    if btc: snapshot['bitcoin'] = btc
    # TODO: adicionar ouro e ações brasileiras (B3) — ex: 'IBOV' não é um ticker direto para yfinance
    return snapshot

def detect_cold_war_actions(self):
    alerts = []
    for a in self.articles:
        title = (a.get('title') or '').lower()
        if any(k.lower() in title for k in self.config.cold_war_keywords):
            alerts.append({'article': a, 'matched_keywords': [k for k in self.config.cold_war_keywords if k.lower() in title]})
    return alerts

def detect_major_investor_mentions(self):
    mentions = []
    for a in self.articles:
        t = (a.get('title') or '') + ' ' + (a.get('summary') or '')
        for m in self.config.major_investors:
            if m.lower() in t.lower():
                mentions.append({'investor': m, 'article': a})
    return mentions

def generate_daily_digest(self) -> Dict[str, Any]:
    # steps: coletar, analisar, snapshots de mercado, sumarizar
    now = datetime.utcnow().isoformat()
    digest = {'generated_at': now}
    self.collect()
    digest['fake_checks'] = self.analyze_fake_news()
    digest['market'] = self.market_snapshot()
    digest['cold_war_alerts'] = self.detect_cold_war_actions()
    digest['major_investor_mentions'] = self.detect_major_investor_mentions()

    # criar seções por tópico
    sections = {}
    # exemplo simples: filtrar por palavras-chave no título
    sections['technology'] = [a for a in self.articles if any(w in (a.get('title') or '').lower() for w in ['tech','ai','artificial','robot','chip','semiconductor','software'])][:10]
    sections['military'] = [a for a in self.articles if any(w in (a.get('title') or '').lower() for w in ['military','army','navy','air force','missile','drone','war','conflict'])][:10]
    sections['medicine'] = [a for a in self.articles if any(w in (a.get('title') or '').lower() for w in ['health','medicine','vaccine','covid','pharma','hospital'])][:10]
    sections['cars'] = [a for a in self.articles if any(w in (a.get('title') or '').lower() for w in ['car','automotive','ev','tesla','bmw','mercedes','toyota'])][:10]
    sections['sports'] = [a for a in self.articles if any(w in (a.get('title') or '').lower() for w in ['football','f.c.','soccer','futebol','f1','formula']))][:15]
    # resumo automatizado de top N por seção
    digest['sections'] = {}
    for k, items in sections.items():
        digest['sections'][k] = []
        for it in items:
            summary = summarize_text_with_openai(it.get('summary') or it.get('title') or '')
            digest['sections'][k].append({'title': it.get('title'), 'link': it.get('link'), 'summary': summary})

    return digest

---------- PROMPT / TREINAMENTO SIMPLIFICADO ----------

def build_summary_prompt(examples: List[Dict[str, str]], tone: str = 'concise neutral') -> str: """ Constrói um prompt few-shot para o LLM que será usado para sumarizar as notícias no tom desejado. Salve o prompt em um lugar editável para "treinar" o agente. """ prompt = f"You are a news summarization assistant. Tone: {tone}. Summarize the article in 2-4 sentences.\n\n" for ex in examples: prompt += f"Article:\n{ex['article']}\nSummary:\n{ex['summary']}\n---\n" prompt += "Now summarize the following article:\n{article}\nSummary:\n" return prompt

---------- SALVAR/ENVIAR DIGEST ----------

def save_digest_to_file(digest: Dict[str, Any], path: str = 'digest.json'): import json with open(path, 'w', encoding='utf-8') as f: json.dump(digest, f, ensure_ascii=False, indent=2) logging.info(f'Digest salvo em {path}')

---------- EXEMPLO DE USO ----------

if name == 'main': cfg = NewsAgentConfig() agent = NewsAgent(cfg) digest = agent.generate_daily_digest() save_digest_to_file(digest, path='daily_digest.json')

# TODO: Implementar envio via Telegram/Email/Slack
print('Digest gerado: veja o arquivo daily_digest.json')

------------------------------

NOTAS FINAIS / TAREFAS RECOMENDADAS:

1) Substituir summarization placeholder por chamadas reais a um LLM (OpenAI, Anthropic ou local), ajustando o prompt

2) Melhorar detecção de fake news: usar Google Fact Check Tools API, Snopes API, e checar imagens (reverse image search)

3) Para métricas financeiras, integrar AlphaVantage, YahooFinance (já usamos yfinance), e CoinGecko para cripto

4) Para esportes, integrar APIs como football-data.org, API-Football, ou usar RSS/ESPN

5) Criar testes e CI, e configurar uma scheduler (cron / cloud function) para rodar diariamente

6) Implementar armazenamento histórico (DB SQLite/Postgres) para detectar movimentos maiores ao longo do tempo

7) Para "treinar" o treinador, adicionar uma interface (JSON/YAML) com exemplos de resumos preferidos

Se quiser, eu completo a integração com APIs específicas (OpenAI, NewsAPI, AlphaVantage, Telegram) e

adapto os filtros por país/região e o formato final do digest (HTML, Markdown ou PDF).
