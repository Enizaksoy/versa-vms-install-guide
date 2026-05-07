"""Run vsh status via bash -lic and check shadow file properly."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko, base64

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASSWORD, timeout=15,
          allow_agent=False, look_for_keys=False)

def run(cmd, sudo=False, timeout=60):
    if sudo:
        # write password to a fd that sudo reads
        b64 = base64.b64encode(cmd.encode()).decode()
        full = f'echo "{PASSWORD}" | sudo -S -p "" bash -c "$(echo {b64} | base64 -d)"'
    else:
        full = cmd
    print(f"$ {cmd}")
    _, o, e = c.exec_command(full, timeout=timeout)
    rc = o.channel.recv_exit_status()
    out = o.read().decode(errors='replace')
    err = e.read().decode(errors='replace')
    if out.strip(): print(out.rstrip())
    if err.strip() and 'password for' not in err and 'job control' not in err and 'ioctl' not in err:
        print(f"[err] {err.rstrip()}")
    print(f"[rc={rc}]\n")
    return out + err

# 1) vsh status via login shell
out = run("bash -lic 'vsh status' 2>&1")
default_warning = 'default/expired passwords' in out
print(f"[default password warning present? {default_warning}]\n")

# 2) Check shadow encrypted password fields for admin and versa
run("awk -F: '$1==\"admin\" || $1==\"versa\" {print $1, substr($2,1,5), \"len=\"length($2)}' /etc/shadow", sudo=True)

# 3) Check shells / login shell of versa user
run("getent passwd versa admin")

# 4) Try login as versa user with new password (in case both got same)
print("\n=== Try versa user with NEW password ===")
c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    c2.connect(HOST, username='versa', password=PASSWORD, timeout=10,
               allow_agent=False, look_for_keys=False)
    print("[versa user accepts new password — both changed in v2 run]")
    c2.close()
except paramiko.AuthenticationException:
    print("[versa user does not accept new password]")
except Exception as e:
    print(f"[error: {e}]")

c.close()
