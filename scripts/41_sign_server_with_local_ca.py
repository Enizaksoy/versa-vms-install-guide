"""
Sign server CSR with the newly-generated internal CA (from vms_cert_gen.sh).
Then rename to server-cert.pem and rebuild bundle.
"""
import sys, time
sys.path.insert(0, '.')
from lib_ssh import VmsSSH, sq

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
KEYPASS = '<keystore-pass>'

s = VmsSSH(HOST, USER, PASSWORD)

print("=== ca-key.pem header (encrypted?) ===")
s.run('head -2 /opt/versa/vms/certs/ca-key.pem', sudo=True)

print("\n=== If encrypted, decrypt to allow openssl ca to use it ===")
# Try to use as-is first; if fails, decrypt
s.run('openssl rsa -in /opt/versa/vms/certs/ca-key.pem -noout -check 2>&1', sudo=True)

# Check if it's encrypted by looking for ENCRYPTED tag
s.run('grep -E "ENCRYPTED|Proc-Type" /opt/versa/vms/certs/ca-key.pem || echo "not encrypted"', sudo=True)

print("\n=== If encrypted, create unencrypted backup and replace ===")
s.run(f"openssl rsa -in /opt/versa/vms/certs/ca-key.pem -out /tmp/ca-key-decrypted.pem -passin pass:{sq(KEYPASS)} 2>&1 | tail -3", sudo=True)
# Replace
s.run('cp /tmp/ca-key-decrypted.pem /opt/versa/vms/certs/ca-key.pem && rm /tmp/ca-key-decrypted.pem && chmod 400 /opt/versa/vms/certs/ca-key.pem', sudo=True)
s.run('head -2 /opt/versa/vms/certs/ca-key.pem', sudo=True)

print("\n=== Run sign-server-cert-with-local-CA.sh ===")
s.run('/opt/versa/scripts/certificates/sign-server-cert-with-local-CA.sh /opt/versa/vms/certs/server-csr.pem 2>&1', sudo=True, timeout=120)

print("\n=== Inspect output ===")
s.run('ls -la /opt/versa/vms/certs/secondary-* 2>&1', sudo=True)

print("\n=== Replace server-cert.pem and server-cert-bundle.pem with new CA-signed versions ===")
s.run('cp /opt/versa/vms/certs/secondary-server-cert.pem /opt/versa/vms/certs/server-cert.pem 2>&1 || echo "primary not found"', sudo=True)
s.run('cp /opt/versa/vms/certs/secondary-server-cert-bundle.pem /opt/versa/vms/certs/server-cert-bundle.pem 2>&1 || echo "bundle not found"', sudo=True)

# Some installs may not generate secondary-* if sign script renames; check both
s.run('ls -la /opt/versa/vms/certs/ | head -25', sudo=True)

# Permissions for pod read access
s.run('chmod 644 /opt/versa/vms/certs/server-cert.pem /opt/versa/vms/certs/server-cert-bundle.pem /opt/versa/vms/certs/server-key.pem', sudo=True)

print("\n=== Verify new server-cert.pem chain ===")
s.run('openssl x509 -in /opt/versa/vms/certs/server-cert.pem -noout -subject -issuer 2>&1', sudo=True)
s.run('grep -c BEGIN /opt/versa/vms/certs/server-cert-bundle.pem', sudo=True)
s.run('openssl verify -CAfile /opt/versa/vms/certs/root-ca-cert.pem -untrusted /opt/versa/vms/certs/ca-cert.pem /opt/versa/vms/certs/server-cert.pem 2>&1', sudo=True)

print("\n=== Verify cert+key match ===")
s.run("diff <(openssl x509 -in /opt/versa/vms/certs/server-cert.pem -pubkey -noout) <(openssl rsa -in /opt/versa/vms/certs/server-key.pem -pubout 2>/dev/null) && echo MATCH || echo MISMATCH", sudo=True)

print("\n=== Restart message-server pod ===")
s.run('kubectl delete pod -n message-server -l app=message-server 2>&1', sudo=True)
print("Waiting 40s for pod...")
time.sleep(40)

print("\n=== Pod status ===")
s.run('kubectl get pods -n message-server -o wide 2>&1', sudo=True)
print()
s.run('kubectl logs -n message-server -l app=message-server --tail=20 2>&1', sudo=True)

s.close()
