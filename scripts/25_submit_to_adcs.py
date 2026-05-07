"""
Submit CSR to Microsoft AD CS web enrollment, retrieve signed cert + root CA.

Steps:
  1. Read local CSR
  2. POST to /certsrv/certfnsh.asp with WebServer template
  3. Parse ReqID from response
  4. GET /certsrv/certnew.cer?ReqID=N&Enc=b64 for signed cert (PEM)
  5. GET /certsrv/certnew.cer?type=CACert (root CA, DER)
  6. Convert to PEM if needed; save both
"""
import sys, os, re, urllib.parse
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import requests
    from requests_ntlm import HttpNtlmAuth
except ImportError:
    print("Installing requests + requests-ntlm ...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "requests", "requests-ntlm"])
    import requests
    from requests_ntlm import HttpNtlmAuth

CA_BASE = 'http://192.168.20.254/certsrv'
CA_USER = 'Administrator'
CA_PASS = '<ad-admin-pass>'
TEMPLATE = 'WebServer'

CSR_PATH = r'C:\Claude\vms_install\certs\server-csr.pem'
SIGNED_CERT_PATH = r'C:\Claude\vms_install\certs\server-cert.pem'
ROOT_CA_PATH = r'C:\Claude\vms_install\certs\root-ca-cert.pem'
CHAIN_PATH = r'C:\Claude\vms_install\certs\ca-chain.p7b'

session = requests.Session()
session.auth = HttpNtlmAuth(CA_USER, CA_PASS)
session.timeout = 30

# 1) Read CSR
with open(CSR_PATH, 'r') as f:
    csr_pem = f.read()
print(f"=== CSR loaded from {CSR_PATH} ({len(csr_pem)} bytes) ===")
print(csr_pem[:200] + "..." + csr_pem[-100:])

# 2) Submit CSR
print("\n=== POST /certsrv/certfnsh.asp ===")
form = {
    'Mode': 'newreq',
    'CertRequest': csr_pem,
    'CertAttrib': f'CertificateTemplate:{TEMPLATE}',
    'TargetStoreFlags': '0',
    'SaveCert': 'yes',
    'ThumbPrint': '',
    'FriendlyType': 'Saved-Request Certificate',
}

r = session.post(f"{CA_BASE}/certfnsh.asp", data=form)
print(f"HTTP {r.status_code}, size={len(r.text)}")

# 3) Parse ReqID
req_id_match = re.search(r'certnew\.cer\?ReqID=(\d+)', r.text)
if not req_id_match:
    # Try alternate patterns
    req_id_match = re.search(r'ReqID=(\d+)', r.text)
if not req_id_match:
    print("\nFailed to find ReqID. First 2000 chars of response:")
    print(r.text[:2000])
    # Look for error markers
    err = re.search(r'(Denied by|error|policy module|disposition message)[^<]{0,300}', r.text, re.I)
    if err:
        print(f"\nError marker found: {err.group(0)[:300]}")
    sys.exit(1)

req_id = req_id_match.group(1)
print(f"\n=== Request ID = {req_id} ===")

# 4) Download signed cert (b64-encoded PEM)
print(f"\n=== GET /certsrv/certnew.cer?ReqID={req_id}&Enc=b64 ===")
r2 = session.get(f"{CA_BASE}/certnew.cer?ReqID={req_id}&Enc=b64")
print(f"HTTP {r2.status_code}, size={len(r2.text)}")

# Should be a PEM-encoded cert
if '-----BEGIN CERTIFICATE-----' not in r2.text:
    print("Signed cert response doesn't look like PEM. First 500 chars:")
    print(r2.text[:500])
    sys.exit(1)

# Save signed cert
with open(SIGNED_CERT_PATH, 'w') as f:
    f.write(r2.text.strip() + '\n')
print(f"Saved signed cert to {SIGNED_CERT_PATH}")

# 5) Download root CA cert
print(f"\n=== GET /certsrv/certnew.cer?ReqID=CACert&Renewal=0&Enc=b64 ===")
r3 = session.get(f"{CA_BASE}/certnew.cer?ReqID=CACert&Renewal=0&Enc=b64")
print(f"HTTP {r3.status_code}, size={len(r3.text)}")

if '-----BEGIN CERTIFICATE-----' in r3.text:
    with open(ROOT_CA_PATH, 'w') as f:
        f.write(r3.text.strip() + '\n')
    print(f"Saved root CA cert to {ROOT_CA_PATH}")
else:
    print("Root CA response not PEM. First 300 chars:")
    print(r3.text[:300])

# 6) Download CA chain (P7B)
print(f"\n=== GET /certsrv/certnew.p7b?ReqID=CACert&Renewal=0&Enc=b64 ===")
r4 = session.get(f"{CA_BASE}/certnew.p7b?ReqID=CACert&Renewal=0&Enc=b64")
print(f"HTTP {r4.status_code}, size={len(r4.text)}")

if r4.status_code == 200 and len(r4.content) > 0:
    with open(CHAIN_PATH, 'wb') as f:
        f.write(r4.content)
    print(f"Saved CA chain to {CHAIN_PATH}")

# 7) Verify signed cert
print("\n=== Verifying signed cert ===")
import subprocess
result = subprocess.run(
    ['openssl', 'x509', '-in', SIGNED_CERT_PATH, '-noout', '-text'],
    capture_output=True, text=True
)
if result.returncode == 0:
    out = result.stdout
    # extract Subject, Issuer, SAN, validity
    for pat in [r'Subject:.*', r'Issuer:.*', r'Not Before.*', r'Not After.*', r'X509v3 Subject Alternative Name:.*\n.*']:
        m = re.search(pat, out)
        if m:
            print(m.group(0).strip())
else:
    print(f"openssl error: {result.stderr}")

print("\n=== DONE — certs ready in C:\\Claude\\vms_install\\certs\\ ===")
