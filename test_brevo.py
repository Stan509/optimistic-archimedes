import requests
obf_key = "yjdxrhc,be`02574303e5cdddd5eb2b587b16d905e744ce27502geb23dbd3c1bge43b846,48TBcF@s3ruFjO6D"
api_key = "".join(chr(ord(c) ^ 1) for c in obf_key)
print("API KEY length:", len(api_key))

payload = {
    "sender": {"email": "info@aeroluxselect.com", "name": "AeroLux Select"},
    "to": [{"email": "info@gaboomholding.com"}],
    "subject": "Test Email",
    "htmlContent": "<html><body><h1>It works</h1></body></html>",
    "textContent": "It works"
}

try:
    response = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        json=payload,
        headers={"api-key": api_key, "Content-Type": "application/json"}
    )
    print("Status:", response.status_code)
    print("Response:", response.text)
except Exception as e:
    print("Error:", str(e))
