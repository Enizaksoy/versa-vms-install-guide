"""Set DNS + NTP via vsh commands."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
DNS_PRIMARY = '192.168.20.254'
DNS_SECONDARY = '8.8.8.8'
NTP_SERVER = 'pool.ntp.org'

s = VmsSSH(HOST, USER, PASSWORD)

# vsh add-name-servers — interactive (no docs on input format from non-interactive).
# Try with stdin pipe; if fails, fall back to direct config.
print("=== vsh add-name-servers (try stdin) ===")
# This pipes both DNS servers separated by newline
rc, out, err = s.run(
    f'printf "{DNS_PRIMARY}\\n{DNS_SECONDARY}\\n" | vsh add-name-servers',
    login=True, sudo=False, timeout=60, pty=False
)

print("=== /etc/resolv.conf after ===")
s.run("cat /etc/resolv.conf")

print("=== vsh update-network-time (NTP server) ===")
rc, out, _ = s.run(
    f"vsh update-network-time --type server {NTP_SERVER}",
    login=True, sudo=False, timeout=60, pty=False
)

print("=== chrony.conf after ===")
s.run("grep -E '^server|^pool' /etc/chrony/chrony.conf 2>/dev/null || cat /etc/chrony/chrony.conf | tail -30", sudo=True)

print("=== chrony status ===")
s.run("chronyc sources -v 2>&1 | head -20", sudo=True)
s.run("chronyc tracking 2>&1 | head -10", sudo=True)

s.close()
