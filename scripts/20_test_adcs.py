"""
Test AD CS web enrollment from VMS host.
Discover available templates and the CA name.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
CA_URL = 'http://192.168.20.254/certsrv/'
CA_USER = 'Administrator'
CA_PASS = '<ad-admin-pass>'

s = VmsSSH(HOST, USER, PASSWORD)

# 1) Connectivity test
print("=== TCP connectivity to CA ===")
s.run("nc -zv 192.168.20.254 80 2>&1 || ncat -zv 192.168.20.254 80 2>&1 || echo 'no nc/ncat'")
s.run("curl -m 10 -s -o /dev/null -w 'HTTP %{http_code}\\n' http://192.168.20.254/")

# 2) Test certsrv root (will likely 401 without auth)
print("=== certsrv root (no auth) ===")
s.run("curl -m 10 -s -o /dev/null -w 'HTTP %{http_code}\\n' http://192.168.20.254/certsrv/")

# 3) Test with NTLM auth + Negotiate
print("=== certsrv root (NTLM auth) ===")
s.run(f"curl -m 15 -s --ntlm -u 'mylab\\\\Administrator:<ad-admin-pass>' http://192.168.20.254/certsrv/ -o /tmp/certsrv.html -w 'HTTP %{{http_code}} size=%{{size_download}}\\n' && head -50 /tmp/certsrv.html")

# 4) Try certrqxt.asp (CSR submit page) with auth
print("=== certrqxt.asp (CSR submit page) ===")
s.run(f"curl -m 15 -s --ntlm -u 'mylab\\\\Administrator:<ad-admin-pass>' 'http://192.168.20.254/certsrv/certrqxt.asp' -o /tmp/certrqxt.html -w 'HTTP %{{http_code}} size=%{{size_download}}\\n' && grep -oE 'name=\"CertificateTemplate\"[^>]*' /tmp/certrqxt.html | head -5")
s.run("grep -A 30 'CertificateTemplate' /tmp/certrqxt.html | head -50")

# 5) Discover CA name
print("=== CA Name from certnew.cer ===")
s.run(f"curl -m 15 -s --ntlm -u 'mylab\\\\Administrator:<ad-admin-pass>' 'http://192.168.20.254/certsrv/certfnsh.asp' -o /tmp/certfnsh.html -w 'HTTP %{{http_code}}\\n'")

s.close()
