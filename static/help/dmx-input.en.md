# DMX Input (receive Art-Net and sACN)

OpenCue can not only send DMX but also **receive it over the network** – from a lighting desk, a program (for example a visualiser or a show controller) or a device. The received values can be **forwarded and mixed** into the output or used as **triggers**.

Open it with **Controls → DMX input…** (it can also be changed from a tablet).

---

## 1. Switching it on

- Switch **Receive DMX** on (off is the default – DMX has no password, anyone in the network can send).
- **Protocols:** Art-Net (UDP 6454) and/or sACN / E1.31 (UDP 5568, multicast). Art-Net universe = *port address* (exactly as OpenCue sends it: universe 1 = port address 1).
- **Allowed senders:** empty = anyone; otherwise IP addresses or their beginnings (e.g. `192.168.1.`).
- **Network adapter:** only needed if the computer has several and the input should listen on a specific one.
- **Source gone after:** that long without a packet, then OpenCue releases the source's values (sACN: immediately on "stream terminated").

**Sources seen** shows live everything that is being sent: protocol, universe, sender, packets per second and how many channels are not zero. **View** shows the 512 channels as a grid; **Forward** creates a mapping right away.

---

## 2. Forward / mix (source → output)

A **mapping** mixes an *input universe* into an *output universe* of OpenCue:

| Mode | Meaning |
|---|---|
| **Highest wins** (HTP) | Per channel the larger value of OpenCue and the input counts. The default, safe for mixing in. |
| **Replace** | The input counts while the source is there (zeros included). Optionally only for a channel range. |

- Several sources for the same universe: **highest wins**. With sACN only the sources with the highest **priority** count.
- If the output universe has **no fixtures** it is still output – that gives a **pure forwarding** (e.g. Art-Net → sACN or → a USB adapter).
- The input lies **above everything** (programmer, cues, effects). The values inside OpenCue stay unchanged; mixing happens only in the **output**.
- Own packets are recognised and ignored – a forwarding does not create a feedback loop.
- It runs in the **DMX output process**: the forwarding carries on unchanged even if the main program hangs. If that process fails and the output runs inside the main program as a fallback, triggers and the display keep working but mixing does not (the dialog says so).

---

## 3. Triggers (channel → command)

A **trigger** runs a command-line command when a channel changes:

- **Button:** when the value rises above the **threshold** the first command runs (e.g. `Go`); when it falls below again, the second (optional, e.g. `Blackout Off`).
- **Fader:** every new value runs as a command; `{value}` stands for the value scaled to the **range** (default 0–100), e.g. `Master {value}`.
- **Learn:** click **Learn** and move a channel at the desk – protocol, universe and channel are filled in.
- The first value seen is only remembered, nothing is triggered (no jump when connecting). Fader commands run at most 20 times a second; the last value always arrives.

Examples: channel 1 = `Go` (button), channel 2 = `Blackout` (button), channel 3 = `Master {value}` (fader), channel 10 = `Goto Cue 5`.

**Recent triggers** shows what was triggered.

---

## 4. Good to know

- The input belongs to the **app configuration** (not the show) and applies to this computer.
- For a desk to reach OpenCue it must send to the computer's IP address or by broadcast; the Windows firewall must allow UDP 6454 / 5568 for OpenCue – the dialog shows whether the rule exists and creates it with one click (Windows asks for permission on the main computer).
- **Announce as an Art-Net device:** OpenCue answers the search (ArtPoll) of other devices and shows up in their list of Art-Net devices – a desk can pick it as a target without typing the IP address.
- An overview of all inputs and outputs is in **Settings → Overview**.
