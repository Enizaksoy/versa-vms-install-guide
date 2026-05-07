"""
Run `vsh configure` end-to-end via PTY shell with adaptive prompt handling.
Logs everything to vms_install/logs/configure_<ts>.log.

Pre-configured answers (by pattern match):
  - change shell password? N
  - mgmt IP                = 192.168.30.15
  - FQDN                   = vms-1.mylab.com
  - First Control Plane    = Y
  - SAN finalized?         = Y (already in cert)
  - keystore password      = <keystore-pass>
  - VOS/ADC connection IP  = 192.168.20.15
  - Elastic FQDN           = vms-1-elastic.mylab.com
  - Elastic IP             = 192.168.30.16
  - Node name              = vms-1.mylab.com
  - SSD/rotational warning = continue
  - Use existing certs?    = Y
"""
import sys, os, time, re, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'

# Configuration values
ANSWERS = {
    'mgmt_ip':       '192.168.30.15',
    'fqdn':          'vms-1.mylab.com',
    'elastic_fqdn':  'vms-1-elastic.mylab.com',
    'elastic_ip':    '192.168.30.16',
    'vos_ip':        '192.168.20.15',
    'node_name':     'vms-1.mylab.com',
    'keystore_pass': '<keystore-pass>',
    'san1':          'vms-1-elastic.mylab.com',
    'san2':          'vms-vos.mylab.com',
}

# Prompt rules: list of (regex, response, hide?)
# Order matters — first match wins. Some prompts share substrings, more
# specific patterns FIRST.
RULES = [
    # password change prompt — already done, decline
    (r'continue to change shell password.*\(y/N\)\s*:\s*$',                             'N',                          False),
    (r'change.*password.*\(y/N\)',                                                      'N',                          False),
    # disk warning — continue
    (r'rotational disk.*continue',                                                      'y',                          False),
    # Subject Alt-Names finalized
    (r'Subject Alt-Names finalized.*\[y/N\]\s*:?\s*$',                                  'Y',                          False),
    # First Control Plane Node
    (r'First Control Plane Node.*\(Y/n\)|First Control Plane.*\[Y/n\]',                  'Y',                          False),
    # FQDN / hostname prompt
    (r'(FQDN|hostname|Fully qualified).*Versa Message.*:?\s*$',                          ANSWERS['fqdn'],              False),
    (r'(FQDN|hostname).*VMS Server.*:?\s*$',                                             ANSWERS['fqdn'],              False),
    (r'(FQDN|hostname).*node.*:?\s*$',                                                   ANSWERS['fqdn'],              False),
    # Management IP
    (r'Management Interface IP.*:?\s*$',                                                 ANSWERS['mgmt_ip'],           False),
    (r'(Management|Northbound).*IP.*:?\s*$',                                             ANSWERS['mgmt_ip'],           False),
    # Subject ALT name 1/2
    (r'Subject ALT Name 1.*:?\s*$|Alt[- ]?Name 1.*:?\s*$|First.*SAN.*:?\s*$',            ANSWERS['san1'],              False),
    (r'Subject ALT Name 2.*:?\s*$|Alt[- ]?Name 2.*:?\s*$|Second.*SAN.*:?\s*$',           ANSWERS['san2'],              False),
    # Confirm FQDN
    (r'Continue.*FQDN.*\[Y/n\]|FQDN.*confirm.*\[Y/n\]',                                  'Y',                          False),
    # Generate certs with FQDN
    (r'Generate.*cert.*FQDN.*\[Y/n\]|Generate certificate.*\[Y/n\]',                     'Y',                          False),
    # Use existing imported certs
    (r'(Use|use existing).*(cert|imported).*\[Y/n\]|certs.*present.*\[Y/n\]',            'Y',                          False),
    # Node name / unique
    (r'(Unique )?[Nn]ode\s*[Nn]ame.*:?\s*$',                                             ANSWERS['node_name'],         False),
    # Keystore password (asked twice usually)
    (r'(Enter|RE-?Enter).*[Pp]assword.*[Cc]ert.*:?\s*$',                                 ANSWERS['keystore_pass'],     True),
    (r'[Cc]ertificate.*[Kk]eystore.*[Pp]assword.*:?\s*$',                                ANSWERS['keystore_pass'],     True),
    (r'[Kk]eystore.*credentials.*:?\s*$',                                                ANSWERS['keystore_pass'],     True),
    (r'[Pp]rivate.*[Kk]ey.*[Pp]assword.*:?\s*$',                                         ANSWERS['keystore_pass'],     True),
    (r'[Aa]pplication.*[Cc]ertificate.*[Pp]assword.*:?\s*$',                             ANSWERS['keystore_pass'],     True),
    # VOS/ADC connection IP (southbound)
    (r'(VOS|ADC|Southbound).*IP.*[Aa]ddress.*:?\s*$|connection IP.*:?\s*$',              ANSWERS['vos_ip'],            False),
    # Elastic FQDN
    (r'[Ee]lastic.*FQDN.*:?\s*$',                                                        ANSWERS['elastic_fqdn'],      False),
    # Elastic IP
    (r'[Ee]lastic.*IP.*:?\s*$',                                                          ANSWERS['elastic_ip'],        False),
    # Generic Y/N safety net (continue) — only at the very end of fallback
    # (placed last, so specific rules above match first)
]

# Patterns indicating completion
DONE_PATTERNS = [
    r'configuration.*complete',
    r'configure.*successful',
    r'\$\s*$',  # back to shell prompt
]

# Patterns indicating we need to break early (errors)
ERROR_PATTERNS = [
    r'fatal error',
    r'aborted',
    r'failed to (configure|generate|apply|start)',
]

def find_match(buf):
    """Search end of buffer (last 600 chars) for a known prompt regex."""
    tail = buf[-600:]
    for pat, response, hide in RULES:
        if re.search(pat, tail, re.IGNORECASE | re.MULTILINE):
            return pat, response, hide
    return None, None, None

def main():
    s = VmsSSH(HOST, USER, PASSWORD)
    chan = s.client.invoke_shell(term='xterm', width=200, height=50)
    chan.settimeout(2.0)

    log_dir = r'C:\Claude\vms_install\logs'
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(log_dir, f'configure_{ts}.log')
    log = open(log_path, 'w', encoding='utf-8')
    print(f"=== Logging full transcript to {log_path} ===\n")

    def emit(text):
        sys.stdout.write(text)
        sys.stdout.flush()
        log.write(text)
        log.flush()

    # consume initial banner
    time.sleep(2)
    while chan.recv_ready():
        d = chan.recv(65535).decode(errors='replace')
        emit(d)

    # Send vsh configure
    emit("\n[CMD] vsh configure\n")
    chan.send('vsh configure\n')

    buf = ''
    last_data = time.time()
    last_prompt = None
    DEADLINE = time.time() + 60 * 75  # 75 min cap
    no_data_break = 600  # 10 min stall = give up

    while time.time() < DEADLINE:
        if chan.recv_ready():
            d = chan.recv(65535).decode(errors='replace')
            buf += d
            emit(d)
            last_data = time.time()
            # detect completion
            tail = buf[-300:]
            if any(re.search(p, tail, re.I) for p in ['kubernetes initialization.*complete', 'all services running', 'completely configured', 'GoodBye']):
                # not necessarily done — wait a bit more
                pass
            # Try to match a prompt
            pat, response, hide = find_match(buf)
            if pat and pat != last_prompt:
                # Wait a moment to ensure prompt is fully there (input cursor settled)
                time.sleep(0.4)
                # drain any extra chars
                while chan.recv_ready():
                    extra = chan.recv(65535).decode(errors='replace')
                    buf += extra
                    emit(extra)
                # send the response
                if hide:
                    emit(f"\n[ANSWER: ({pat[:40]}...) → ********]\n")
                else:
                    emit(f"\n[ANSWER: ({pat[:40]}...) → {response!r}]\n")
                chan.send(response + '\n')
                last_prompt = pat
                last_data = time.time()
        else:
            # idle
            time.sleep(0.5)
            # If long no-data, see if we are at shell prompt = done
            if time.time() - last_data > 30:
                tail = buf[-200:]
                if re.search(r'\[admin@vms-1.*\]\s*\$\s*$', tail.strip()):
                    emit("\n[DONE — back at shell prompt]\n")
                    break
            if time.time() - last_data > no_data_break:
                emit(f"\n[STALL >{no_data_break}s — aborting]\n")
                break

    # Run vsh status as final check
    emit("\n[CMD] vsh status (final check)\n")
    chan.send('vsh status\n')
    time.sleep(5)
    end = time.time() + 60
    while time.time() < end:
        if chan.recv_ready():
            d = chan.recv(65535).decode(errors='replace')
            buf += d
            emit(d)
        else:
            time.sleep(0.5)

    chan.close()
    s.close()
    log.close()
    print(f"\n[Done. Log saved at {log_path}]")

if __name__ == '__main__':
    main()
