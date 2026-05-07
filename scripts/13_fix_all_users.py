"""Find all users with default passwords and set them."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
NEW_PASS = '<vms-admin-pass>'

s = VmsSSH(HOST, USER, PASSWORD)

# 1) List all human-shell users
print("=== All users with bash/sh shell ===")
s.run("awk -F: '$7 ~ /bash|sh$/ && $3 >= 1000 {print $1, $3, $7}' /etc/passwd")

# 2) Shadow ages
print("=== Shadow ages (lower=older=likely default) ===")
s.run("awk -F: '$3 >= 1000 || $1 ~ /aaa|admin|versa|vmsadmin/ {print $1, $3, substr($2,1,5)}' /etc/passwd | head", )
s.run("awk -F: '{print $1, $3, substr($2,1,5)}' /etc/shadow | grep -E 'admin|versa|aaa|root|vms'", sudo=True)

# 3) Set password for each known default-bearing user
for u in ['aaaadmin', 'aaauser', 'versa', 'vmsadmin']:
    print(f"--- check user {u} ---")
    rc, out, _ = s.run(f"id {u} 2>/dev/null && echo EXISTS || echo MISSING", quiet=True)
    if 'EXISTS' in out:
        print(f"setting password for {u}")
        s.run(f"printf '{u}:{NEW_PASS}\\n' | chpasswd", sudo=True)
        s.run(f"chage -d $(date +%Y-%m-%d) {u}", sudo=True)
    else:
        print(f"{u} missing, skip")

# 4) Verify all shadow dates updated
print("=== After ===")
s.run("awk -F: '{print $1, $3}' /etc/shadow | grep -E 'admin|versa|aaa|vms'", sudo=True)

# 5) vsh status
print("=== vsh status ===")
rc, out, _ = s.vsh("status", timeout=30)
warning = 'default/expired passwords' in out
print(f"\n[default password warning: {warning}]")

s.close()
