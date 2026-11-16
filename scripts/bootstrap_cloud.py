"""Configure the requested GitHub/GCP deployment. Credentials stay in stdin/memory."""
import json
import base64
import requests
import shutil
import subprocess
from pathlib import Path
from dotenv import dotenv_values

PROJECT = "slabspro-slabsuser37"
REPO = "shubhamprabhukhanolkar/northgate-ekyc-chaser-fde"
SA = f"slabsuser37-service-account@{PROJECT}.iam.gserviceaccount.com"
POOL = "northgate-github"


def command(args, input=None, allow_failure=False):
    executable = shutil.which(args[0])
    result = subprocess.run([executable, *args[1:]], input=input, text=True, capture_output=True)
    if result.returncode and not allow_failure:
        # Never print input or the full command: commands may carry private values.
        raise RuntimeError(f"{args[0]} {args[1]} failed: {result.stderr[:1800]}")
    return result


def gcloud(*args, allow_failure=False):
    return command(["gcloud", *args, f"--project={PROJECT}", "--quiet"], allow_failure=allow_failure)


def main():
    active = command(["gcloud", "config", "get-value", "project"]).stdout.strip()
    if active != PROJECT:
        raise RuntimeError(f"Active project {active} differs from expected {PROJECT}")
    values = dotenv_values(Path(__file__).resolve().parents[1]/".env")
    for name in ("GEMINI_API_KEY", "GROQ_API_KEY", "AUTH_SECRET", "MCP_API_KEY"):
        if not values.get(name):
            raise RuntimeError(f"Missing {name} in .env")
    gcloud("services", "enable", "iam.googleapis.com", "iamcredentials.googleapis.com", "sts.googleapis.com", "run.googleapis.com", "artifactregistry.googleapis.com", "secretmanager.googleapis.com")
    print("Required GCP APIs enabled.", flush=True)
    # Match the supplied p1.yml service-account JSON authentication. Never write
    # a private key to disk or pass it on a process command line.
    names = json.loads(command(["gh", "secret", "list", "--repo", REPO, "--json", "name"]).stdout)
    if not any(item["name"] == "GCP_CREDENTIALS" for item in names):
        token = command(["gcloud", "auth", "print-access-token"]).stdout.strip()
        response = requests.post(f"https://iam.googleapis.com/v1/projects/{PROJECT}/serviceAccounts/{SA}/keys",
            headers={"Authorization": "Bearer " + token}, json={"privateKeyType": "TYPE_GOOGLE_CREDENTIALS_FILE", "keyAlgorithm": "KEY_ALG_RSA_2048"}, timeout=40)
        if response.status_code != 200:
            raise RuntimeError(f"Service-account deployment key creation denied (HTTP {response.status_code}). Supply an existing authorized service-account key privately.")
        key = base64.b64decode(response.json()["privateKeyData"]).decode()
        command(["gh", "secret", "set", "GCP_CREDENTIALS", "--repo", REPO], input=key)
    print("Existing service-account deployment identity configured in encrypted GitHub secret.", flush=True)
    variables = {"GCP_PROJECT": PROJECT, "GCP_SERVICE_ACCOUNT": SA,
                 "GROQ_MODEL": values.get("GROQ_MODEL") or "openai/gpt-oss-120b",
                 "GEMINI_MODEL_NAME": values.get("GEMINI_MODEL_NAME") or values.get("GEMINI_MODEL") or "gemini-3.5-flash-lite"}
    for key, value in variables.items():
        command(["gh", "variable", "set", key, "--repo", REPO], input=value)
    for key in ("GEMINI_API_KEY", "GROQ_API_KEY", "AUTH_SECRET", "MCP_API_KEY", "DEFAULT_OPERATOR_PASSWORD"):
        command(["gh", "secret", "set", key, "--repo", REPO], input=values.get(key) or "NorthgateDemo!2026")
    print("GitHub variables and five encrypted secrets configured; no values printed.", flush=True)


if __name__ == "__main__":
    main()
