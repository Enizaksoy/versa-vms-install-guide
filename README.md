# Versa VMS 5.2.2 — End-to-End Lab Install Guide

End-to-end install runbook for **Versa Messaging Service (VMS) 5.2.2** in a single-node lab,
integrated with **Versa Director**, a **VOS branch (FlexVNF)**, the **WMI Agent**, and **Active Directory**
to deliver passive user-IP authentication.

**Live guide:** https://enizaksoy.github.io/versa-vms-install-guide/

## What's covered

- Pre-flight: ESXi sizing, disk expand, network plan (Northbound/Southbound, Elastic VIP), DNS/NTP
- VMS install: OVA boot, password change (19-char policy), DB cert, server CSR, AD CS web enrollment, `import-certs.sh`, pre-upgrade patch, `vsh configure` (Pass 1/2/3)
- Cert workaround for the message-server pod (internal CA chain rebuild)
- Director: VMS Connector wizard, branch service profile, tag-value mapping
- VOS branch (A-P-HA1): VERSA-Control-VR routing instance, gRPC over overlay, Connected state
- WMI Agent v11.4.11 install + AD config + sample event flow
- Verification: `eniz@mylab.com` → `192.168.30.254` mapping live on the branch
- Issues hit during the install and how each was fixed (CockroachDB clock skew, message-server CrashLoopBackOff, Director "Cannot reach VMS at IP", Branch "Connecting" indefinitely, etc.)

## Repo layout

```
.
├── index.html             # The full HTML guide (rendered on GitHub Pages)
├── scripts/               # 40+ Python automation scripts (paramiko-based)
│   ├── lib_ssh.py         # Robust SSH/sudo helper with single-quote escaping
│   ├── 02_set_network.py
│   ├── 05_grow_filesystem.py
│   ├── 06_change_password_v2.py
│   ├── 19_dns_ntp.py
│   ├── 24_generate_server_csr.py
│   ├── 25_submit_to_adcs.py
│   ├── 27_run_imports.py
│   ├── 33_apply_patch.py
│   ├── 36_vsh_configure_v4.py
│   ├── 37_vsh_configure_v5.py
│   ├── 40_internal_cert_gen.py
│   ├── 41_sign_server_with_local_ca.py
│   ├── 43_reset_cockroach_db.py
│   └── ...
└── README.md
```

## Credentials in scripts

All real passwords have been replaced with placeholders. Before running, set your own values:

| Placeholder            | What it is                                             |
|------------------------|--------------------------------------------------------|
| `<vms-admin-pass>`     | VMS `admin` (and `versa`) user password                |
| `<default-ova-pass>`   | Initial Versa OVA default password (vendor-shipped)    |
| `<old-admin-pass>`     | First post-OVA admin password (replaced by stronger)   |
| `<keystore-pass>`      | DB cert keystore password                              |
| `<ad-admin-pass>`      | AD CS web enrollment password (Domain Admin)           |

## Requirements

- Python 3.9+
- `paramiko`, `requests`, `requests-ntlm`
- VMS 5.2.2 OVA + `vms_5.2.2_pre_upgrade_patch.bin` from the Versa support portal
- ESXi 7.0+ host
- Reachable Versa Director and a VOS branch
- Active Directory + AD CS (for cert enrollment)
- Windows Server 2022 for the WMI Agent (4 vCPU, 16 GB)

## Disclaimer

This is a **lab runbook** built during a 2026-05 install.
Not an official Versa Networks document. Use at your own risk in production.
Always cross-check the official Versa documentation portal for your release.
