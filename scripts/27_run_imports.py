"""
Run vsh import-ca-certs + vsh import-server-certs.
Feed answers via stdin pipe (script uses 'read -p' which reads stdin).

For server-cert-bundle: since this is single-tier CA (root signs server directly),
bundle = server-cert.pem (just the cert). Some installs require intermediate, so
we use the same file.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH, sq

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'

s = VmsSSH(HOST, USER, PASSWORD)

# 1) Verify uploaded files
print("=== Cert files in /tmp ===")
s.run("ls -la /tmp/server-cert.pem /tmp/root-ca-cert.pem")
s.run("openssl x509 -in /tmp/server-cert.pem -noout -subject -issuer 2>&1")
s.run("openssl x509 -in /tmp/root-ca-cert.pem -noout -subject -issuer 2>&1")

# 2) For server-cert-bundle, create a chain file (server-cert + ca-cert)
print("\n=== Build server-cert-bundle (server + CA chain) ===")
s.run("cat /tmp/server-cert.pem /tmp/root-ca-cert.pem > /tmp/server-cert-bundle.pem && ls -la /tmp/server-cert-bundle.pem", sudo=True)

# 3) Run vsh import-ca-certs with stdin answers
# Prompts:
#   1: ca-cert file -> /tmp/root-ca-cert.pem
#   2: ca-cert-bundle file -> (skip / empty)
#   3: root-ca-cert file -> (skip / empty -> reuses ca-cert)
print("\n=== vsh import-ca-certs ===")
ca_answers = "/tmp/root-ca-cert.pem\n\n\n"
rc, out, _ = s.run(
    f"printf {sq(ca_answers)} | /opt/versa/scripts/import-certs.sh -type ca-certs",
    sudo=True, timeout=60
)

# 4) Verify ca-certs imported
print("\n=== /opt/versa/vms/certs/ after CA import ===")
s.run("ls -la /opt/versa/vms/certs/ /opt/versa/vms/certs/imported/", sudo=True)

# 5) Run vsh import-server-certs
# Prompts:
#   1: server-cert -> /tmp/server-cert.pem
#   2: server-cert-bundle -> /tmp/server-cert-bundle.pem
#   3: server-key -> /opt/versa/vms/certs/server-key.pem (we keep key on VMS)
print("\n=== vsh import-server-certs ===")
server_answers = "/tmp/server-cert.pem\n/tmp/server-cert-bundle.pem\n/opt/versa/vms/certs/server-key.pem\n"
rc, out, _ = s.run(
    f"printf {sq(server_answers)} | /opt/versa/scripts/import-certs.sh -type server-certs",
    sudo=True, timeout=60
)

# 6) Verify final state
print("\n=== Final cert directory ===")
s.run("ls -la /opt/versa/vms/certs/ /opt/versa/vms/certs/imported/", sudo=True)
print("\n=== Verify imported server cert ===")
s.run("openssl x509 -in /opt/versa/vms/certs/server-cert.pem -noout -subject -issuer -ext subjectAltName 2>&1", sudo=True)

s.close()
print("\n=== DONE — certs imported, ready for vsh configure ===")
