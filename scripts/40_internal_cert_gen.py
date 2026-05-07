"""
Run vms_cert_gen.sh manually to generate complete internal CA chain.
This is what PDF doc shows the install does in Pass 2 when regenerate=Y.

After regen: restart message-server pod and verify it comes up.
"""
import sys, time
sys.path.insert(0, '.')
from lib_ssh import VmsSSH, sq

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
DOMAIN = 'vms-1.mylab.com'
KEYPASS = '<keystore-pass>'

s = VmsSSH(HOST, USER, PASSWORD)

print("=== Find vms_cert_gen.sh location ===")
s.run('ls -la /opt/versa/vms/certs/vms_cert_gen.sh /opt/versa/scripts/certificates/vms_cert_gen.sh 2>&1', sudo=True)

print("\n=== Backup current cert dir (just in case) ===")
s.run('mkdir -p /opt/versa/vms/certs/pre_internal_gen_backup', sudo=True)
s.run('cp -p /opt/versa/vms/certs/*.pem /opt/versa/vms/certs/pre_internal_gen_backup/ 2>&1', sudo=True)

print("\n=== Run vms_cert_gen.sh — generates full internal chain ===")
# Build SAN list per PDF format
san = (
    f"{DOMAIN},"
    "DNS.1:vms-1-elastic.mylab.com,"
    "DNS.2:vms-vos.mylab.com,"
    "DNS.3:vms-1,"
    "IP.1:192.168.30.15,"
    "IP.2:192.168.30.16,"
    "IP.3:192.168.20.15"
)

cmd = (f"/opt/versa/vms/certs/vms_cert_gen.sh "
       f"--domain {DOMAIN} --country TR --state Istanbul --locality Istanbul "
       f"--organization VersaLab --organizationalunit IT "
       f"--email admin@example.com "
       f"--keypass {sq(KEYPASS)} --validity 3650 "
       f"--san {san}")

s.run(cmd, sudo=True, timeout=300)

print("\n=== After generation — list certs ===")
s.run('ls -la /opt/versa/vms/certs/*.pem /opt/versa/vms/certs/*.pfx /opt/versa/vms/certs/*.crt 2>/dev/null', sudo=True)

print("\n=== Inspect new server-cert.pem ===")
s.run('openssl x509 -in /opt/versa/vms/certs/server-cert.pem -noout -subject -issuer 2>&1', sudo=True)
s.run('wc -l /opt/versa/vms/certs/server-cert-bundle.pem', sudo=True)
s.run('grep -c BEGIN /opt/versa/vms/certs/server-cert-bundle.pem', sudo=True)

print("\n=== chmod for pod read access ===")
s.run('chmod 644 /opt/versa/vms/certs/server-cert.pem /opt/versa/vms/certs/server-cert-bundle.pem /opt/versa/vms/certs/server-key.pem /opt/versa/vms/certs/ca-cert.pem /opt/versa/vms/certs/root-ca-cert.pem', sudo=True)

print("\n=== Restart message-server pod ===")
s.run('kubectl delete pod -n message-server -l app=message-server 2>&1', sudo=True)
print("Waiting 30s for pod to start...")
time.sleep(30)

print("\n=== Pod status ===")
s.run('kubectl get pods -n message-server -o wide 2>&1', sudo=True)
print()
s.run('kubectl logs -n message-server -l app=message-server --tail=15 2>&1', sudo=True)

print("\n=== HTTPS endpoint test ===")
s.run('curl -k -s -o /dev/null -w "HTTPS Elastic IP (443): %{http_code}\\n" https://192.168.30.16:443/ --max-time 10')

s.close()
