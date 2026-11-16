"""GitHub Actions only: publish masked environment secrets to Secret Manager via stdin."""
import os
import subprocess

project = os.environ["PROJECT_ID"]
for key in ("GEMINI_API_KEY", "GROQ_API_KEY", "AUTH_SECRET", "MCP_API_KEY", "DEFAULT_OPERATOR_PASSWORD"):
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Required GitHub secret {key} is missing")
    name = "northgate-" + key.lower().replace("_", "-")
    args = ["gcloud", "secrets", "describe", name, f"--project={project}", "--quiet"]
    if subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        subprocess.run(["gcloud", "secrets", "create", name, f"--project={project}", "--replication-policy=user-managed", "--locations=asia-south1", "--quiet"], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["gcloud", "secrets", "versions", "add", name, f"--project={project}", "--data-file=-", "--quiet"], input=value, text=True, check=True, stdout=subprocess.DEVNULL)
    print(f"Runtime secret version configured: {key}")
