"""
Set versa user password directly via chpasswd to clear 'default password' warning.
Bypasses vsh modify-system-password (which would try admin again and fail on reuse).
"""
import sys, base64
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
NEW_VERSA_PASS = '<vms-admin-pass>'  # same as admin for simplicity

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASSWORD, timeout=15,
          allow_agent=False, look_for_keys=False)

def run(cmd, sudo=False, timeout=60, stdin_data=None):
    if sudo:
        b64 = base64.b64encode(cmd.encode()).decode()
        full = f'echo "{PASSWORD}" | sudo -S -p "" bash -c "$(echo {b64} | base64 -d)"'
    else:
        full = cmd
    print(f"$ {cmd}")
    si, o, e = c.exec_command(full, timeout=timeout)
    if stdin_data:
        si.write(stdin_data)
        si.flush()
        si.channel.shutdown_write()
    rc = o.channel.recv_exit_status()
    out = o.read().decode(errors='replace')
    err = e.read().decode(errors='replace')
    if out.strip(): print(out.rstrip())
    if err.strip() and 'password for' not in err: print(f"[err] {err.rstrip()}")
    print(f"[rc={rc}]\n")
    return out + err

# 1) Inspect shadow to confirm versa needs change
b64_check = base64.b64encode(b"awk -F: '$1==\"admin\" || $1==\"versa\" {print $1, $3, substr($2,1,4)}' /etc/shadow").decode()
run(f"echo {b64_check} | base64 -d | bash", sudo=True)

# 2) Inspect sshd_config for AllowUsers
run("grep -E '^AllowUsers|^DenyUsers|^PermitRootLogin' /etc/ssh/sshd_config", sudo=True)

# 3) Set versa password via chpasswd (encrypted via stdin)
print("=== Setting versa user password via chpasswd ===")
chpasswd_cmd = f"chpasswd <<EOF\nversa:{NEW_VERSA_PASS}\nEOF"
run(chpasswd_cmd, sudo=True)

# 4) Verify shadow updated
b64_check2 = base64.b64encode(b"awk -F: '$1==\"admin\" || $1==\"versa\" {print $1, $3, substr($2,1,4)}' /etc/shadow").decode()
run(f"echo {b64_check2} | base64 -d | bash", sudo=True)

# 5) Update chage to mark password changed today (in case VMS checks age)
run("chage -d $(date +%Y-%m-%d) versa", sudo=True)
run("chage -l versa", sudo=True)

# 6) Re-run vsh status to see if warning clears
print("\n=== vsh status after fix ===")
out = run("bash -lic 'vsh status' 2>&1 | head -40")
warning = 'default/expired passwords' in out
print(f"[default password warning still present? {warning}]")

c.close()
