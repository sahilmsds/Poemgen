import os
import time
import uuid
import sqlite3
from typing import Annotated
from pydantic import Field
from fastmcp import FastMCP, Context
from fastapi import FastAPI

# Environment variables
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "dev-token")
MY_NUMBER = os.getenv("MY_NUMBER", None)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)

# Optional OpenAI import
try:
    import openai
    if OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
except ImportError:
    openai = None

# SQLite database for usage tracking
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
    _conn.execute(
        "INSERT INTO calls VALUES (?,?,?,?,?,?)",
        (str(uuid.uuid4()), time.time(), theme, style, length, tone)
    )
    _conn.commit()

# Create MCP instance
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

    if OPENAI_API_KEY and openai:
        try:
            prompt = f"Write a {length} {style} poem about '{theme}' in a {tone} tone."
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.8
            )
            return resp["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

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

# FastAPI app from MCP
app = mcp.as_fastapi()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))