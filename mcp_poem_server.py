import os
import time, uuid, sqlite3
from typing import Annotated
from pydantic import Field
from mcp.server.fastmcp import FastMCP, Context
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# Read environment variables
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "dev-token")
MY_NUMBER = os.getenv("MY_NUMBER", None)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)

try:
    import openai
    if OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
except ImportError:
    openai = None

# Database for tracking usage
DB_PATH = "usage.db"
_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.execute("""
CREATE TABLE IF NOT EXISTS calls (
  id TEXT PRIMARY KEY,
  ts REAL,
  theme TEXT,
  style TEXT,
  length TEXT,
  tone TEXT
)
""")
_conn.commit()

def record_call(theme, style, length, tone):
    _conn.execute("INSERT INTO calls VALUES (?,?,?,?,?,?)",
                  (str(uuid.uuid4()), time.time(), theme, style, length, tone))
    _conn.commit()

# MCP server
mcp = FastMCP(name="PoemGen")

@mcp.tool()
def validate(token: str) -> str:
    """Required by Puch for authentication"""
    if token != AUTH_TOKEN:
        raise Exception("Invalid token")
    if not MY_NUMBER:
        raise Exception("MY_NUMBER not set in environment")
    return MY_NUMBER

@mcp.tool(description="Generate a poem based on theme, style, length, and tone")
async def generate_poem(
    theme: Annotated[str, Field(description="Poem topic")],
    style: Annotated[str, Field(description="haiku|sonnet|free_verse")] = "free_verse",
    length: Annotated[str, Field(description="short|medium|long")] = "short",
    tone: Annotated[str, Field(description="romantic|funny|dark|neutral")] = "romantic",
    ctx: Context = None
) -> str:
    record_call(theme, style, length, tone)

    # If OpenAI API key present
    if OPENAI_API_KEY and openai:
        try:
            prompt = (
                f"Write a {length} {style} poem about '{theme}' "
                f"in a {tone} tone."
            )
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.8
            )
            return resp["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    # Fallback simple poem
    return fallback_poem(theme, style, length, tone)

def fallback_poem(theme, style, length, tone):
    if style == "haiku":
        return f"{theme} at sunrise\nsoft winds drift across the sky\nhope wakes quietly"
    lines = [
        f"In the {tone} light of {theme}, I stand,",
        f"Whispers and dreams held in my hand.",
        f"The {theme} sings a story untold,",
        "Woven in stardust, silver and gold."
    ]
    if tone == "funny":
        lines[-1] += " (and maybe some cheese)."
    return "\n".join(lines[:3] if length == "short" else lines)



app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def read_root():
    return "<h1>PoemGen Server is running ✅</h1><p>Use this endpoint via MCP or API requests.</p>"

# Mount the MCP server inside FastAPI
mcp.fastapi_mount(app)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    import uvicorn
    print(f"Starting PoemGen MCP server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)

