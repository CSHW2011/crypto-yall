# Troubleshooting Guide (For Non-Technical Users)

Things sometimes go wrong. Here's how to handle the common ones without panicking.

---

## Step 1: When Something Looks Wrong, Don't Touch Anything

Before doing anything else:

1. Take a deep breath. Most issues self-resolve on the next scheduled run.
2. Read this guide to identify what's happening.
3. If you can't figure it out in 5 minutes, **pause all the bots** (see QUICKSTART) and email Brendan.

Avoid:
- Trying random fixes
- Manually editing things in GitHub or Gists
- Closing positions out of panic before checking what's happening

---

## Common Issue 1: "I Stopped Getting Trade Alerts"

### Possible cause A: The market is quiet

This is actually the most common reason. The bots only send alerts when:
- A signal changes (BUY, SELL, etc.)
- A trade actually executes

In a flat, sideways market, this can be hours or days. **Quiet alerts = quiet market.** This is normal.

### How to verify

1. Open the dashboard: https://crypto-yall-8s3evlspcczux5ztdmat9e.streamlit.app/
2. Look at the "Last Run" timestamp on each bot section.
   - Daily bot should show within 24 hours
   - Intraday bot should show within 2 hours
   - Aggressive bot should show within 1 hour

If those timestamps look fresh, the bots are running fine — there's just nothing to alert on.

### Possible cause B: A bot is paused

Did someone (or you) accidentally flip a kill switch to OFF?

1. Go to https://github.com/aicodepathways/crypto-yall/settings/variables/actions
2. Check `KILL_SWITCH`, `INTRADAY_KILL_SWITCH`, `AGGRESSIVE_KILL_SWITCH`
3. Any showing "OFF" = that bot is paused

### Possible cause C: Email going to spam

Open your spam folder. Look for emails from `nocodepathways@gmail.com` with subject `[Crypto Y'all]`. Mark as "not spam."

### Possible cause D: Telegram bot got blocked

1. Open Telegram, search for `@Crypto_yall_bot`
2. If you see "Bot blocked," tap it and unblock
3. Send the bot a message

### Possible cause E: GitHub Actions stopped running

This is rare but possible if the repo got disabled or hit limits.

1. Go to https://github.com/aicodepathways/crypto-yall/actions
2. Look at "Execute Aggressive" workflow
3. The most recent run should be within the last hour (since it runs every 30 minutes)
4. If the most recent run was more than 6 hours ago → contact Brendan

---

## Common Issue 2: "I Got an Error Email"

### Error: "Daily drawdown triggered — halting today"

**What it means:** The bot lost more than 5% (or 3% for aggressive) in a single day and auto-paused itself for the rest of the day. This is the safety net working correctly.

**What to do:** Nothing. The bot will automatically resume the next calendar day.

**When to worry:** If this happens 3+ days in a row, the strategy is misaligned with market conditions. Email Brendan.

### Error: "API Wallet does not exist"

**What it means:** Hyperliquid is rejecting the bot's authentication. Usually because:
- The API wallet was de-authorized on Hyperliquid
- The bot is pointed at testnet but the wallet was only authorized on mainnet (or vice versa)
- The private key got rotated

**What to do:**
1. Pause all bots (see QUICKSTART)
2. Email Brendan
3. Don't try to "re-authorize" the wallet yourself — let him handle it

### Error: "Insufficient balance"

**What it means:** The Hyperliquid account doesn't have enough margin to open the position.

**What to do:**
1. Open https://app.hyperliquid.xyz
2. Check the account balance
3. If it's drained, that's a bigger problem — pause all bots, email Brendan immediately

### Error: "CLIENT INIT FAILED"

**What it means:** The bot couldn't even connect to Hyperliquid. Usually a temporary network issue.

**What to do:** Wait for the next scheduled run. If it fails 3 runs in a row, email Brendan.

### Error: "Telegram error: 400" or "401"

**What it means:** Telegram rejected the message. Usually:
- A user blocked the bot
- A chat ID is invalid

**What to do:** Email alerts will still work. Brendan can investigate Telegram separately when he's back.

### Error: "Email sent to []" (empty recipient list)

**What it means:** The `NOTIFY_EMAILS` secret is empty or got reset.

**What to do:** Email Brendan to re-add recipients.

---

## Common Issue 3: "The Dashboard Shows No Data"

### The "Live Trading" sections are missing

**Likely cause:** Streamlit Cloud secrets are not configured.

**What to do:**

1. Open https://share.streamlit.io/
2. Find the Crypto Yall app
3. Click the ⋮ menu → Settings → Secrets
4. The secrets should contain four lines:
   ```toml
   GIST_TOKEN = "ghp_..."
   TRADING_GIST_ID = "d35732f9c123e95a4dc13a51855d21de"
   INTRADAY_GIST_ID = "02cbe06fb1c4eb8afb5fad321aa3a251"
   AGGRESSIVE_GIST_ID = "0917280713a7781dc72a984147eef295"
   ```
5. If they're missing or empty, contact Brendan to re-add them

### The dashboard shows positions but they're stale

**Likely cause:** Streamlit cached the data for 60 seconds. Just wait or refresh.

If still stale after 5 minutes:
1. Click the ⋮ menu (top right of the dashboard)
2. Click "Rerun"
3. Or click "Reboot app" if it's really stuck

### The dashboard won't load at all

**Likely cause:** Streamlit Cloud puts apps to sleep after extended inactivity.

**What to do:**
1. First visit might take 30 seconds to wake up — be patient
2. If it shows an error after 60 seconds, click the menu and "Reboot app"
3. If still broken after that, email Brendan

---

## Common Issue 4: "The Bot Opened a Position But Hyperliquid Shows Nothing"

**Cause:** All three bots share the same Hyperliquid account. If Daily bot opened ETH long ($300 worth) and Aggressive bot opened ETH short ($100 worth), Hyperliquid sees a single net position of $200 long.

This is a known limitation of the shared-account architecture. Hyperliquid sub-accounts would fix it, but they require $100,000+ in mainnet trading volume to unlock, so most users can't use them. The code-level ownership tracking still keeps each bot managing only its own positions safely.

**What to do:** Nothing urgent. The dashboards will still show each bot's intended position correctly. The actual exchange shows the net. Email Brendan if it gets confusing.

---

## Common Issue 5: "I Want to Stop the Bots Right Now"

### Most urgent emergency procedure:

**Step 1:** Pause all bots via kill switches (takes 30 seconds via GitHub web UI):

1. Go to https://github.com/aicodepathways/crypto-yall/settings/variables/actions
2. Set all three to OFF:
   - `KILL_SWITCH` → OFF
   - `INTRADAY_KILL_SWITCH` → OFF
   - `AGGRESSIVE_KILL_SWITCH` → OFF

**Step 2:** If you want to close existing positions:

1. Open https://app.hyperliquid.xyz
2. Connect Josh's wallet
3. For each open position, click "Close Market"

**Step 3:** Email Brendan so he knows you intervened.

---

## Common Issue 6: "The Bot Made a Trade I Don't Understand"

The alerts include a "Reason" field that explains why the bot did what it did. Common reasons:

- **"Sync to hold_long"** = Bot's records show no position, but strategy says it should be long. So it opened a long to match.
- **"SELL / EXIT signal"** = Oscillator crossed zero from above, exit the long.
- **"LIQUIDATE TO CASH signal"** = HMM detected Bear regime, move to cash (Daily bot only).
- **"ENTER SHORT signal"** = Oscillator crossed down from overbought.
- **"pyramid add #1"** = Aggressive bot adding to an existing winner.
- **"BUY signal"** = Fresh entry, oscillator crossed up from oversold.

If a trade really doesn't make sense to you, screenshot it and send to Brendan. He can dig into the data.

---

## Common Issue 7: "I Accidentally Changed Something in GitHub"

### If you accidentally edited a variable:

1. The variable history is visible at https://github.com/aicodepathways/crypto-yall/settings/variables/actions
2. Edit it back to the previous value
3. The bot will pick up the change on the next scheduled run

### If you accidentally edited a secret:

Secrets don't show their old values for security. You'll need to email Brendan to restore the original.

### If you accidentally pushed code changes:

You probably can't — the repo settings should prevent that. But if you did:

1. **Pause all bots immediately**
2. Email Brendan
3. Don't try to "undo" — let him roll it back properly

---

## When to Definitely Contact Brendan

Email `nocodepathways@gmail.com` for:

- 3+ consecutive error alerts of the same kind
- "Insufficient balance" or "API wallet does not exist" errors
- Major market events that you want input on
- Anything you don't understand
- Wanting to make changes beyond what's covered in QUICKSTART.md
- A new community member wanting to be added (see ADDING_COMMUNITY_USERS.md first)
- A discussion about going to mainnet (see MAINNET_LAUNCH.md first)
- Anything legal or regulatory (you probably shouldn't be making those decisions alone)

---

## The "I'm Panicking" Protocol

1. **Stop and breathe.** Nothing the bots do in 5 minutes will be catastrophic with the position sizes you're running.
2. **Pause all bots.** Three clicks (see Common Issue 5).
3. **Check Hyperliquid** for open positions. Note what's there.
4. **Email Brendan** with a summary of what's happening.
5. **Do NOT** start making changes to fix things until you've heard back.

The kill switch is your friend. Use it generously when in doubt.

---

## Diagnostic Checklist Before Emailing Brendan

When you do contact Brendan, having this info ready helps a lot:

- What time did the problem start?
- Which bot is affected (Daily / Intraday / Aggressive)?
- Did you get an error email? Forward it.
- Can you reproduce it? (Or is it just one event?)
- What does the dashboard show?
- What does Hyperliquid show (positions and balance)?
- What did you try, if anything?

Send all of that in one email so he doesn't have to ask follow-ups.
