"""Locate the source of 'default/expired passwords' check in VMS scripts."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
s = VmsSSH(HOST, USER, PASSWORD)

# Find string in scripts
print("=== Grep for 'default/expired' in versa scripts ===")
s.run("grep -rln 'default/expired' /opt/versa/ /etc/profile.d/ 2>/dev/null", sudo=True)

print("=== Grep for 'modify-system-password' as message ===")
s.run("grep -rn 'modify-system-password' /opt/versa/scripts/ 2>/dev/null | head -10", sudo=True)

print("=== Look for password check function ===")
s.run("grep -n 'check.*password\\|password.*check\\|default.*password' /etc/profile.d/versa-env.sh | head -20", sudo=True)
s.run("grep -rn 'default_password\\|check_password\\|default.expired' /opt/versa/scripts/initmsghelper.sh 2>/dev/null | head -20", sudo=True)

print("=== Look at check_prerequisites function ===")
s.run("grep -A 30 '^check_prerequisites\\|check_prerequisites()' /etc/profile.d/versa-env.sh | head -60", sudo=True)

print("=== Find any state file that vsh uses to track password changes ===")
s.run("ls -la /opt/versa/etc/install/ 2>/dev/null", sudo=True)
s.run("ls -la /var/lib/vs/ 2>/dev/null", sudo=True)
s.run("cat /opt/versa/etc/install/initial_pass_change 2>/dev/null", sudo=True)

print("=== /etc/profile.d/versa-env.sh tail (1000 lines+) ===")
s.run("wc -l /etc/profile.d/versa-env.sh", sudo=True)

s.close()
