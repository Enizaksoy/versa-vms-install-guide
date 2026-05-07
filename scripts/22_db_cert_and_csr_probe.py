"""
Generate DB cert (self-signed, internal). Then probe vsh generate-server-csr
to capture interactive prompts.
"""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH, sq

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import paramiko

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'

# Cert params
DOMAIN = 'vms-1.mylab.com'
COUNTRY = 'TR'
STATE = 'Istanbul'
LOCALITY = 'Istanbul'
ORG = 'VersaLab'
OU = 'IT'
EMAIL = 'admin@example.com'
KEYPASS = '<keystore-pass>'  # for cert key
VALIDITY = '3650'

s = VmsSSH(HOST, USER, PASSWORD)

# 1) DB cert
print("=== Locate cert generation scripts ===")
s.run("ls -la /opt/versa/vms/db/ /opt/versa/vms/certs/ /opt/versa/scripts/certificates/ 2>/dev/null", sudo=True)
s.run("find /opt/versa -name 'vms_db_ca_cert_gen.sh' -o -name 'vms_cert_gen.sh' -o -name 'gen-server-csr.sh' 2>/dev/null", sudo=True)

# 2) Generate DB cert with --san covering all VMS FQDNs
db_san = "vms-1.mylab.com,DNS.1:vms-1-elastic.mylab.com,DNS.2:vms-vos.mylab.com,IP.1:192.168.30.15,IP.2:192.168.30.16,IP.3:192.168.20.15"
db_cmd = (f"/opt/versa/vms/db/vms_db_ca_cert_gen.sh "
          f"--domain {DOMAIN} --country {COUNTRY} --state {STATE} "
          f"--locality {LOCALITY} --organization {ORG} --organizationalunit {OU} "
          f"--email {EMAIL} --keypass {sq(KEYPASS)} --validity {VALIDITY} "
          f"--san {db_san}")

print("\n=== Generate DB CA cert ===")
print(f"Command: {db_cmd}")
s.run(db_cmd, sudo=True, timeout=180)

# 3) List generated db cert files
print("\n=== DB cert files ===")
s.run("ls -la /opt/versa/vms/db/ | head -30", sudo=True)
s.run("find /opt/versa/vms/db -name '*.pem' -o -name '*.crt' -o -name '*.key' 2>/dev/null | head -10", sudo=True)

# 4) Probe vsh generate-server-csr by running with interactive shell + capturing prompts
print("\n=== Probe vsh generate-server-csr (interactive) — first prompt only ===")
chan = s.client.invoke_shell(term='xterm', width=200, height=50)
chan.settimeout(2.0)

# wait for shell prompt
time.sleep(2)
buf = ''
while chan.recv_ready():
    buf += chan.recv(65535).decode(errors='replace')
print(buf, end='')

# send command
chan.send('vsh generate-server-csr\n')

# read for 30s capturing prompts
print("\n[reading prompts for 30s...]")
buf = ''
end = time.time() + 30
while time.time() < end:
    if chan.recv_ready():
        d = chan.recv(65535).decode(errors='replace')
        buf += d
        sys.stdout.write(d)
        sys.stdout.flush()
        # If we see a prompt that needs response, abort with Ctrl-C
        if re.search(r'(:\s*$|\?\s*$|\[Y/n\]|\[y/N\]|\(Y/N\))', buf.split('\n')[-1] if buf else ''):
            time.sleep(1)
    else:
        time.sleep(0.5)

# Cancel — we just probed
print("\n[sending Ctrl-C to cancel]")
chan.send('\x03')
time.sleep(1)
chan.send('q\n')
time.sleep(1)
chan.close()

s.close()
