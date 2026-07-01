import requests
import json
import base64
from nacl import encoding, public

token = "YOUR_GITHUB_TOKEN_HERE"
owner = "lchau4501-collab"
repos = ["goctoiphapluat-step2-scripting", "goctoiphapluat-step3-prompts", "goctoiphapluatpipeline"]

# Read GOOGLE_SERVICE_ACCOUNT_TOKEN value
with open("/media/vpsg16gb/Workspace/goctoiphapluat/user_oauth2.json", "r") as f:
    g_token_val = f.read().strip()

secrets_to_update = {
    "GOOGLE_SERVICE_ACCOUNT_TOKEN": g_token_val,
    "SPREADSHEET_ID": "SPREADSHEET_ID_PLACEHOLDER",
    "GATEWAY_TOKEN": "sk-225f4ad2e9fb692e-2kwh0i-b1a15c74",
    "GATEWAY_URL": "https://unequaled-frankie-pseudoarchaically.ngrok-free.dev/v1",
    "GH_PAT": token
}

headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json"
}

def encrypt_secret(public_key_b64, secret_val):
    public_key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_val.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")

for repo in repos:
    print(f"\n=== Processing Repository: {owner}/{repo} ===")
    
    # Get public key
    pk_url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key"
    r = requests.get(pk_url, headers=headers)
    if r.status_code != 200:
        print(f"Failed to get public key for {repo}: {r.status_code} {r.text}")
        continue
    
    pk_info = r.json()
    key_id = pk_info["key_id"]
    public_key_b64 = pk_info["key"]
    
    for secret_name, secret_val in secrets_to_update.items():
        print(f"Updating secret {secret_name}...")
        encrypted_value = encrypt_secret(public_key_b64, secret_val)
        
        put_url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{secret_name}"
        data = {
            "encrypted_value": encrypted_value,
            "key_id": key_id
        }
        r_put = requests.put(put_url, headers=headers, json=data)
        if r_put.status_code in [201, 204]:
            print(f"  Successfully updated {secret_name} (Status: {r_put.status_code})")
        else:
            print(f"  Failed to update {secret_name}: {r_put.status_code} {r_put.text}")
