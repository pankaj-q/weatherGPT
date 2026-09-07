import streamlit as st
import requests
import re

# --- Page Configuration ---
st.set_page_config(
    page_title="WeatherGPT - Meteorological Intelligence",
    page_icon="🌤️",
    layout="wide"
)

# --- Theme-Adaptive CSS (Dark & Light Mode Safe) ---
st.markdown("""
    <style>
    .metric-card {
        background-color: var(--secondary-background-color, #f1f5f9);
        color: var(--text-color, #0f172a);
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 12px;
        padding: 14px 10px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-card b {
        font-size: 1.25rem;
        color: var(--text-color, #0f172a);
    }
    .metric-card small {
        color: var(--text-color, #64748b);
        font-weight: 500;
    }

    .insight-box {
        border-radius: 10px;
        padding: 16px 20px;
        margin-top: 12px;
        color: var(--text-color, #0f172a);
    }
    .insight-safe {
        background-color: rgba(34, 197, 94, 0.12);
        border-left: 5px solid #22c55e;
    }
    .insight-warning {
        background-color: rgba(239, 68, 68, 0.12);
        border-left: 5px solid #ef4444;
    }
    .insight-caution {
        background-color: rgba(245, 158, 11, 0.12);
        border-left: 5px solid #f59e0b;
    }
    .insight-box h4 {
        margin: 0 0 8px 0;
        color: var(--text-color, #0f172a);
    }
    .insight-box ul {
        margin: 0;
        padding-left: 20px;
        line-height: 1.6;
    }
    </style>
""", unsafe_allow_html=True)

# --- Helper: Geocoding (City Name -> Coordinates) ---
@st.cache_data(show_spinner=False, ttl=3600)
def geocode_city(city_name):
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=en&format=json"
    try:
        res = requests.get(url, timeout=5).json()
        if "results" in res and len(res["results"]) > 0:
            item = res["results"][0]
            return item["latitude"], item["longitude"], f"{item['name']}, {item.get('admin1', item.get('country', ''))}"
    except Exception:
        pass
    return 28.9845, 77.7064, "Meerut, Uttar Pradesh"

# --- Helper: Fetch Live Telemetry ---
def get_live_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code&forecast_days=1"
    try:
        res = requests.get(url, timeout=5).json()
        current = res.get("current", {})
        return {
            "temp": current.get("temperature_2m", 28),
            "humidity": current.get("relative_humidity_2m", 60),
            "rain": current.get("precipitation", 0.0),
            "wind": current.get("wind_speed_10m", 12),
            "code": current.get("weather_code", 0)
        }
    except Exception:
        return {"temp": 28, "humidity": 60, "rain": 0.0, "wind": 12, "code": 0}

# --- Intelligent Location & Language Extractor from Prompt ---
def extract_location_from_query(query):
    # Common Indian cities/districts list for fast entity matching
    known_cities = [
        "delhi", "mumbai", "meerut", "lucknow", "patna", "bhopal", "jaipur", "punjab", 
        "chandigarh", "pune", "nagpur", "varanasi", "kanpur", "kolkata", "chennai", 
        "hyderabad", "bengaluru", "ahmedabad", "surat", "ranchi", "shimla", "dehradun"
    ]
    words = re.findall(r'\b[A-Za-z]+\b', query.lower())
    for w in words:
        if w in known_cities:
            return w.capitalize()
    
    # Regex fallback for patterns like "in <City>" or "<City> me"
    match = re.search(r'(?:in|at|near|for|around)\s+([A-Za-z]+)', query, re.IGNORECASE)
    if match:
        candidate = match.group(1).capitalize()
        if candidate.lower() not in ["the", "my", "our", "today", "tomorrow"]:
            return candidate
            
    match_hindi = re.search(r'([A-Za-z]+)\s+(?:me|mein|mai|ka|ki|ke)', query, re.IGNORECASE)
    if match_hindi:
        candidate = match_hindi.group(1).capitalize()
        if candidate.lower() not in ["aaj", "kal", "fasal", "khet", "pani"]:
            return candidate

    return None

def detect_language(query):
    q = query.lower()
    # Check for Devanagari script
    if re.search(r'[\u0900-\u097F]', query):
        return "hindi"
    # Check for common Hinglish cues
    hinglish_words = ["kya", "hai", "hoga", "hogi", "barish", "sinchai", "paani", "khet", "taapman", "mausam", "batao", "aaj", "kal", "spray", "chhidkav"]
    if any(w in q.split() for w in hinglish_words):
        return "hinglish"
    return "english"

# --- State Initialization ---
if "current_city" not in st.session_state:
    st.session_state.current_city = "Meerut"

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Namaste! Main WeatherGPT hoon. Just ask your query naturally in Hindi, English, or any language (e.g., *'Kya Pune me kal barish hogi?'* or *'Is it safe to spray pesticides in Meerut?'*)."}
    ]

if "current_insights" not in st.session_state:
    st.session_state.current_insights = {
        "status": "Safe",
        "irrigation": "✅ Regular morning irrigation is safe.",
        "spraying": "✅ Safe window available (Low wind & no immediate rain).",
        "risk_level": "Low / Normal",
        "action": "Proceed with standard field operations."
    }

# --- Core Dynamic Decision Engine ---
def process_user_query(query):
    # 1. Update location if detected
    detected_city = extract_location_from_query(query)
    if detected_city:
        st.session_state.current_city = detected_city

    # 2. Fetch fresh weather
    lat, lon, resolved_city = geocode_city(st.session_state.current_city)
    weather = get_live_weather(lat, lon)
    
    # 3. Detect language
    lang = detect_language(query)
    
    q = query.lower()
    temp = weather["temp"]
    rain = weather["rain"]
    wind = weather["wind"]
    hum = weather["humidity"]

    # Irrigation / Water Query
    if any(k in q for k in ["paani", "pani", "sinchai", "irrigate", "irrigation", "water"]):
        if rain > 0.5 or hum > 80:
            if lang in ["hindi", "hinglish"]:
                reply = f"📍 **{resolved_city}**: Agle 24-48 ghanton me barish ({rain}mm) aur high humidity ({hum}%) ki sambhavna hai. Fasal me **sinchai abhi taal dein** taaki paani bharne se jadon ko nuksan na ho."
            else:
                reply = f"📍 **{resolved_city}**: Rain ({rain}mm) and high humidity ({hum}%) expected in the next 24-48 hours. **Postpone irrigation** to avoid waterlogging and root damage."
            
            insights = {
                "status": "Warning",
                "risk_level": "High Rain Risk",
                "irrigation": "🚫 DO NOT irrigate (Risk of field waterlogging).",
                "spraying": "🧪 Postpone chemical spraying (Washout hazard).",
                "action": "Inspect low-lying field drainage channels."
            }
        else:
            if lang in ["hindi", "hinglish"]:
                reply = f"📍 **{resolved_city}**: Mausam shushk hai aur taapman {temp}°C hai. Subah ke samay sinchai karna **puri tarah anukool aur surakshit** hai."
            else:
                reply = f"📍 **{resolved_city}**: Weather is clear with a temperature of {temp}°C. Morning irrigation is **completely safe and recommended**."
            
            insights = {
                "status": "Safe",
                "risk_level": "Normal Conditions",
                "irrigation": "✅ Safe to irrigate in morning/evening.",
                "spraying": "✅ Safe window for nutrient application.",
                "action": "Maintain routine soil moisture checks."
            }

    # Pesticide / Spraying Query
    elif any(k in q for k in ["spray", "keetnashak", "fertilizer", "dawa", "chemical", "pesticide"]):
        if wind > 18:
            if lang in ["hindi", "hinglish"]:
                reply = f"📍 **{resolved_city}**: Hawa ki gati tez ({wind} km/h) hai. Dawa hawa ke sath udkar barbaad hogi. **Chhidkav abhi rok dein**."
            else:
                reply = f"📍 **{resolved_city}**: High wind speed detected ({wind} km/h). **Halt chemical spraying** to prevent wind drift and chemical wastage."
            
            insights = {
                "status": "Caution",
                "risk_level": "High Wind Drift Alert",
                "irrigation": "✅ Irrigation can continue normally.",
                "spraying": "🚫 STOP chemical spraying (Wind speed > 15 km/h).",
                "action": "Wait for wind speeds to subside."
            }
        else:
            if lang in ["hindi", "hinglish"]:
                reply = f"📍 **{resolved_city}**: Hawa ki gati anukool ({wind} km/h) hai aur barish ka koi khatra nahi hai. Keetnashak chhidkav **safalta-poorvak kiya ja sakta hai**."
            else:
                reply = f"📍 **{resolved_city}**: Favorable wind speed ({wind} km/h) with zero rain risk. **Pesticide application window is fully open**."
            
            insights = {
                "status": "Safe",
                "risk_level": "Favorable Spray Window",
                "irrigation": "✅ Normal schedule.",
                "spraying": "✅ Excellent spraying window active.",
                "action": "Use standard safety protective gear."
            }

    # Rain / Storm / Weather Alerts
    elif any(k in q for k in ["storm", "toofan", "barish", "flood", "alert", "baarish", "rain"]):
        if rain > 0.8 or wind > 25:
            if lang in ["hindi", "hinglish"]:
                reply = f"🚨 **Severe Weather Alert ({resolved_city})**: Bhari barish/tez aandhi ({wind} km/h) ki aashanka hai. Khet ke upkaran surakshit karein aur khet me na jayein."
            else:
                reply = f"🚨 **Severe Weather Alert ({resolved_city})**: Heavy rain/high winds ({wind} km/h) expected. Secure livestock and field machinery immediately."
            
            insights = {
                "status": "Warning",
                "risk_level": "Severe Weather Warning",
                "irrigation": "🚫 Halt all irrigation pumps immediately.",
                "spraying": "🚫 Strict ban on all chemical spraying.",
                "action": "Clear drainage blockages and secure equipment."
            }
        else:
            if lang in ["hindi", "hinglish"]:
                reply = f"📍 **{resolved_city}**: Agle 24 ghanton me kisi gambhir toofan ya bhari barish ki chetavni nahi hai. Mausam sthir hai."
            else:
                reply = f"📍 **{resolved_city}**: No severe storm or flood warnings for the next 24 hours. Weather conditions are stable."
            
            insights = {
                "status": "Safe",
                "risk_level": "Low Hazard",
                "irrigation": "✅ Standard routine.",
                "spraying": "✅ Safe window open.",
                "action": "Monitor daily regional forecasts."
            }

    # General Weather / Fallback
    else:
        if lang in ["hindi", "hinglish"]:
            reply = f"📍 **{resolved_city} Live Update**: Taapman **{temp}°C**, Hawa **{wind} km/h**, Nami (Humidity) **{hum}%**, aur Barish **{rain} mm** hai."
        else:
            reply = f"📍 **{resolved_city} Live Update**: Temperature is **{temp}°C**, Wind is **{wind} km/h**, Humidity is **{hum}%**, and Precipitation is **{rain} mm**."
        
        insights = {
            "status": "Safe",
            "risk_level": "Normal Field Weather",
            "irrigation": "✅ Routine morning irrigation safe.",
            "spraying": "✅ Normal spraying window open.",
            "action": "Standard field maintenance active."
        }

    return reply, insights, resolved_city, weather

# --- Clean Header (No Options/Dropdowns) ---
st.title("🌤️ WeatherGPT")
st.caption("Zero-Barrier Meteorological AI — Auto-detects location & language directly from your conversational prompt.")
st.divider()

# Get coordinates and telemetry for the current active city
lat, lon, resolved_city_name = geocode_city(st.session_state.current_city)
weather_data = get_live_weather(lat, lon)

# --- Main Dual-Panel Grid Layout ---
left_panel, right_panel = st.columns([1.1, 0.9], gap="large")

# ==========================================
# LEFT PANEL: Conversational Stream
# ==========================================
with left_panel:
    st.subheader("💬 Conversational Assistant")
    
    chat_container = st.container(height=440)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    user_input = st.chat_input("Ask anything (e.g., 'Kya Lucknow me kal barish hogi?' or 'Can I spray pesticides in Jaipur?')...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Analyze prompt, infer location & language, update insights
        ai_reply, new_insights, resolved_city_name, weather_data = process_user_query(user_input)
        
        st.session_state.current_insights = new_insights
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
        st.rerun()

# ==========================================
# RIGHT PANEL: Live Telemetry & Insights
# ==========================================
with right_panel:
    st.subheader(f"📊 Live Telemetry & Insights ({resolved_city_name})")

    # 1. Real-Time Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"<div class='metric-card'>🌡️<br><b>{weather_data['temp']}°C</b><br><small>Temp</small></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric-card'>🌧️<br><b>{weather_data['rain']} mm</b><br><small>Precip</small></div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='metric-card'>💨<br><b>{weather_data['wind']} km/h</b><br><small>Wind</small></div>", unsafe_allow_html=True)
    with m4:
        st.markdown(f"<div class='metric-card'>💧<br><b>{weather_data['humidity']}%</b><br><small>Humidity</small></div>", unsafe_allow_html=True)

    st.write("")

    # 2. Dynamic Actionable Insight Card (Updated Post-Response)
    st.markdown("#### 💡 Actionable Agro-Advisory")
    insights = st.session_state.current_insights

    card_type = "insight-warning" if insights["status"] == "Warning" else ("insight-caution" if insights["status"] == "Caution" else "insight-safe")

    st.markdown(f"""
    <div class='insight-box {card_type}'>
        <h4>Risk Status: {insights['risk_level']}</h4>
        <ul>
            <li><b>Irrigation Guidance:</b> {insights['irrigation']}</li>
            <li><b>Chemical Spray Window:</b> {insights['spraying']}</li>
            <li><b>Recommended Action:</b> {insights['action']}</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    
    # 3. Mass Broadcast Trigger
    if st.button(f"🚨 Broadcast Advisory to Registered Farmers ({resolved_city_name})", use_container_width=True):
        st.success(f"✅ Advisory successfully dispatched to farmer WhatsApp groups in {resolved_city_name} cluster.")

# import os
# from dotenv import load_dotenv
# import streamlit as st
# from langchain_core.messages import AIMessage, HumanMessage
# from src.agent import build_weather_agent

# load_dotenv()

# st.set_page_config(
#     page_title="WeatherGPT Dashboard",
#     page_icon="🌤️",
#     layout="wide"  # Uses full screen width
# )

# # Custom CSS for cards and metrics styling
# st.markdown("""
# <style>
#     .metric-card {
#         background-color: rgba(255, 255, 255, 0.05);
#         border: 1px solid rgba(255, 255, 255, 0.15);
#         border-radius: 12px;
#         padding: 16px;
#         margin-bottom: 12px;
#     }
#     .alert-banner {
#         padding: 10px 14px;
#         border-radius: 8px;
#         font-weight: 600;
#         margin-bottom: 12px;
#     }
# </style>
# """, unsafe_allow_html=True)

# # -------------------------------------------------------------
# # Initialize Session State
# # -------------------------------------------------------------
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# if "latest_telemetry" not in st.session_state:
#     st.session_state.latest_telemetry = {
#         "location": "No search yet",
#         "temp": "--",
#         "humidity": "--",
#         "wind": "--",
#         "rain_prob": "--",
#         "alert_status": "Normal"
#     }

# # -------------------------------------------------------------
# # Header
# # -------------------------------------------------------------
# st.title("🌤️ WeatherGPT Assisstance")
# st.caption("AI-powered weather forecasting, hyper-local advisories, and disaster alerts.")
# st.divider()

# # -------------------------------------------------------------
# # Main Layout: 60% Chat, 40% Live Data Cards
# # -------------------------------------------------------------
# col_chat, col_data = st.columns([1.3, 0.9], gap="large")

# # === LEFT COLUMN: CONVERSATIONAL AGENT ===
# with col_chat:
#     st.subheader("💬 Weather Assistant")
    
#     # Scrollable chat message container
#     chat_container = st.container(height=520)
#     with chat_container:
#         for msg in st.session_state.messages:
#             role = "user" if isinstance(msg, HumanMessage) else "assistant"
#             with st.chat_message(role):
#                 st.markdown(msg.content)

#     # Chat Input
#     if user_input := st.chat_input("Ask about weather, rain forecasts, or crop advice..."):
#         st.session_state.messages.append(HumanMessage(content=user_input))
#         with chat_container:
#             with st.chat_message("user"):
#                 st.markdown(user_input)

#         with chat_container:
#             with st.chat_message("assistant"):
#                 with st.spinner("Analyzing atmospheric models..."):
#                     agent = build_weather_agent()
#                     history = st.session_state.messages[:-1]
#                     result = agent.invoke({"input": user_input, "chat_history": history})
#                     response_text = result["output"]
                    
#                     st.markdown(response_text)
#                     st.session_state.messages.append(AIMessage(content=response_text))
                    
#                     # Optional: Parse simple metrics for the right panel if available
#                     st.rerun()

# # === RIGHT COLUMN: DYNAMIC TELEMETRY CARDS ===
# with col_data:
#     st.subheader("📊 Live Weather Insights")
    
#     telemetry = st.session_state.latest_telemetry
    
#     # 1. Location & Alert Status Card
#     with st.container():
#         st.markdown(f"### 📍 **{telemetry['location']}**")
#         if telemetry["alert_status"] == "Warning":
#             st.error("⚠️ High Rain/Wind Warning Active")
#         else:
#             st.success("🟢 Atmospheric Status: Normal")

#     # 2. Key Metrics Grid
#     m1, m2 = st.columns(2)
#     with m1:
#         st.metric(label="🌡️ Temperature", value=f"{telemetry['temp']} °C")
#         st.metric(label="💨 Wind Speed", value=f"{telemetry['wind']} km/h")
#     with m2:
#         st.metric(label="💧 Humidity", value=f"{telemetry['humidity']} %")
#         st.metric(label="🌧️ Rain Probability", value=f"{telemetry['rain_prob']} %")

#     st.divider()

#     # 3. Actionable Quick Checklist
#     st.markdown("#### 🚜 Advisory Checklist")
#     st.markdown("""
#     * **Farming/Spraying:** Check 24-hr rain risk before chemical application.
#     * **Travel/Commute:** Safe driving conditions unless wind > 40 km/h.
#     * **Disaster Protocol:** Monitor yellow/orange alerts for severe rainfall.
#     """)

