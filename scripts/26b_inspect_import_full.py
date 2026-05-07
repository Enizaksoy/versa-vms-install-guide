"""Read the rest of import-certs.sh to understand server-certs flow."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
s = VmsSSH(HOST, USER, PASSWORD)

# Read full script
s.run("cat /opt/versa/scripts/import-certs.sh", sudo=True)

s.close()
