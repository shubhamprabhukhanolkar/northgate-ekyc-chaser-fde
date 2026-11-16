import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"backend"))
from app.db import rows

for row in rows("SELECT node,payload FROM traces ORDER BY id DESC LIMIT 8"):
    payload = json.loads(row["payload"])
    print(json.dumps({"node": row["node"], "payload": payload}, ensure_ascii=True))
