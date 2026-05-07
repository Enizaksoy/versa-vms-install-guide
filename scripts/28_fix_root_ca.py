"""
Workaround for import-certs.sh bug: copy ca-cert.pem -> root-ca-cert.pem manually.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
s = VmsSSH(HOST, USER, PASSWORD)

# Copy ca-cert -> root-ca-cert
s.run("cp /opt/versa/vms/certs/ca-cert.pem /opt/versa/vms/certs/root-ca-cert.pem", sudo=True)
s.run("touch /opt/versa/vms/certs/imported/root-ca-cert.pem", sudo=True)
s.run("chown -R root:root /opt/versa/vms/certs/root-ca-cert.pem", sudo=True)

# Verify
s.run("ls -la /opt/versa/vms/certs/*.pem /opt/versa/vms/certs/imported/", sudo=True)
s.run("openssl x509 -in /opt/versa/vms/certs/root-ca-cert.pem -noout -subject 2>&1", sudo=True)

# Also verify cert chain validation
print("\n=== Chain validation: signed cert against root CA ===")
s.run("openssl verify -CAfile /opt/versa/vms/certs/root-ca-cert.pem /opt/versa/vms/certs/server-cert.pem 2>&1", sudo=True)

s.close()
