"""Set versa user password via chpasswd, then verify default-warning clears."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH, sq

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
NEW_VERSA = '<vms-admin-pass>'

s = VmsSSH(HOST, USER, PASSWORD)

# Inspect current state
print("=== Before ===")
s.run("awk -F: '$1==\"admin\" || $1==\"versa\" {print $1, $3, substr($2,1,5)}' /etc/shadow", sudo=True)
s.run("grep -E '^AllowUsers|^DenyUsers|^PermitRootLogin' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/* 2>/dev/null || echo 'none'", sudo=True)

# Set versa password via chpasswd reading from stdin
print("=== Setting versa password ===")
chpasswd_inner = f"printf 'versa:{NEW_VERSA}\\n' | chpasswd"
s.run(chpasswd_inner, sudo=True)

# Update password change date
s.run("chage -d $(date +%Y-%m-%d) versa", sudo=True)
s.run("chage -l versa", sudo=True)

# Verify shadow updated
print("=== After ===")
s.run("awk -F: '$1==\"admin\" || $1==\"versa\" {print $1, $3, substr($2,1,5)}' /etc/shadow", sudo=True)

# Re-run vsh status
print("=== vsh status now ===")
rc, out, _ = s.vsh("status", timeout=30)
warning = 'default/expired passwords' in out
req_not_met = 'Server requirements not met' in out
print(f"\n[default password warning: {warning}]")
print(f"[server requirements not met: {req_not_met}]")

s.close()
