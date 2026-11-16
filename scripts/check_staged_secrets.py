"""Fail without disclosing values if any private local key appears in staged source."""
from pathlib import Path
import subprocess
from dotenv import dotenv_values

values = dotenv_values(Path(__file__).resolve().parents[1]/".env")
files = subprocess.check_output(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]).decode().split("\0")
for file in filter(None, files):
    data = subprocess.check_output(["git", "show", ":"+file])
    for name in ("GEMINI_API_KEY", "GROQ_API_KEY", "AUTH_SECRET", "MCP_API_KEY"):
        value = values.get(name)
        if value and value.encode() in data:
            raise RuntimeError(f"Private value {name} detected in staged file {file}; commit blocked")
    if b'-----BEGIN PRIVATE KEY-----\n' in data or b'-----BEGIN PRIVATE KEY-----\r\n' in data:
        raise RuntimeError(f"Private key detected in staged file {file}; commit blocked")
print("Staged source secret scan passed; .env and runtime data are excluded.")
