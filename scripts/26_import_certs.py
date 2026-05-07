"""
Push signed cert + root CA to VMS, then import via vsh.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
KEYPASS = '<keystore-pass>'

LOCAL_SIGNED = r'C:\Claude\vms_install\certs\server-cert.pem'
LOCAL_ROOT_CA = r'C:\Claude\vms_install\certs\root-ca-cert.pem'

s = VmsSSH(HOST, USER, PASSWORD)

# 0) Inspect import-certs.sh to know where it expects files
print("=== import-certs.sh source (first 100 lines) ===")
s.run("head -100 /opt/versa/scripts/import-certs.sh", sudo=True)

# 1) Upload certs to /tmp on VMS
print("\n=== Uploading certs to VMS:/tmp ===")
sftp = s.client.open_sftp()
sftp.put(LOCAL_SIGNED, '/tmp/server-cert.pem')
sftp.put(LOCAL_ROOT_CA, '/tmp/root-ca-cert.pem')
sftp.close()
s.run("ls -la /tmp/server-cert.pem /tmp/root-ca-cert.pem")

s.close()
