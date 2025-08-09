import os
import time
import uuid
import sqlite3
import random
from typing import Annotated
from pydantic import Field
from fastmcp import FastMCP, Context

# Environment variables
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "dev-token")
MY_NUMBER = os.getenv("MY_NUMBER", None)

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

WORD_BANKS = {
    "romantic": ["love", "heart", "kiss", "dream", "embrace", "rose", "desire", "whisper"],
    "funny": ["cheese", "joke", "clown", "banana", "giggle", "pickle", "snort", "silly"],
    "dark": ["shadow", "night", "ghost", "fear", "whisper", "void", "bleed", "grave"],
    "neutral": ["sky", "tree", "wind", "river", "stone", "cloud", "path", "light"]
}

TEMPLATES = {
    "haiku": [
        "{theme} at dawn breaks,",
        "soft {tone_word} drifts through the air,",
        "peaceful silence hums."
    ],
    "sonnet": [
        "Oh {theme}, in {tone_word} hues you shine,",
        "A melody that stirs this heart of mine.",
        "Through {tone_word} days and quiet nights,",
        "Your presence paints the soul with lights.",
        "With every breath, a gentle song,",
        "Where {tone_word} feelings do belong.",
        "In verses penned by whispered dreams,",
        "You’re more than ever what life means.",
        "Though {theme} fades, your spirit stays,",
        "In {tone_word} hearts and tender ways.",
        "Forevermore, in silent streams,",
        "You dance within my nightly themes.",
        "O {theme}, beloved and true,",
        "This sonnet’s all I give to you."
    ],
    "free_verse": [
        "In the {tone_word} light of {theme}, I stand,",
        "Whispers and dreams held in my hand.",
        "The {theme} sings a story untold,",
        "Woven in stardust, silver and gold.",
        "Echoes of {tone_word} memories flow,",
        "Paths where only the brave dare to go.",
        "Beneath the {tone_word} sky so wide,",
        "Feelings and moments collide."
    ]
}

def fallback_poem(theme, style, length, tone):
    theme = theme.capitalize()
    tone = tone.lower()
    style = style.lower()
    length = length.lower()

    tone_word = random.choice(WORD_BANKS.get(tone, WORD_BANKS["neutral"]))
    lines = TEMPLATES.get(style, TEMPLATES["free_verse"])
    poem_lines = [line.format(theme=theme, tone_word=tone_word) for line in lines]

    if length == "short":
        poem_lines = poem_lines[:3]
    elif length == "medium":
        poem_lines = poem_lines[:6]
    else:
        poem_lines = poem_lines

    if length != "long":
        first_line = poem_lines[0]
        rest = poem_lines[1:]
        random.shuffle(rest)
        poem_lines = [first_line] + rest

    return "\n".join(poem_lines)

mcp = FastMCP(name="PoemGen")

@mcp.tool()
def validate(token: str) -> str:
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
    return fallback_poem(theme, style, length, tone)

app = mcp.from_fastapi()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))