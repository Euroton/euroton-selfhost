// Turns the prebuilt clients into this install's clients: its SRP public key &
// its domain. A rebuild would take 12 minutes; this takes seconds. The key sits
// in several chunks, each chunk's hash sits in the runtime chunk, & the runtime
// chunk's hash sits in index.html, so hashes are recomputed until nothing moves.
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const [src, dest, bakedDomain, domain, bakedKeyFile, keyFile] = process.argv.slice(2);
const stamp = createHash('sha256').update(fs.readFileSync(keyFile)).update(domain).digest('hex');
const stampFile = path.join(dest, '.patched');
if (fs.existsSync(stampFile) && fs.readFileSync(stampFile, 'utf8') === stamp) process.exit(0);

const readKey = (file) => fs.readFileSync(file, 'utf8').trim().replace(/\r\n/g, '\n');
const bakedKey = readKey(bakedKeyFile);
const key = readKey(keyFile);
// Bundles hold the key as a template literal, some with \n escapes.
const escape = (armored) => armored.replace(/\n/g, '\\n');
if (key.length < 100 || !key.includes('BEGIN PGP PUBLIC KEY')) throw new Error(`no public key in ${keyFile}`);

// dest is a mounted volume, so only its contents can go.
for (const entry of fs.readdirSync(dest)) fs.rmSync(path.join(dest, entry), { recursive: true, force: true });
fs.cpSync(src, dest, { recursive: true });

const isText = (f) => /\.(js|html|json|css|webmanifest|xml|txt)$/.test(f);
const walk = (d) => fs.readdirSync(d, { withFileTypes: true })
    .flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));

for (const app of fs.readdirSync(dest, { withFileTypes: true }).filter((e) => e.isDirectory())) {
    const files = walk(path.join(dest, app.name)).filter(isText);
    const body = new Map(files.map((f) => [f, fs.readFileSync(f, 'utf8')]));
    const integrity = (text) => createHash('sha384').update(text).digest('base64');
    const before = new Map();
    let keyFiles = 0;
    for (const [f, text] of body) {
        before.set(f, integrity(text));
        let next = text.replaceAll(bakedKey, key).replaceAll(escape(bakedKey), escape(key));
        if (next !== text) keyFiles += 1;
        if (domain !== bakedDomain) next = next.replaceAll(bakedDomain, domain);
        body.set(f, next);
    }
    if (app.name !== 'godmode' && keyFiles === 0) throw new Error(`baked SRP key not found in ${app.name}`);
    for (let changed = true, round = 0; changed; round += 1) {
        if (round > 5) throw new Error(`integrity hashes in ${app.name} didn't settle`);
        changed = false;
        for (const [f, oldHash] of before) {
            const newHash = integrity(body.get(f));
            if (newHash === oldHash) continue;
            before.set(f, newHash);
            for (const [g, text] of body) {
                if (text.includes(oldHash)) {
                    body.set(g, text.replaceAll(oldHash, newHash));
                    changed = true;
                }
            }
        }
    }
    for (const [f, text] of body) fs.writeFileSync(f, text);
    console.log(`${app.name}: key in ${keyFiles} files`);
}
fs.writeFileSync(stampFile, stamp);
