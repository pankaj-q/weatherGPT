import os
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from src.tools.weather_tool import fetch_weather_data

load_dotenv()


class WeatherAgentRunner:

  def __init__(self, api_key: str = None):
    key = api_key or os.getenv("GROQ_API_KEY")
    # Free, ultra-fast model with tool calling
    self.llm = ChatGroq(
        model="openai/gpt-oss-120b", temperature=0.1, groq_api_key=key
    )
    self.tools = [fetch_weather_data]
    self.tools_map = {t.name: t for t in self.tools}
    self.llm_with_tools = self.llm.bind_tools(self.tools)

    self.system_prompt = """You are WeatherGPT, an AI meteorological intelligence assistant.

Response Formatting Rules:
1. ALWAYS use the `fetch_weather_data` tool when asked about any location or forecast.
2. Structure your output strictly into 3 short, bulleted sections:
   - 📍 **Current Conditions:** (Temperature, Wind, Humidity, and Sky conditions in 1-2 lines)
   - 📅 **3-Day Forecast Highlights:** (High/Low temperatures and precipitation chances)
   - 💡 **Actionable Advisory:** (1-2 clear bullet points for farmers, travelers, or outdoor safety)
3. Keep the entire response under 120 words. Be direct, factual, and crisp."""

  def invoke(self, input_dict: dict) -> dict:
    user_query = input_dict.get("input", "")
    chat_history = input_dict.get("chat_history", [])

    messages = [SystemMessage(content=self.system_prompt)]
    messages.extend(chat_history)
    messages.append(HumanMessage(content=user_query))

    ai_msg = self.llm_with_tools.invoke(messages)
    messages.append(ai_msg)

    if ai_msg.tool_calls:
      for tool_call in ai_msg.tool_calls:
        selected_tool = self.tools_map.get(tool_call["name"])
        if selected_tool:
          tool_output = selected_tool.invoke(tool_call["args"])
          messages.append(
              ToolMessage(
                  tool_call_id=tool_call["id"], content=str(tool_output)
              )
          )

      final_response = self.llm.invoke(messages)
      return {"output": final_response.content}

    return {"output": ai_msg.content}


def build_weather_agent(api_key: str = None):
  return WeatherAgentRunner(api_key)