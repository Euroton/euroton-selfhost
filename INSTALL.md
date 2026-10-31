# Install

Euroton is alpha. [POST-INSTALL.md](POST-INSTALL.md) says what that means & covers outside mail, certificates, plans, branding & upgrades.

This takes a bare Debian 13 host to a running Euroton server. The measured run took 2 min 36 s for `provision.yml` & 14 min 7 s for `playbook.yml`, on an LXC container with 8 cores & 16 GB of RAM. It used 5.8 GB of disk afterwards. Those 16 GB are what was tested, not a proven minimum: the client builds set an 8 GB Node heap, so don't start below that.

You need 2 machines. The **host** runs Euroton. The **control machine** runs Ansible & keeps the generated secrets.

## 1. Prepare the host

Install Debian 13 with `root` SSH access from the control machine by key. Every package the install needs comes after this, except what Ansible itself needs:

```sh
apt install openssh-server python3
```

In a Proxmox LXC, turn on `nesting=1,keyctl=1`, because Postgres runs in Docker. Don't put this host on the public internet yet; sign-up is open by default. See [After the install](#after-the-install).

## 2. Prepare the control machine

You need `git`, `openssl` & Ansible. The run above used ansible-core 2.21 with no extra collections.

```sh
pipx install ansible-core
git clone https://github.com/Euroton/euroton-selfhost.git
cd euroton-selfhost/ansible
cp inventory.example inventory.yml
cp group_vars/all.example.yml group_vars/all.yml
```

Put the host's address in `inventory.yml` at `ansible_host`. `group_vars/all.yml` works as it is, with the domain `euroton.internal`. Change `domain` now if you want another one, because addresses created at sign-up keep the suffix they got.

## 3. Run the playbooks

```sh
ansible-playbook -i inventory.yml provision.yml
ansible-playbook -i inventory.yml playbook.yml
```

The first installs Node, Docker & Caddy, clones the sources at their pinned tags & starts Postgres. The second builds Mail, Account & Calendar, then starts the services. Both end with `failed=0` in the recap. If one stops on a failed download, run it again; re-running is safe.

Secrets land in `files/secrets/` & the certificates in `files/ssl/`, both on the control machine. `files/ssl/` holds the CA private key, so back up both folders & don't commit them.

## 4. Point your hostnames at the host

On each computer that will use Euroton, add this to `/etc/hosts`, or to your LAN's DNS, with the host's address:

```
192.0.2.10 mail.euroton.internal account.euroton.internal calendar.euroton.internal mail-api.euroton.internal account-api.euroton.internal godmode.euroton.internal
```

## 5. Trust the CA

Copy `files/ssl/euroton-ca.crt` to each of those computers. Don't copy anything else from that folder.

Chromium on Linux:

```sh
certutil -d sql:$HOME/.pki/nssdb -A -t "CT,," -n euroton-ca -i euroton-ca.crt
```

Firefox: Settings, Privacy & Security, Certificates, View Certificates, Authorities, Import.

Restart the browser. Clicking through the warning instead breaks sign-up, because its hidden frames load from `account-api.euroton.internal` & browsers show no warning for a frame.

## 6. Create accounts & send mail

1. Open `https://account.euroton.internal/mail/signup` & create an account.
2. Sign out, then create a second account the same way.
3. Send a message from one to the other at `https://mail.euroton.internal`.
4. Open `https://calendar.euroton.internal` & save an event.

## 7. Open the admin UI

Open `https://godmode.euroton.internal`. It asks for the token in `files/secrets/operator_token` on the control machine. Caddy answers 403 to any address outside private ranges.

That token is root on the database: the SQL console can run shell commands inside the Postgres container through `COPY ... PROGRAM`. Don't widen `operator_allowed` to the internet.

## After the install

A reboot brings everything back. Check with:

```sh
systemctl is-active caddy euroton-server godmode-dev
```

Before this host faces the internet, set `SIGNUP_ENABLED=false` in `/etc/euroton/server.env` & restart `euroton-server`. With it off, only organization invites can create accounts. A re-run of `playbook.yml` rewrites that file, so make the change again afterwards.

[ansible/README.md](ansible/README.md) covers logs, upgrades & token rotation. Outside mail is off & has never moved a real message, so this install moves mail between accounts on the same server only.

The audit that ran before release was partial, and its open items are listed in `SECURITY.md`.
