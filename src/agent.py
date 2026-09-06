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

    self.system_prompt = (
        "You are WeatherGPT, an AI meteorological assistant. Use"
        " `fetch_weather_data` to retrieve real-time data when needed, and"
        " provide actionable agricultural, disaster, and forecast guidance."
    )

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