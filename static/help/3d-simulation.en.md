# 3D Simulation

The panel **3D Simulation** shows your stage in 3D with every fixture lit live from the DMX values. Add it with **Add Panel**. This guide explains the buttons, the settings in **Room & light** and what to check when the picture is not as expected (not every fixture lights the stage, cones or shadows are missing, it is slow).

---

## 1. The panel

- Three modes at the top left: **View**, **Build** (objects and 3D models) and **Fixtures** (place fixtures, aim moving heads).
- Buttons at the top right: VR headset (only if the browser offers one), share the camera between devices, **Room & light** (gear icon), **Stop / Start 3D simulation**, **Blackout** (light bulb), **Reset view**, **Fullscreen**.
- Bottom left: the quality button shows the frame rate and the resolution; a click switches Auto → Low → Medium → High.

## 2. Stop and start the 3D simulation

The pause button stops the simulation completely: the scene, the graphics context and the models are removed, nothing is calculated or drawn and the rest of OpenCue is not slowed down. The panel stays in your layout and shows a play button; **Start** builds everything again. The choice is remembered **per device** and applies to all 3D panels on that device. If a 3D panel is empty and says that it is stopped, press the play button.

After starting, after loading a big show or after changing the light limits the panel shows *Preparing lighting …* for a moment: the graphics card prepares its programs in the background and the rest of OpenCue stays usable.

## 3. Room & light

Open the dialog with the gear icon. It has two parts.

**For all devices** – shared by every device connected to the show (console, iPad, remote access): *Lighting* (work light in Build mode, house light), *Bounced light* (room light, wall reflection, colour bleeding), *Image* (object reflection, exposure, **Haze**) and *Grid and axes in View*. **Haze at 0 %** switches the haze off completely: no light cones and no haze calculation – this saves the most performance.

**This device only** – performance and quality. They are stored on this device only, every device can choose differently:

| Setting | Meaning |
|---|---|
| **Quality** | Auto (adapts to the frame rate), Low, Medium, High: resolution and shadow detail. |
| **Max. lights** | How many fixtures get their own light on the surfaces at the same time (default 32). The brightest fixtures win. |
| **Max. shadows** | How many of these lights cast shadows. 0 = as many as the graphics card allows. |
| **Max. mirror beams** | Reflections on metal and mirrors. |
| **Max. simple light cones** | How many simple light cones are drawn. 0 = all. With a limit every fixture keeps its first cone first, then the brightest ones. |
| **Max. frame rate** | Limits how often the picture is redrawn per second (for example 30). 0 = unlimited. |
| **Fixtures cast shadows** | The fixture housings cast shadows into the light cones (on by default). |

The line below the settings shows what applies right now (lights, shadows, fixtures placed) and what the graphics card allows. **Reset limits** restores the defaults.

## 4. When the picture is not as expected

- **Not every fixture lights the stage, some fixtures have no shadow, only some show a gobo.** This is caused by the limits of this device. Only the brightest *Max. lights* fixtures (default 32) light the surfaces, only *Max. shadows* of them cast shadows (the graphics card sets an upper limit, shown in the info line), and a gobo or prism pattern is shown on the first **3** such lights; the others show open light. Raise *Max. lights* and *Max. shadows* (0 = as many as possible) if you want everything shown – with many fixtures the picture then becomes slower or lags a little.
- **A fixture is lit but its cone is missing.** Check **Haze** (0 % = no cones), *Max. simple light cones*, Blackout, the Grand Master, the dimmer of the fixture and that the 3D simulation is not stopped.
- **The picture is dark.** The work light only exists in Build mode; check the *Exposure* slider, Blackout and the Grand Master.
- **The 3D simulation is slow.** Try, in this order: Haze 0 % (if you do not need haze), a lower *Max. lights* / *Max. shadows*, *Max. simple light cones* (for example 200), switch *Fixtures cast shadows* off, quality Low or Auto, a *Max. frame rate* of 30, or stop the 3D simulation while you do not need it. Stages with 100 or more fixtures lit at once are demanding; with up to about 16 fixtures lit at the same time the defaults are fine.
- **A fixture does not move in 3D.** Its fixture type needs a 3D model with a moving yoke / head and Pan / Tilt channels; types without them (LED panels, bars, blinders) stay still. The fixture must also be placed on the stage (Fixtures mode → *Place all*).
- **A light cone points the wrong way.** OpenCue turns the direction automatically when a GDTF file lets the beam point into the housing. If a fixture type is still wrong, note its name and tell the developer.
