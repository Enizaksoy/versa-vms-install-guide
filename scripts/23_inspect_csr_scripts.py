"""Read the CSR/SAN list scripts to understand prompt sequence."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
s = VmsSSH(HOST, USER, PASSWORD)

# 1) gen-server-csr.sh
print("=== gen-server-csr.sh ===")
s.run("wc -l /opt/versa/scripts/gen-server-csr.sh", sudo=True)
s.run("cat /opt/versa/scripts/gen-server-csr.sh", sudo=True)

print("\n\n=== add-san-list helper in initmsghelper.sh ===")
s.run("grep -n 'add-san-list\\|add_san_list\\|add_san\\|SAN' /opt/versa/scripts/initmsghelper.sh | head -40", sudo=True)
# find function definition
s.run("awk '/add-san-list\\(\\)|add_san_list\\(\\)/,/^}/' /opt/versa/scripts/initmsghelper.sh | head -80", sudo=True)

print("\n=== server-csr.conf ===")
s.run("cat /opt/versa/scripts/certificates/server-csr.conf", sudo=True)

print("\n=== server-csr-base.conf ===")
s.run("cat /opt/versa/scripts/certificates/server-csr-base.conf", sudo=True)

s.close()
