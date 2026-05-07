"""
Phase 2 — Restore AD CS-signed certs (replace internal CA with mylab CA).
1. Restore from /opt/versa/vms/certs/adcs_backup/
2. But — bundle needs proper format. Use server-cert + ca-cert (= AD CS Issuer = root) only since AD CS deploy is single-tier.
3. Pod restart, verify chain still valid + Issuer = mylab-WIN-TOKHI12EIJE-CA
"""
import sys, time
sys.path.insert(0, '.')
from lib_ssh import VmsSSH

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
s = VmsSSH(HOST, USER, PASSWORD)

print("=== Backup current internal CA setup ===")
s.run('mkdir -p /opt/versa/vms/certs/internal_ca_phase1_backup', sudo=True)
s.run('cp -p /opt/versa/vms/certs/{server-cert.pem,server-cert-bundle.pem,server-key.pem,ca-cert.pem,ca-key.pem,root-ca-cert.pem,root-ca-key.pem} /opt/versa/vms/certs/internal_ca_phase1_backup/', sudo=True)
s.run('ls -la /opt/versa/vms/certs/internal_ca_phase1_backup/', sudo=True)

print("\n=== List adcs_backup contents ===")
s.run('ls -la /opt/versa/vms/certs/adcs_backup/', sudo=True)

print("\n=== Check AD CS bundle format (is it 2 or 3 BEGIN markers?) ===")
s.run('grep -c BEGIN /opt/versa/vms/certs/adcs_backup/server-cert-bundle.pem', sudo=True)
s.run('openssl x509 -in /opt/versa/vms/certs/adcs_backup/server-cert.pem -noout -issuer', sudo=True)

# AD CS is single-tier (no intermediate). Bundle needs proper PEM concat.
# Bundle = server + (intermediate(s) | none) + root.
# For AD CS single-tier: bundle = server + root (2 BEGIN). VMS needs 3 BEGIN, so we need intermediate.
# WORKAROUND: Use AD CS server-cert as leaf, and our INTERNAL ca-cert + root-ca-cert as chain
# Wait — that wouldn't validate chain (server signed by AD CS root, not internal CA).
# CORRECT APPROACH: For AD CS single-tier, bundle = server + root (2 BEGIN). VMS may not accept this.
# We need to create a "fake intermediate" or just use server-cert.pem alone as cert-file?

# Strategy: try as-is first (server-cert.pem + bundle = server+root). If pod fails, try alternative.

print("\n=== Restore AD CS certs to active locations ===")
s.run('cp -p /opt/versa/vms/certs/adcs_backup/server-cert.pem /opt/versa/vms/certs/server-cert.pem', sudo=True)
s.run('cp -p /opt/versa/vms/certs/adcs_backup/server-cert-bundle.pem /opt/versa/vms/certs/server-cert-bundle.pem', sudo=True)
s.run('cp -p /opt/versa/vms/certs/adcs_backup/server-key.pem /opt/versa/vms/certs/server-key.pem', sudo=True)
s.run('cp -p /opt/versa/vms/certs/adcs_backup/ca-cert.pem /opt/versa/vms/certs/ca-cert.pem', sudo=True)
s.run('cp -p /opt/versa/vms/certs/adcs_backup/root-ca-cert.pem /opt/versa/vms/certs/root-ca-cert.pem', sudo=True)
s.run('chmod 644 /opt/versa/vms/certs/server-cert.pem /opt/versa/vms/certs/server-cert-bundle.pem /opt/versa/vms/certs/server-key.pem /opt/versa/vms/certs/ca-cert.pem /opt/versa/vms/certs/root-ca-cert.pem', sudo=True)

print("\n=== Verify ===")
s.run('openssl x509 -in /opt/versa/vms/certs/server-cert.pem -noout -subject -issuer', sudo=True)
s.run('grep -c BEGIN /opt/versa/vms/certs/server-cert-bundle.pem', sudo=True)
s.run('openssl verify -CAfile /opt/versa/vms/certs/root-ca-cert.pem /opt/versa/vms/certs/server-cert.pem', sudo=True)
s.run('diff <(openssl x509 -in /opt/versa/vms/certs/server-cert.pem -pubkey -noout) <(openssl rsa -in /opt/versa/vms/certs/server-key.pem -pubout 2>/dev/null) && echo MATCH || echo MISMATCH', sudo=True)

print("\n=== Restart message-server pod ===")
s.run('kubectl delete pod -n message-server -l app=message-server 2>&1', sudo=True)
print("Waiting 40s...")
time.sleep(40)

print("\n=== Pod status ===")
s.run('kubectl get pods -n message-server -o wide 2>&1', sudo=True)
print()
s.run('kubectl logs -n message-server -l app=message-server --tail=20 2>&1', sudo=True)

s.close()
