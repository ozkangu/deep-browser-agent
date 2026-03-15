# Deep Browser Agent — Kapsamli Rehber

> Chrome DevTools MCP + LangGraph DeepAgent ile browser otomasyonu.
> Bu rehber gercek testlere dayanmaktadir (Hacker News, Google, Skyscanner, Wikipedia, GitHub, httpbin).

---

## 1. Nedir?

**Chrome DevTools MCP**, Chrome browser'i kontrol eden bir MCP (Model Context Protocol) sunucusudur.
29 adet tool sunar: navigasyon, tiklama, form doldurma, screenshot, JS calistirma, network izleme, performans analizi.

**LangGraph DeepAgent**, LangChain ekosistemindeki ajan cercevesidir.
Planlama, dosya yonetimi, sub-agent spawning ve uzun sureli bellek ozellikleri sunar.

**Bu proje**, ikisini birlestirerek bir AI ajaninin browser'i tamamen yonetmesini saglar.

```
DeepAgent/ReAct → langchain-mcp-adapters (stdio) → chrome-devtools-mcp → Chrome (CDP)
```

---

## 2. Kurulum

### On Gereksinimler

```bash
# Node.js v20.19+ (chrome-devtools-mcp icin)
node --version

# Python 3.11+
python3 --version

# Chrome browser yuklu olmali
ls /Applications/Google\ Chrome.app  # macOS
```

### Proje Kurulumu

```bash
cd ~/chrome-mcp

# Virtual environment olustur
python3 -m venv .venv
source .venv/bin/activate

# Temel kurulum + Anthropic
pip install -e ".[anthropic]"

# Veya tum provider'larla
pip install -e ".[all-providers]"

# DeepAgent ile (opsiyonel)
pip install -e ".[deep,anthropic]"

# .env dosyasini ayarla
cp .env.example .env
# Icine API key'ini yaz
```

### chrome-devtools-mcp Test

```bash
# MCP'nin calistigini dogrula
npx -y chrome-devtools-mcp@latest --help
```

---

## 3. LLM Provider Yapilandirmasi

Proje 6 farkli provider destekler. `.env` dosyasinda veya CLI'da secebilirsin.

### Anthropic (varsayilan)
```bash
AGENT_MODEL=anthropic:claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-...
```

### OpenRouter (cok modelli gateway)
```bash
AGENT_MODEL=openrouter:anthropic/claude-sonnet-4-20250514
OPENROUTER_API_KEY=sk-or-...

# Diger OpenRouter modelleri:
# openrouter:openai/gpt-4o
# openrouter:deepseek/deepseek-chat-v3
# openrouter:meta-llama/llama-4-maverick
# openrouter:google/gemini-2.5-pro
```

### Ollama (lokal LLM)
```bash
AGENT_MODEL=ollama:llama3.3
OLLAMA_BASE_URL=http://localhost:11434

# Once modeli cek:
# ollama pull llama3.3
```

### Azure AI Foundry
```bash
AGENT_MODEL=azure:gpt-4o
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

### Google Gemini
```bash
AGENT_MODEL=google:gemini-2.5-pro
GOOGLE_API_KEY=...
```

### OpenAI
```bash
AGENT_MODEL=openai:gpt-4o
OPENAI_API_KEY=sk-...
```

### CLI ile provider secimi
```bash
deep-browser-agent --model anthropic:claude-sonnet-4-20250514
deep-browser-agent --model openrouter:deepseek/deepseek-chat-v3
deep-browser-agent --model ollama:llama3.3
deep-browser-agent --providers  # mevcut preset'leri listele
```

---

## 4. Kullanim

### Interaktif CLI

```bash
deep-browser-agent                                       # normal mod
deep-browser-agent --headless                            # headless
deep-browser-agent --model ollama:llama3.3               # lokal model
deep-browser-agent --browser-url http://localhost:9222   # mevcut Chrome'a baglan
```

### Python API

```python
import asyncio
from deep_browser_agent import BrowserAgentSession, AgentConfig

async def main():
    config = AgentConfig(model="anthropic:claude-sonnet-4-20250514")

    async with BrowserAgentSession(config=config) as session:
        result = await session.invoke(
            "news.ycombinator.com'a git ve ilk 5 haberi listele"
        )
        # result["messages"] icerisinde ajan cevabi var

asyncio.run(main())
```

### Farkli Provider ile

```python
config = AgentConfig(
    model="openrouter:deepseek/deepseek-chat-v3",
    api_key="sk-or-...",
    headless=True,
)
```

---

## 5. KRITIK: UID-Tabanli Etkilesim Modeli

> Bu, projenin en onemli teknik detayidir.

Chrome DevTools MCP, CSS selector degil **UID** kullanir. Akis:

```
1. take_snapshot → a11y agaci doner, her elemana UID atanir
2. UID ile etkilesim: fill(uid="1_2", value="test") veya click(uid="1_5")
3. Her navigasyonda UID'ler degisir!
```

### Ornek a11y snapshot ciktisi:

```
uid=1_0 RootWebArea url="https://httpbin.org/forms/post"
  uid=1_1 StaticText "Customer name: "
  uid=1_2 textbox "Customer name: "          ← fill ile doldur
  uid=1_3 StaticText "Telephone: "
  uid=1_4 textbox "Telephone: "              ← fill ile doldur
  uid=1_8 radio " Small"                     ← click ile sec
  uid=1_9 radio " Medium"                    ← click ile sec
  uid=1_12 checkbox " Bacon"                 ← click ile toggle
  uid=1_24 button "Submit order"             ← click ile gonder
```

### Gercek calisan form doldurma:

```python
# 1. Snapshot al
snap = await session.call_tool("take_snapshot", {})

# 2. UID'leri oku ve kullan
await session.call_tool("fill", {"uid": "1_2", "value": "Gurkan Ozkan"})
await session.call_tool("fill", {"uid": "1_4", "value": "+90 555 123 4567"})
await session.call_tool("click", {"uid": "1_9"})   # Medium radio
await session.call_tool("click", {"uid": "1_12"})   # Bacon checkbox
await session.call_tool("click", {"uid": "1_24"})   # Submit

# 3. Toplu doldurma (fill_form)
await session.call_tool("fill_form", {
    "elements": [
        {"uid": "1_2", "value": "Gurkan Ozkan"},
        {"uid": "1_4", "value": "+90 555 123 4567"},
        {"uid": "1_6", "value": "gurkan@test.com"},
    ],
    "includeSnapshot": True
})
```

### UID Kurallari:
- UID formati: `pageNum_elementNum` (orn. `1_2`, `3_15`)
- Her navigate_page sonrasi UID prefix'i artar (1_X → 2_X → 3_X)
- **Asla** eski snapshot'tan UID kullanma — her zaman taze snapshot al
- CSS selector gecersizdir — `fill(selector="input")` CALISMAZ

---

## 6. Tool Parametre Referansi (Test Edilmis)

| Tool | Parametreler | Notlar |
|------|-------------|--------|
| `navigate_page` | `url`, `type` (url/back/forward/reload) | `type` opsiyonel |
| `take_snapshot` | (yok) | a11y agaci + UID'ler doner |
| `take_screenshot` | (yok) | PNG goruntu doner |
| `click` | `uid` (zorunlu), `dblClick` | Snapshot'tan UID |
| `fill` | `uid` (zorunlu), `value` (zorunlu) | Textbox, combobox icin |
| `fill_form` | `elements: [{uid, value}]`, `includeSnapshot` | Toplu doldurma |
| `evaluate_script` | `function` (zorunlu), `args` | Arrow function olmali! |
| `press_key` | `key` (zorunlu) | "Enter", "Tab", "Escape" vb. |
| `wait_for` | `text: [str]` (zorunlu), `timeout` | Dizi olmali! |
| `hover` | `uid` (zorunlu) | Snapshot'tan UID |
| `list_pages` | (yok) | Tum acik tab'lari listeler |
| `new_page` | `url` | Yeni tab acar |
| `select_page` | `index` (0-based) | Tab degistirir |
| `close_page` | `index` | Tab kapatir (son tab kapatilamaz) |
| `list_network_requests` | (yok) | reqid, method, url, status |
| `list_console_messages` | (yok) | msgid, level, text |
| `resize_page` | `width`, `height` | Viewport boyutu degistirir |

### evaluate_script DIKKAT:
```
YANLIS: evaluate_script(script="document.title")
DOGRU:  evaluate_script(function="() => document.title")
DOGRU:  evaluate_script(function="() => JSON.stringify({title: document.title})")
```

---

## 7. Gercek Test Sonuclari

### Calisan Siteler
| Site | Sonuc | Detay |
|------|-------|-------|
| Hacker News | ✅ Tam | Navigasyon, veri cekme, link tiklama |
| Wikipedia | ✅ Tam | Navigasyon, hover, link tiklama |
| GitHub | ✅ Tam | Repo bilgisi, DOM okuma, screenshot |
| httpbin | ✅ Tam | Form doldurma, submit, sonuc okuma |
| example.com | ✅ Tam | Temel navigasyon |

### Bot Korumasina Takilanlar
| Site | Sonuc | Detay |
|------|-------|-------|
| Google | ⚠️ Kismi | Ilk arama calisiyor, ardindan reCAPTCHA |
| Skyscanner | ❌ Engellendi | "Are you a person or a robot?" |

### Bot Korumasini Asmak
1. **Non-headless mod** kullan (browser penceresi gorunsun)
2. **Mevcut Chrome oturumuna baglan:**
   ```bash
   # Chrome'u debug portuyla baslat
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

   # MCP'yi bagla
   deep-browser-agent --browser-url http://localhost:9222
   ```
3. `--isolated` kaldir (kalici cookie/session icin)
4. Proxy kullan: `--proxyServer socks5://proxy:1080`

---

## 8. DeepAgent Entegrasyonu

### Temel Entegrasyon (langchain-mcp-adapters)

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model

async with MultiServerMCPClient({
    "chrome-devtools": {
        "command": "npx",
        "args": ["-y", "chrome-devtools-mcp@latest", "--headless", "--isolated"],
        "transport": "stdio",
    }
}) as client:
    tools = await client.get_tools()  # 29 MCP tool otomatik kesfedilir
    model = init_chat_model("anthropic:claude-sonnet-4-20250514")

    agent = create_deep_agent(
        model=model,
        tools=tools,
        system_prompt="Browser automation agent...",
    )

    result = await agent.ainvoke({
        "messages": [{"role": "user", "content": "Go to example.com"}]
    })
```

### DeepMCPAgent ile HTTP Bridge

```bash
# 1. stdio → HTTP proxy baslat
npx @anthropic/mcp-proxy --port 3100 -- npx -y chrome-devtools-mcp@latest

# 2. DeepMCPAgent ile baglan
pip install "deepmcpagent[deep]"
```

```python
from deepmcpagent import HTTPServerSpec, build_deep_agent

graph, _ = await build_deep_agent(
    servers={"chrome": HTTPServerSpec(url="http://127.0.0.1:3100/mcp", transport="http")},
    model="anthropic:claude-sonnet-4-20250514",
)
```

### Bilinen Kisitlama
DeepAgent sub-agent'lari (task tool ile) MCP tool'larina dogrudan eriseemiyor.
Tum browser islemlerini ana agent uzerinden yurut.

---

## 9. Dosya Yapisi

```
chrome-mcp/
├── pyproject.toml                        # Bagimliliklar ve proje tanimlari
├── .env.example                          # Ortam degiskenleri sablonu
├── GUIDE.md                              # Bu rehber
├── config/
│   └── mcp_servers.json                  # MCP sunucu konfigurasyonlari
├── src/deep_browser_agent/
│   ├── __init__.py                       # Public API
│   ├── config.py                         # AgentConfig — tum ayarlar
│   ├── providers.py                      # Multi-provider LLM desteği
│   ├── agent.py                          # Cekirdek: DeepAgent + MCP baglantisi
│   ├── skills.py                         # Test edilmis browser skill'leri
│   └── cli.py                            # Interaktif terminal arayuzu
├── examples/
│   ├── basic_navigation.py               # Sayfa gezinme
│   ├── form_automation.py                # Form doldurma
│   ├── performance_audit.py              # Performans analizi
│   ├── multi_agent_scraper.py            # Coklu ajan scraping
│   └── deepmcp_http_bridge.py            # DeepMCPAgent HTTP yaklasimi
└── test_screenshots/                     # Test sirasinda alinan ekran goruntuleri
```

---

## 10. Hizli Baslangic Tarifleri

### Tarif 1: Basit sayfa okuma
```bash
deep-browser-agent --headless
> url https://news.ycombinator.com
> Ilk 5 haberi listele
```

### Tarif 2: Form doldurma
```bash
deep-browser-agent
> httpbin.org/forms/post adresine git ve formu doldur: isim=Ali, tel=555-0000
```

### Tarif 3: Lokal model ile
```bash
ollama pull llama3.3
deep-browser-agent --model ollama:llama3.3
```

### Tarif 4: OpenRouter ile ucuz model
```bash
export OPENROUTER_API_KEY=sk-or-...
deep-browser-agent --model openrouter:deepseek/deepseek-chat-v3
```

### Tarif 5: Mevcut Chrome oturumuna baglanma
```bash
# Terminal 1: Chrome'u baslat
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Terminal 2: Agent'i bagla
deep-browser-agent --browser-url http://localhost:9222
```
