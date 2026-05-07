"""Inspect the dialog script that contains 'default/expired passwords' string."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
s = VmsSSH(HOST, USER, PASSWORD)

s.run("cat /etc/profile.d/versa-vms-profile.sh", sudo=True)
print("\n\n=========================================\n\n")
s.run("cat /opt/versa/scripts/dialog/versa-vms-profile-dialog.sh", sudo=True)

s.close()
