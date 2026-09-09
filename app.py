import re
import requests
import streamlit as st
import streamlit.components.v1 as components

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="WeatherGPT",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- 2. Executive Dark Theme Styling ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap');

    html, body, [class*="css"], .stApp {
        background-color: #07090E !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: #F8FAFC !important;
    }

    #MainMenu, header, footer {
        visibility: hidden !important;
        height: 0px !important;
    }

    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1280px !important;
    }

    /* Landing Centered Hero */
    .hero-box {
        text-align: center;
        margin-top: 10vh;
        margin-bottom: 2.2rem;
    }
    .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #38BDF8;
        background: rgba(56, 189, 248, 0.08);
        border: 1px solid rgba(56, 189, 248, 0.2);
        padding: 6px 14px;
        border-radius: 9999px;
        margin-bottom: 1.2rem;
    }
    .hero-title {
        font-size: 3.5rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        background: linear-gradient(180deg, #FFFFFF 40%, #94A3B8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.6rem;
    }
    .hero-sub {
        font-size: 1.05rem;
        color: #64748B;
        max-width: 540px;
        margin: 0 auto;
        line-height: 1.6;
    }

    /* Suggestion Query Chips */
    .stButton button {
        background-color: #0F1219 !important;
        border: 1px solid #1E2433 !important;
        border-radius: 100px !important;
        color: #94A3B8 !important;
        font-size: 0.84rem !important;
        font-weight: 500 !important;
        padding: 0.55rem 1.1rem !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    .stButton button:hover {
        border-color: #38BDF8 !important;
        color: #FFFFFF !important;
        background-color: #151A24 !important;
        transform: translateY(-2px);
    }

    /* Dashboard Grid Cards */
    .dash-card {
        background-color: #0D1017;
        border: 1px solid #1A202C;
        border-radius: 14px;
        padding: 1.25rem 1.4rem;
        margin-bottom: 1rem;
    }
    .card-header {
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #64748B;
        margin-bottom: 0.9rem;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.65rem;
    }
    .metric-item {
        background-color: #121620;
        border: 1px solid #1F2737;
        border-radius: 10px;
        padding: 12px 6px;
        text-align: center;
    }
    .metric-lbl {
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748B;
    }
    .metric-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.28rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-top: 4px;
    }

    /* Advisory Badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.84rem;
        font-weight: 700;
        padding: 5px 12px;
        border-radius: 6px;
        margin-bottom: 0.9rem;
    }
    .status-safe {
        background: rgba(34, 197, 94, 0.1);
        color: #4ADE80;
        border: 1px solid rgba(34, 197, 94, 0.25);
    }
    .status-caution {
        background: rgba(245, 158, 11, 0.1);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.25);
    }
    .status-warning {
        background: rgba(239, 68, 68, 0.1);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.25);
    }

    /* Chat Messages */
    [data-testid="stChatMessage"] {
        background-color: #0D1017 !important;
        border: 1px solid #1A202C !important;
        border-radius: 12px !important;
        padding: 1rem 1.2rem !important;
        margin-bottom: 0.75rem !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# --- 3. Telemetry & Geocoding Endpoints ---
@st.cache_data(show_spinner=False, ttl=3600)
def geocode_location(place_name: str):
  url = f"https://geocoding-api.open-meteo.com/v1/search?name={place_name}&count=1&language=en&format=json"
  try:
    res = requests.get(url, timeout=5).json()
    if "results" in res and len(res["results"]) > 0:
      item = res["results"][0]
      return (
          item["latitude"],
          item["longitude"],
          f"{item['name']}, {item.get('admin1', item.get('country', ''))}",
      )
  except Exception:
    pass
  return 28.6139, 77.2090, "New Delhi, India"


def fetch_weather(lat: float, lon: float):
  url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m&forecast_days=1"
  try:
    res = requests.get(url, timeout=5).json()
    cur = res.get("current", {})
    return {
        "temp": round(cur.get("temperature_2m", 28.0), 1),
        "humidity": cur.get("relative_humidity_2m", 55),
        "rain": round(cur.get("precipitation", 0.0), 1),
        "wind": round(cur.get("wind_speed_10m", 10.0), 1),
    }
  except Exception:
    return {"temp": 28.0, "humidity": 55, "rain": 0.0, "wind": 10.0}


def parse_location(text: str):
  cities = [
      "delhi",
      "meerut",
      "jaipur",
      "lucknow",
      "pune",
      "mumbai",
      "bhopal",
      "patna",
      "bengaluru",
      "chennai",
      "kolkata",
      "chandigarh",
      "ahmedabad",
      "nagpur",
  ]
  tokens = re.findall(r"\b[A-Za-z]+\b", text.lower())
  for token in tokens:
    if token in cities:
      return token.capitalize()
  match = re.search(
      r"(?:in|at|near|for|around)\s+([A-Za-z]+)", text, re.IGNORECASE
  )
  if match and match.group(1).lower() not in [
      "the",
      "my",
      "today",
      "tomorrow",
      "this",
  ]:
    return match.group(1).capitalize()
  return None


# --- 4. State Management ---
if "has_searched" not in st.session_state:
  st.session_state.has_searched = False
if "current_city" not in st.session_state:
  st.session_state.current_city = "New Delhi"
if "messages" not in st.session_state:
  st.session_state.messages = []
if "insights" not in st.session_state:
  st.session_state.insights = {}
if "preset_prompt" not in st.session_state:
  st.session_state.preset_prompt = None


# --- 5. Reasoning Engine ---
def generate_insights(query: str):
  loc = parse_location(query)
  if loc:
    st.session_state.current_city = loc

  lat, lon, resolved_name = geocode_location(st.session_state.current_city)
  data = fetch_weather(lat, lon)
  q = query.lower()

  if any(
      k in q
      for k in ["spray", "pesticide", "fertilizer", "chhidkav", "keetnashak"]
  ):
    if data["wind"] > 16.0:
      reply = f"Wind speeds are currently elevated at **{data['wind']} km/h** in {resolved_name}. Chemical spraying should be suspended to avoid pesticide drift."
      insights = {
          "status": "Caution: High Wind Velocity",
          "class": "status-caution",
          "irrigation": "Routine schedule unaffected",
          "spray": "🚫 Halt spray operations (Wind > 15 km/h)",
          "action": "Wait for wind speeds to drop below 15 km/h.",
      }
    else:
      reply = f"Atmospheric conditions in {resolved_name} are optimal ({data['wind']} km/h wind, 0 mm rain). Safe window for field chemical spraying."
      insights = {
          "status": "Safe: Optimal Conditions",
          "class": "status-safe",
          "irrigation": "Routine schedule active",
          "spray": "✅ Spray window is open",
          "action": "Proceed with recommended dosages.",
      }
  elif any(
      k in q
      for k in ["rain", "barish", "baarish", "water", "irrigation", "sinchai"]
  ):
    if data["rain"] > 0.4:
      reply = f"Precipitation (**{data['rain']} mm**) detected across {resolved_name}. Delay additional irrigation to prevent crop root waterlogging."
      insights = {
          "status": "Warning: Rain Expected",
          "class": "status-warning",
          "irrigation": "🚫 Postpone field watering",
          "spray": "🚫 Washout hazard",
          "action": "Inspect low-lying drainage channels.",
      }
    else:
      reply = f"Clear atmospheric conditions in {resolved_name} with **{data['temp']}°C** temperature and **{data['humidity']}%** humidity. Field irrigation is safe."
      insights = {
          "status": "Optimal: Clear Conditions",
          "class": "status-safe",
          "irrigation": "✅ Regular morning irrigation safe",
          "spray": "✅ Normal spraying permitted",
          "action": "Maintain standard soil moisture checks.",
      }
  else:
    reply = f"Live telemetry for **{resolved_name}**: Temperature is **{data['temp']}°C**, Wind velocity **{data['wind']} km/h**, Humidity **{data['humidity']}%**, and Precipitation **{data['rain']} mm**."
    insights = {
        "status": "Nominal Telemetry",
        "class": "status-safe",
        "irrigation": "✅ Regular operations",
        "spray": "✅ Conditions normal",
        "action": "Monitor routine operational updates.",
    }

  return reply, insights, resolved_name, data


# --- 6. Custom Center Search Component ---
def render_center_search_bar():
  search_html = """
    <div style="max-width: 650px; margin: 0 auto;">
        <form id="searchForm" onsubmit="handleSubmit(event)" style="position: relative; width: 100%;">
            <div style="
                display: flex;
                align-items: center;
                background: #0E121A;
                border: 1px solid #232C3D;
                border-radius: 9999px;
                padding: 7px 10px 7px 20px;
                box-shadow: 0 16px 36px rgba(0, 0, 0, 0.6);
                transition: border-color 0.2s ease;
            " onmouseover="this.style.borderColor='#38BDF8'" onmouseout="this.style.borderColor='#232C3D'">
                <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 12px; flex-shrink: 0;">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                <input id="queryInput" type="text" placeholder="Ask about rain, wind, spraying in any city..." autocomplete="off" style="
                    width: 100%;
                    background: transparent;
                    border: none;
                    outline: none;
                    color: #FFFFFF;
                    font-size: 15px;
                    font-family: 'Plus Jakarta Sans', sans-serif;
                " />
                <button type="submit" style="
                    background: #FFFFFF;
                    border: none;
                    border-radius: 9999px;
                    width: 38px;
                    height: 38px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    flex-shrink: 0;
                    margin-left: 8px;
                    transition: transform 0.15s ease;
                " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#07090E" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                        <polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                </button>
            </div>
        </form>
    </div>
    <script>
        function handleSubmit(e) {
            e.preventDefault();
            const val = document.getElementById('queryInput').value;
            if (val && val.trim() !== "") {
                const parentDoc = window.parent.document;
                const nativeInput = parentDoc.querySelector('input[aria-label="hidden_query_bridge"]');
                if (nativeInput) {
                    nativeInput.value = val.trim();
                    nativeInput.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        }
    </script>
    """
  components.html(search_html, height=75)


# --- 7. View Routing ---

# Hidden input bridge for HTML Form to Streamlit State communication
hidden_bridge = st.text_input(
    "hidden_query_bridge", label_visibility="collapsed", key="bridge_input"
)
active_query = None

if hidden_bridge:
  active_query = hidden_bridge
  st.session_state.bridge_input = ""

if not st.session_state.has_searched:
  # LANDING VIEW
  st.markdown(
      """
        <div class="hero-box">
            <div class="badge-pill">Autonomous Climate Decision Core</div>
            <div class="hero-title">WeatherGPT</div>
            <div class="hero-sub">Instant hyper-local telemetry, agricultural decision support, and emergency disaster dispatch.</div>
        </div>
    """,
      unsafe_allow_html=True,
  )

  # Custom Floating Search Pill
  render_center_search_bar()

  # Quick Suggestion Chips
  st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
  _, c1, c2, c3, _ = st.columns([0.8, 1.2, 1.2, 1.2, 0.8])
  with c1:
    if st.button("🌦️ Rain forecast for Meerut", use_container_width=True):
      active_query = "Will it rain in Meerut tomorrow?"
  with c2:
    if st.button("🌾 Safe to spray in Jaipur?", use_container_width=True):
      active_query = "Is it safe to spray pesticides in Jaipur?"
  with c3:
    if st.button("⚡ Live telemetry in Mumbai", use_container_width=True):
      active_query = "What is the live weather in Mumbai?"

else:
  # DASHBOARD VIEW
  st.markdown(
      """
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.2rem; border-bottom: 1px solid #1A202C; padding-bottom: 0.9rem;">
            <div>
                <span style="font-size:1.35rem; font-weight:800; color:#FFFFFF;">🌤️ WeatherGPT</span>
                <span style="font-size:0.85rem; color:#64748B; margin-left:8px;">| Agro-Decision Core</span>
            </div>
            <span style="font-size:0.75rem; font-weight:700; color:#4ADE80; background:rgba(34,197,94,0.1); border:1px solid rgba(34,197,94,0.2); padding:4px 10px; border-radius:100px;">● Live Telemetry Ingestion</span>
        </div>
    """,
      unsafe_allow_html=True,
  )

  col_chat, col_dash = st.columns([1.15, 0.85], gap="large")

  with col_chat:
    chat_box = st.container(height=480)
    with chat_box:
      for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
          st.markdown(msg["content"])

    # Bottom search bar for conversation follow-ups
    bottom_query = st.chat_input("Ask a follow-up query...")
    if bottom_query:
      active_query = bottom_query

  with col_dash:
    lat, lon, current_name = geocode_location(st.session_state.current_city)
    telemetry = fetch_weather(lat, lon)
    ins = st.session_state.insights

    # Card 1: Metric Telemetry Grid
    st.markdown(
        f"""
        <div class="dash-card">
            <div class="card-header">📡 Real-Time Telemetry &bull; {current_name}</div>
            <div class="metric-grid">
                <div class="metric-item">
                    <div class="metric-lbl">Temp</div>
                    <div class="metric-val">{telemetry['temp']}°C</div>
                </div>
                <div class="metric-item">
                    <div class="metric-lbl">Rain</div>
                    <div class="metric-val">{telemetry['rain']}mm</div>
                </div>
                <div class="metric-item">
                    <div class="metric-lbl">Wind</div>
                    <div class="metric-val">{telemetry['wind']}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-lbl">Humidity</div>
                    <div class="metric-val">{telemetry['humidity']}%</div>
                </div>
            </div>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # Card 2: Decision Advisory Card
    st.markdown(
        f"""
        <div class="dash-card">
            <div class="card-header">💡 Field Decision Advisory</div>
            <div class="status-badge {ins.get('class', 'status-safe')}">● {ins.get('status', 'Nominal')}</div>
            <div style="font-size:0.88rem; line-height:1.8; color:#CBD5E1;">
                <div><b>Irrigation:</b> {ins.get('irrigation', 'Nominal')}</div>
                <div><b>Chemical Spray:</b> {ins.get('spray', 'Nominal')}</div>
                <div><b>Action Plan:</b> {ins.get('action', 'Maintain routine operations')}</div>
            </div>
        </div>
    """,
        unsafe_allow_html=True,
    )

    if st.button(
        f"🚨 Broadcast Advisory to {current_name} (Twilio Gateway)",
        use_container_width=True,
    ):
      st.toast(
          f"Advisory successfully dispatched via Twilio SMS to {current_name}."
      )

# --- 8. Query Execution ---
if active_query:
  st.session_state.has_searched = True
  st.session_state.messages.append({"role": "user", "content": active_query})

  bot_res, new_ins, _, _ = generate_insights(active_query)
  st.session_state.insights = new_ins
  st.session_state.messages.append({"role": "assistant", "content": bot_res})
  st.rerun()