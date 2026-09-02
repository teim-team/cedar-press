#!/usr/bin/env node
/**
 * Generate the value of `VITE_PRESS_DEMO_ACCOUNTS` for one preview account.
 *
 *     node scripts/press-demo-account.mjs reviewer@example.org press_pro
 *
 * It asks for the password on stdin and prints the JSON to paste into the
 * repository secret. The password is not echoed as it is typed, is never
 * printed back, is never passed as an argument (which would put it in the
 * shell history and in every process listing) and is never written to a
 * file. What comes out is an email, a random salt and a SHA-256 digest.
 *
 * The digest is computed by `hashPressDemoPassword`, imported rather than
 * reimplemented, so this generator and the check the browser runs cannot
 * drift apart. Read that module before using this one: the gate it feeds is a
 * demonstration gate, and the password issued here must be one used for the
 * preview and nowhere else.
 */
import { randomBytes } from "node:crypto";
import { argv, exit, stdin, stdout } from "node:process";
import { createInterface } from "node:readline/promises";
import { Writable } from "node:stream";

import { hashPressDemoPassword } from "../src/features/grove/pressDemoGate.js";

const [email, tier = "press_pro"] = argv.slice(2);

if (!email || !email.includes("@")) {
  stdout.write("usage: node scripts/press-demo-account.mjs <email> [press|press_pro]\n");
  exit(2);
}
if (tier !== "press" && tier !== "press_pro") {
  stdout.write(`unknown tier "${tier}": expected press or press_pro\n`);
  exit(2);
}

// The prompt is written through, the typing is swallowed. Without this
// readline echoes each character to the terminal, which puts the password on
// the operator's screen and into any terminal recording running over it.
let echo = true;
const muted = new Writable({
  write(chunk, encoding, done) {
    if (echo) stdout.write(chunk, encoding);
    done();
  },
});

const rl = createInterface({ input: stdin, output: muted, terminal: true });
const answer = rl.question(`Password for ${email} (not shown as you type): `);
echo = false;
const password = await answer;
echo = true;
rl.close();
stdout.write("\n");

if (password.length < 12) {
  stdout.write("Refused: use at least 12 characters. This digest ships in a public bundle.\n");
  exit(1);
}

const salt = randomBytes(16).toString("hex");
const value = JSON.stringify({
  [email.trim().toLowerCase()]: {
    salt,
    hash: await hashPressDemoPassword(salt, password),
    tier,
  },
});

stdout.write(`VITE_PRESS_DEMO_ACCOUNTS=${value}\n`);
