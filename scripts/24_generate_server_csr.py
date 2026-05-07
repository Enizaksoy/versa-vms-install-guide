"""
Generate server CSR by:
1. Writing custom SAN list to /opt/versa/scripts/certificates/server-csr.conf
2. Calling gen-server-csr.sh directly with --domain/--keypass args
3. Pulling the resulting CSR file to the workstation
"""
import sys, os, base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH, sq

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'

# Cert params
DOMAIN = 'vms-1.mylab.com'
COUNTRY = 'TR'
ORG = 'VersaLab'
KEYPASS = '<keystore-pass>'  # same pass as DB cert (per doc)

# SAN list — minimum 4 entries needed
SANS_DNS = [
    'vms-1.mylab.com',         # management FQDN
    'vms-1-elastic.mylab.com', # elastic FQDN
    'vms-vos.mylab.com',       # VOS-facing FQDN
    'vms-1',                   # short hostname
]
SANS_IP = [
    '192.168.30.15',  # eth0 mgmt
    '192.168.30.16',  # elastic VIP
    '192.168.20.15',  # eth1 southbound
]

s = VmsSSH(HOST, USER, PASSWORD)

# 1) Read server-csr-base.conf to get the base structure
print("=== Read server-csr-base.conf ===")
rc, base_conf, _ = s.run("cat /opt/versa/scripts/certificates/server-csr-base.conf", sudo=True)

# 2) Build new server-csr.conf
san_lines = []
for i, dns in enumerate(SANS_DNS, start=1):
    san_lines.append(f"DNS.{i} = {dns}")
for i, ip in enumerate(SANS_IP, start=1):
    san_lines.append(f"IP.{i} = {ip}")

new_conf = base_conf.rstrip() + "\n\n# SANs added by VMS install\n" + "\n".join(san_lines) + "\n"
print("\n=== New server-csr.conf content ===")
print(new_conf)

# 3) Write to VMS via base64 (avoids quoting issues)
b64 = base64.b64encode(new_conf.encode()).decode()
print("\n=== Write server-csr.conf ===")
s.run(f"echo {b64} | base64 -d > /opt/versa/scripts/certificates/server-csr.conf && cat /opt/versa/scripts/certificates/server-csr.conf", sudo=True)

# 4) Run gen-server-csr.sh
print("\n=== Run gen-server-csr.sh ===")
csr_cmd = (f"/opt/versa/scripts/gen-server-csr.sh "
           f"--domain {DOMAIN} --country {COUNTRY} --organization {ORG} "
           f"--keypass {sq(KEYPASS)}")
s.run(csr_cmd, sudo=True, timeout=300)

# 5) Show generated files
print("\n=== Generated cert files ===")
s.run("ls -la /opt/versa/vms/certs/", sudo=True)

# 6) Display CSR content
print("\n=== CSR PEM content ===")
s.run("cat /opt/versa/vms/certs/server-csr.pem", sudo=True)

# 7) Display CSR info
print("\n=== CSR details ===")
s.run("openssl req -noout -text -in /opt/versa/vms/certs/server-csr.pem", sudo=True)

# 8) Pull CSR to workstation
print("\n=== Pulling CSR to workstation ===")
sftp = s.client.open_sftp()
local_csr = r"C:\Claude\vms_install\certs\server-csr.pem"
local_key = r"C:\Claude\vms_install\certs\server-key.pem"

# Need to copy with sudo first to a path readable by admin
s.run("cp /opt/versa/vms/certs/server-csr.pem /tmp/server-csr.pem && chmod 644 /tmp/server-csr.pem", sudo=True)
sftp.get('/tmp/server-csr.pem', local_csr)
print(f"Saved CSR to {local_csr}")
# We won't pull the key — keep it on VMS
sftp.close()

s.close()
print("\n=== DONE ===")
print(f"CSR ready at {local_csr}")
print("Next: submit to AD CS via web enrollment.")
