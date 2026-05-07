"""Add NOPASSWD sudoers entry for admin user."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
s = VmsSSH(HOST, USER, PASSWORD)

print("=== Existing sudoers ===")
s.run("ls -la /etc/sudoers.d/ && cat /etc/sudoers | grep -v '^#' | grep -v '^$'", sudo=True)
s.run("cat /etc/sudoers.d/*admin* /etc/sudoers.d/*versa* 2>/dev/null", sudo=True)

print("=== Add admin NOPASSWD entry ===")
# Use tee to write file with sudo
content = "admin ALL=(ALL) NOPASSWD: ALL\n"
s.run(f"echo 'admin ALL=(ALL) NOPASSWD: ALL' | tee /etc/sudoers.d/99-admin-nopasswd && chmod 440 /etc/sudoers.d/99-admin-nopasswd && visudo -c -f /etc/sudoers.d/99-admin-nopasswd", sudo=True)

print("=== Verify ===")
s.run("cat /etc/sudoers.d/99-admin-nopasswd", sudo=True)

print("\n=== Test sudo without password ===")
s.run("sudo -n whoami", sudo=False)
s.run("sudo -n test -f /opt/versa/etc/install/initial_pass_change && echo FLAG_PRESENT || echo FLAG_MISSING", sudo=False)

print("\n=== vsh status (no PTY needed now) ===")
rc, out, _ = s.vsh("status", timeout=60, pty=False)
print(f"\n[default password warning: {'default/expired passwords' in out}]")
print(f"[Server requirements not met: {'Server requirements not met' in out}]")
print(f"[sudo no tty errors: {'no tty present' in out}]")

s.close()
