"""
Create the initial_pass_change flag file (cleared password change).
Then verify all check_prerequisites pass: cores>=16, mem>=32000MB, disk>=1024GB, ROTA=0.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
s = VmsSSH(HOST, USER, PASSWORD)

# Verify what check_prerequisites actually computes
print("=== Prerequisite values ===")
s.run("lscpu | grep -m1 'CPU(s)' | awk '{print \"NCPU=\"$2}'")
s.run("free -m | grep Mem | awk '{print \"MEM=\"$2\"MB\"}'")
s.run("df -BG --output=size / | tail -n 1 | awk '{print \"DISK=\"$1}'")
s.run("lsblk -d -o name,rota | head")
s.run("lsblk -d -o name,rota | head -1 | grep -v sr0 | grep -v fd0 | grep -v ROTA | awk '{print \"ROTA=\"$2}'")
# the actual code does: head -1, after grep filters; let me run it correctly
s.run("lsblk -d -o name,rota | grep -vE 'sr0|fd0|ROTA' | head -1 | awk '{print \"ROTA(filtered)=\"$2}'")

# Create the flag file
print("=== Creating initial_pass_change flag ===")
s.run("touch /opt/versa/etc/install/initial_pass_change && chown versa:versa /opt/versa/etc/install/initial_pass_change && ls -la /opt/versa/etc/install/", sudo=True)

# Re-run vsh status
print("=== vsh status now ===")
rc, out, _ = s.vsh("status", timeout=30)
warning = 'default/expired passwords' in out
req = 'Server requirements not met' in out
print(f"\n[default password warning: {warning}]")
print(f"[Server requirements not met: {req}]")

# If still failing, identify which check fails
print("\n=== Check error messages in output ===")
for line in out.split('\n'):
    if 'requires at least' in line or 'rotational' in line or 'expired' in line:
        print(f"  ! {line.strip()}")

s.close()
