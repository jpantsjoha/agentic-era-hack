# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# mypy: disable-error-code="union-attr"
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from google.cloud import aiplatform
from google.cloud.aiplatform import generative_models
from google.cloud.aiplatform.rag import rag


LOCATION = "us-central1"
LLM_LOCATION = "us-east5"
LLM = "claude-3-7-sonnet@20250219"


# Note: We're not explicitly initializing Vertex AI here to be consistent with app/agent.py
# If you encounter initialization errors, you may need to add:
# aiplatform.init(project='your-project-id', location=LLM_LOCATION)

# 1. Define tools

# Get RAG corpus
rag_corpus = rag.RagCorpus(f"projects/qwiklabs-gcp-00-ec45a6172538/locations/${LOCATION}/ragCorpora/4611686018427387904")

# Create RAG retrieval tool
rag_retrieval_tool = generative_models.Tool.from_retrieval(
    retrieval=rag.Retrieval(
        source=rag.VertexRagStore(
            rag_resources=[rag.RagResource(rag_corpus=rag_corpus.name)],
            rag_retrieval_config=rag.RagRetrievalConfig(
                top_k=10,  # Optional
                filter=rag.Filter(
                    vector_distance_threshold=0.5,  # Optional
                ),
            ),
        ),
    )
)

# Convert Vertex AI RAG tool to LangChain tool for the LangGraph workflow
@tool
def rag_search(query: str) -> str:
    """Search through the RAG corpus for relevant information."""
    # Use the Vertex AI RAG tool to retrieve information
    model = generative_models.GenerativeModel(
        LLM,  # Using the LLM constant defined above
        generation_config=generative_models.GenerationConfig(
            temperature=0,
            max_output_tokens=1024,
        )
    )
    response = model.generate_content(
        [generative_models.Content(
            parts=[generative_models.Part(text=query)]
        )],
        tools=[rag_retrieval_tool]
    )
    return response.text

tools = [rag_search]

# 2. Set up the language model with tools
# This is a custom function that mimics the behavior of ChatVertexAI.bind_tools()
def get_claude_with_tools(tools):
    """Creates a callable that mimics the behavior of a LangChain LLM with bound tools."""
    
    def invoke_claude(messages, config=None):
        """Invokes Claude with the given messages and tools."""
        # Convert LangChain messages to Vertex AI format
        vertex_messages = []
        
        for msg in messages:
            if isinstance(msg, dict):
                # Handle dict-style messages
                if msg["type"] == "system":
                    vertex_messages.append(generative_models.Content(
                        role="user", 
                        parts=[generative_models.Part(text=msg["content"])]
                    ))
                elif msg["type"] == "human":
                    vertex_messages.append(generative_models.Content(
                        role="user", 
                        parts=[generative_models.Part(text=msg["content"])]
                    ))
                elif msg["type"] == "ai":
                    vertex_messages.append(generative_models.Content(
                        role="model", 
                        parts=[generative_models.Part(text=msg["content"])]
                    ))
            else:
                # Handle LangChain message objects
                if msg.type == "human":
                    vertex_messages.append(generative_models.Content(
                        role="user", 
                        parts=[generative_models.Part(text=msg.content)]
                    ))
                elif msg.type == "ai":
                    vertex_messages.append(generative_models.Content(
                        role="model", 
                        parts=[generative_models.Part(text=msg.content)]
                    ))
        
        # Create the model
        model = generative_models.GenerativeModel(
            LLM,
            generation_config=generative_models.GenerationConfig(
                temperature=0,
                max_output_tokens=1024,
            )
        )
        
        # Call the Claude model through Vertex AI
        response = model.generate_content(
            vertex_messages,
            tools=[rag_retrieval_tool],
            stream=config is not None and config.get("callbacks") is not None
        )
        
        # Convert the response back to LangChain format
        if config is not None and config.get("callbacks") is not None and hasattr(response, 'candidates'):
            # For streaming responses
            response_text = response.candidates[0].content.parts[0].text
        else:
            # For non-streaming responses
            response_text = response.text
        
        # Create an AIMessage
        ai_message = AIMessage(content=response_text)
        
        # Check if there are tool calls in the response
        if hasattr(response, 'candidates') and response.candidates and hasattr(response.candidates[0].content.parts[0], 'function_calls'):
            function_calls = response.candidates[0].content.parts[0].function_calls
            if function_calls:
                tool_calls = []
                for function_call in function_calls:
                    tool_calls.append({
                        "name": function_call.name,
                        "arguments": function_call.args
                    })
                ai_message.tool_calls = tool_calls
        
        return ai_message
    
    return invoke_claude

# Create a callable that mimics a LangChain LLM with bound tools
llm = get_claude_with_tools(tools)


# 3. Define workflow components
def should_continue(state: MessagesState) -> str:
    """Determines whether to use tools or end the conversation."""
    last_message = state["messages"][-1]
    return "tools" if last_message.tool_calls else END


def call_model(state: MessagesState, config: RunnableConfig) -> dict[str, BaseMessage]:
    """Calls the language model and returns the response."""
    system_message = "You are a helpful AI assistant with access to RAG capabilities. Use the rag_search tool when you need to retrieve specific information from the knowledge base."
    messages_with_system = [{"type": "system", "content": system_message}] + state[
        "messages"
    ]
    # Forward the RunnableConfig object to ensure the agent is capable of streaming the response.
    response = llm(messages_with_system, config)
    return {"messages": response}


# 4. Create the workflow graph
workflow = StateGraph(MessagesState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools))
workflow.set_entry_point("agent")

# 5. Define graph edges
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

# 6. Compile the workflow
agent = workflow.compile()
