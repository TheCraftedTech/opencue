# Remote Control (Tablet and Phone)

With **remote control** you operate OpenCue from an iPad, tablet, phone or any other computer in the **same network** – while the console computer keeps running the show and sending the DMX. Walk through the room and adjust lights, trigger cues from the stage, or use a tablet as a second screen.

Remote control is **off by default**. As long as it is off, OpenCue is not reachable from the network at all (the port is really closed, not just password-protected).

---

## 1. The idea in one minute

- The **console** is the computer where OpenCue is installed and running. It does all the work: it holds the show, calculates the cues and sends DMX.
- A **remote device** is just a browser. It opens a web address of the console, logs in with the password and shows **the same OpenCue interface** – same toolbar, same panels, same rights.
- Everything stays in sync live: when you select a fixture, move a fader or press *Go* on one device, all others show it immediately.
- No internet is needed. Everything happens inside your local network.

---

## 2. Switching it on

1. On the console open **Settings** (toolbar) → category **Remote**.
2. Turn on **Allow access from the network**.
3. Set a **password** (at least 4 characters). Use *Show* to check what you typed.
4. Optionally change the **port** (1024–65535, default 8000). A changed port takes effect after restarting OpenCue.
5. Click **Save & Apply**. No restart is needed.

OpenCue now listens on every network address of the console. The page shows:

| Item | Meaning |
|---|---|
| **Status** | “Reachable on the network” or “Local only”. |
| **Addresses** | Every address under which the console can be reached, each with a **Copy** button. |
| **QR code** | For the selected address – scan it with the camera of an iPad or phone. The password is asked when connecting. |
| **Detect addresses again** | After you changed Wi-Fi or plugged in a cable. |

When you switch it off again, the listeners are closed again, immediately.

> **Windows firewall:** when remote access is switched on for the first time, Windows may ask whether OpenCue may communicate on the network. Allow it for your **private** network; otherwise other devices cannot connect.

---

## 3. Connecting a device

1. Make sure the device is in the **same network** (same Wi-Fi or LAN) as the console.
2. Open the address from the settings page in the device's browser – for example `http://192.168.1.20:8000/` – or scan the QR code. The address redirects to the remote page `/remote/`.
3. Enter the password and tap **Sign in**.

**Save password** (checkbox on the login page) stores the password in the browser of **that device only** and pre-fills the field next time. There is no automatic login – you still tap *Sign in*. Untick the box to delete the stored password immediately.

**Wrong password:** repeated wrong attempts lock the device out for a while (brute-force protection).

**Sign out:** *File → Sign out* (only shown on remote devices).

If nothing connects: check that both devices are in the same network (guest Wi-Fi networks often separate devices from each other), that the address matches the one on the settings page, and the firewall (see above).

---

## 4. What a remote device can do

- **Everything the console can do.** After logging in, a remote device has the same rights: programming, cues, effects, files, settings, DMX settings and remote settings. That includes things with consequences – switching off remote access (which locks that device out) or **quitting OpenCue**, which stops the program for everybody. Use a password that only people you trust know.
- **Own layout per device.** Each device remembers which layout it used and can show a different one than the console. Build a layout for the tablet with big buttons (see below). If one device saves a layout that another device currently shows, the other one takes it over – or, if it has unsaved changes of its own, offers *Apply* or *Keep my version*.
- **Own per device:** only **fullscreen** (each browser's own) and the **GUI scale**.
- **Data stays on the console.** Saving and loading always go through the console; shows, layouts and fixtures live on the console computer.

### Who is connected?

A toolbar icon shows **how many remote devices are connected**. Click it to see IP address, device and connection time of each – and to **disconnect** (*Kick*) a device. A disconnected device sees a notice and must reload the page to log in again.

---

## 5. Install as an app (iPad / iPhone / Android)

The remote page is a **web app**. On the device you can add it to the home screen:

- **iPad / iPhone (Safari):** Share button → **Add to Home Screen**.
- **Android (Chrome):** menu → **Install app** / **Add to Home screen**.

It then opens full-screen without browser bars, with the colours of your current theme.

**Limitation:** installable web apps and the offline page need a secure connection (HTTPS). OpenCue is reached over plain `http://` in your local network, so the home-screen app works, but there is no offline page and the device must reach the console to show anything.

---

## 6. Tips for a good tablet layout

- Create a **separate layout** for the tablet (*Edit → Manage Layouts…*): large **Executor**, **Cue List**, a few **Button** or **Fader** panels and the **Fixture Control** category you need most. Remote devices load their own layout, so the console layout stays as it is.
- For touch use the panels **Command Numpad** and **Command Buttons** instead of typing on the screen keyboard.
- Increase the **GUI scale** on the tablet (`Ctrl +` or *View → GUI Scale…*) – it applies to that device only.
- Layouts can be switched by **swiping** horizontally if *Settings → General → Switch layouts by swiping* is on (per device).
- Cue lists with timecode triggers keep running on the console even if a device disconnects – the show does not depend on the tablet.

---

## 7. Safety and good practice

- Use remote control only in networks you trust (your own router, a dedicated show network). The connection is **not encrypted** (plain HTTP); anyone in the network could read the traffic.
- Choose a password you do not use elsewhere – it is stored in the app configuration on the console and, if you tick *Save password*, in the browser of that device.
- Switch remote off when you do not need it.
- DMX output always runs on the console – even if all remote devices disconnect, the lights stay as they are.
