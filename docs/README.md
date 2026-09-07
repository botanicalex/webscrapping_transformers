# Radar de Riesgo Social — Front de consulta

`busqueda_pipeline.html` es la interfaz de consulta (HTML + JS vanilla, sin build).
Se publica por **GitHub Pages** desde esta carpeta `docs/` y habla con la **API**
(`src/api.py`, FastAPI) a través de un túnel HTTPS.

La API corre donde haya GPU (Google Colab), porque el pipeline usa el modelo NLI
`mDeBERTa-v3`. El túnel de **cloudflared** expone esa API con una URL pública HTTPS
que el front recibe por el parámetro `?api=`.

```
[GitHub Pages: busqueda_pipeline.html]  --fetch-->  [https://xxxx.trycloudflare.com]
                                                              │ (túnel cloudflared)
                                                     [Colab: uvicorn src.api:app :8000]
```

---

## 1. Correr la API en Colab con cloudflared

En un notebook de Colab **con GPU** (`Entorno de ejecución → Cambiar tipo → GPU`):

```python
# 1. Clonar el repo y entrar
!git clone https://github.com/botanicalex/webscrapping_transformers.git
%cd webscrapping_transformers

# 2. Instalar dependencias (incluye fastapi, uvicorn, httpx)
!pip install -q -r requirements.txt
!playwright install chromium        # el scraping usa Playwright

# 3. Descargar cloudflared (túnel HTTPS, sin cuenta)
!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared
!chmod +x cloudflared

# 4. Levantar la API en segundo plano (puerto 8000)
import subprocess, time
api = subprocess.Popen(["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"])
time.sleep(60)  # uvicorn carga mDeBERTa al arrancar: puede tardar VARIOS minutos

# 5. Abrir el túnel y ver la URL pública
!./cloudflared tunnel --url http://localhost:8000
```

En la salida de la última celda aparece una línea con la URL del túnel, algo como:

```
+--------------------------------------------------------+
|  https://abc-def-ghi.trycloudflare.com                 |
+--------------------------------------------------------+
```

Esa `https://....trycloudflare.com` es el **API_BASE** que usará el front.
Dejá esa celda corriendo: mientras esté viva, el túnel funciona.

> **Verificación rápida:** abrí `https://....trycloudflare.com/health` en el navegador.
> Debe responder un JSON con `"ok": true` y los cortes activos.

Notas:
- **uvicorn tarda varios minutos en arrancar**: el pipeline NLI (`mDeBERTa-v3`) se
  carga al inicio de la app (carga temprana, no perezosa, para evitar un conflicto
  CUDA/torch en el thread del worker que daba 500 en `/analizar`). El `time.sleep(60)`
  es un mínimo; si el túnel expone el puerto antes de que el modelo termine de cargar,
  las primeras requests fallan con *connection refused*. Lo seguro es esperar a que
  `https://....trycloudflare.com/health` responda `"ok": true` antes de usar el front.
- El túnel *quick* de cloudflared no necesita cuenta ni login, pero la URL **cambia
  cada vez** que se reinicia. Hay que volver a copiarla al front.
- La primera consulta a `/analizar` es lenta (carga el modelo + scrapea en vivo):
  puede tardar **varios minutos**. El front muestra la pantalla de carga mientras tanto.

---

## 2. Abrir el front con la URL del túnel

El front lee la API del parámetro `?api=` en la URL. Sin parámetro usa
`http://localhost:8000` (solo sirve si la API corre en tu propia máquina).

```js
const params = new URLSearchParams(window.location.search);
const API_BASE = params.get("api") || "http://localhost:8000";
```

Para usar la API de Colab, agregá `?api=` + la URL del túnel al link de GitHub Pages:

```
https://botanicalex.github.io/webscrapping_transformers/busqueda_pipeline.html?api=https://abc-def-ghi.trycloudflare.com
```

**Importante:** como GitHub Pages sirve por HTTPS, el `?api=` **debe ser https**
(el túnel de cloudflared ya lo es). Un `?api=http://...` sería bloqueado por el
navegador (*mixed content*).

---

## 3. Ejemplo del link completo

Suponiendo que cloudflared imprimió `https://abc-def-ghi.trycloudflare.com`:

```
https://botanicalex.github.io/webscrapping_transformers/busqueda_pipeline.html?api=https://abc-def-ghi.trycloudflare.com
```

Con ese link:
- El autocompletado del campo *Territorio* consulta `GET {api}/lugares?q=...` (DIVIPOLA).
- El botón **Analizar** llama a `POST {api}/analizar` y muestra el radar real.

---

## Activar GitHub Pages (una sola vez)

Repo → **Settings → Pages** → *Build and deployment* → *Source: Deploy from a branch*
→ elegir la rama a publicar y la carpeta **`/docs`** → *Save*.

La página queda en
`https://botanicalex.github.io/webscrapping_transformers/busqueda_pipeline.html`.
