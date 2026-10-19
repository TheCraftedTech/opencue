/* Gemeinsame SVG-Symbole der Oberflaeche (immer SVG, nie Emoji/Unicode-Symbole: sehen auf jedem Geraet gleich aus).
 * Nutzung: Icons.svg("play") liefert ein <svg class="ico">-Element (Farbe = currentColor, Groesse = 1em);
 * Icons.markup("play") dasselbe als Zeichenkette fuer statisches HTML. Die Pfade sind feste, eigene Zeichenketten. */
const Icons = (() => {
  // Linien-Symbole (24x24, Strich) - "fill": true = gefuellte Form
  const PATHS = {
    "chevron-down": '<path d="M6 9l6 6 6-6"/>',
    "chevron-up": '<path d="M6 15l6-6 6 6"/>',
    "chevron-left": '<path d="M15 6l-6 6 6 6"/>',
    "chevron-right": '<path d="M9 6l6 6-6 6"/>',
    "arrow-up": '<path d="M12 19V5M5 12l7-7 7 7"/>',
    "arrow-left": '<path d="M19 12H5M12 5l-7 7 7 7"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    close: '<path d="M6 6l12 12M18 6L6 18"/>',
    star: { fill: true, d: '<path d="M12 3.2l2.7 5.6 6.1.8-4.5 4.2 1.1 6.1L12 17l-5.4 2.9 1.1-6.1-4.5-4.2 6.1-.8z"/>' },
    play: { fill: true, d: '<path d="M7 4.5v15l12.5-7.5z"/>' },
    "play-reverse": { fill: true, d: '<path d="M17 4.5v15L4.5 12z"/>' },
    pause: { fill: true, d: '<rect x="6" y="4.5" width="4" height="15" rx="1"/><rect x="14" y="4.5" width="4" height="15" rx="1"/>' },
    stop: { fill: true, d: '<rect x="5.5" y="5.5" width="13" height="13" rx="1.5"/>' },
    "skip-start": { fill: true, d: '<rect x="4.5" y="5" width="2.6" height="14" rx="1"/><path d="M19.5 5v14L8.5 12z"/>' },
    "step-back": { fill: true, d: '<path d="M18 5v14L8 12z"/><rect x="5" y="5" width="2.6" height="14" rx="1"/>' },
    "step-forward": { fill: true, d: '<path d="M6 5v14l10-7z"/><rect x="16.4" y="5" width="2.6" height="14" rx="1"/>' },
    volume: '<path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5z" fill="currentColor"/><path d="M15.5 9a4 4 0 010 6M17.8 6.5a7.5 7.5 0 010 11"/>',
    "volume-off": '<path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5z" fill="currentColor"/><path d="M16 9.5l5 5M21 9.5l-5 5"/>',
    expand: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
    collapse: '<path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"/>',
    upload: '<path d="M12 16V4M7 9l5-5 5 5M5 20h14"/>',
    trash: '<path d="M5 7h14M9 7V4.5h6V7M7 7l1 13h8l1-13"/>',
    film: '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M3.5 9h17M3.5 15h17M8 4.5v15M16 4.5v15"/>',
    music: '<path d="M9 18V6l10-2v12"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="16.5" cy="16" r="2.5"/>',
    clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3.5 2"/>',
    loop: '<path d="M4 12a5 5 0 015-5h9M15 4l3 3-3 3M20 12a5 5 0 01-5 5H6M9 20l-3-3 3-3"/>',
    link: '<path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1"/>',
    folder: '<path d="M3.5 7a1.5 1.5 0 011.5-1.5h4l2 2.5h7.5A1.5 1.5 0 0120 9.5V17a1.5 1.5 0 01-1.5 1.5H5A1.5 1.5 0 013.5 17z"/>',
    camera: '<rect x="3" y="7" width="12.5" height="10" rx="2"/><path d="M15.5 11l5.5-3v8l-5.5-3z"/>',
    alert: '<path d="M12 4l9 16H3z"/><path d="M12 10v4.5M12 17.5v.01"/>',
    drop: '<path d="M12 3.5c3.4 4.1 6.2 7.2 6.2 10.4a6.2 6.2 0 01-12.4 0c0-3.2 2.8-6.3 6.2-10.4z"/><path d="M9 14.6a3.2 3.2 0 003.1 2.5"/>',
    refresh: '<path d="M20 5.5V10h-4.5M4 18.5V14h4.5"/><path d="M6.2 9.5A7 7 0 0118.6 10M17.8 14.5A7 7 0 015.4 14"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    "arrow-up": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "arrow-down": '<path d="M12 5v14M6 13l6 6 6-6"/>',
    "chevron-right": '<path d="M9 6l6 6-6 6"/>',
    "chevron-down": '<path d="M6 9l6 6 6-6"/>',
    edit: '<path d="M4 20l1-4L16 5l3 3L8 19z"/><path d="M14 7l3 3"/>',
    search: '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
    grid: '<rect x="4" y="4" width="6.5" height="6.5" rx="1.2"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.2"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1.2"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.2"/>',
    panel: '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M3.5 9h17"/>',
    dmx: '<path d="M4 20h16M6.5 20v-6M10.5 20V8M14.5 20v-9M18.5 20V5"/>',
    fixtures: '<path d="M7 4h10l2 8H5z"/><path d="M12 12v4M8 20h8M12 16v4"/>',
    programmer: '<path d="M8 8l-4 4 4 4M16 8l4 4-4 4M13.5 5l-3 14"/>',
    presets: '<path d="M7 4h10v16l-5-4-5 4z"/>',
    fx: '<path d="M3 12c2-6 4-6 6 0s4 6 6 0 4-6 6 0"/>',
    cuelist: '<path d="M9 6h11M9 12h11M9 18h11"/><path d="M4.5 6v.01M4.5 12v.01M4.5 18v.01"/>',
    executor: '<path d="M12 4v9"/><rect x="9" y="6.5" width="6" height="4" rx="1"/><rect x="6.5" y="15.5" width="11" height="4.5" rx="1.5"/>',
    terminal: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 10l3 2-3 2M12.5 15H17"/>',
    keypad: '<path d="M6 6v.01M12 6v.01M18 6v.01M6 12v.01M12 12v.01M18 12v.01M6 18v.01M12 18v.01M18 18v.01" stroke-width="3.2"/>',
    keys: '<rect x="3" y="7" width="18" height="10" rx="2"/><path d="M7 11v.01M11 11v.01M15 11v.01M8 14h8"/>',
    button: '<rect x="3.5" y="7.5" width="17" height="9" rx="4.5"/><circle cx="12" cy="12" r="2"/>',
    fader: '<path d="M6 4v16M12 4v16M18 4v16"/><rect x="4" y="13" width="4" height="3" rx="1"/><rect x="10" y="7" width="4" height="3" rx="1"/><rect x="16" y="10" width="4" height="3" rx="1"/>',
    lock: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/>',
    info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5M12 7.7v.01"/>',
    target: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><path d="M12 12v.01M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3"/>',
    cube: '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M12 12l8-4.5M12 12L4 7.5M12 12v9"/>',
    wheel: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="2.2"/><path d="M12 3.5v4.3M12 16.2v4.3M3.5 12h4.3M16.2 12h4.3"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M5.6 5.6l1.8 1.8M16.6 16.6l1.8 1.8M18.4 5.6l-1.8 1.8M7.4 16.6l-1.8 1.8"/>',
    cylinder: '<ellipse cx="12" cy="6.5" rx="6.5" ry="2.7"/><path d="M5.5 6.5v11c0 1.5 2.9 2.7 6.5 2.7s6.5-1.2 6.5-2.7v-11"/>',
    undo: '<path d="M9 5L4 10l5 5"/><path d="M4 10h9.5a5 5 0 010 10H9"/>',
    redo: '<path d="M15 5l5 5-5 5"/><path d="M20 10h-9.5a5 5 0 000 10H15"/>',
    sphere: '<circle cx="12" cy="12" r="8.5"/><ellipse cx="12" cy="12" rx="8.5" ry="3"/>',
    wedge: '<path d="M4 19h16L4 8z"/><path d="M4 8v11"/>',
    help: '<circle cx="12" cy="12" r="8.5"/><path d="M9.6 9.4a2.5 2.5 0 114 2c-.9.6-1.6 1.1-1.6 2.1M12 16.8v.01"/>',
    bulb: '<path d="M9 18h6M10 21h4M12 3a6 6 0 00-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0012 3z"/>',
    stage: '<path d="M3.5 19l3.5-5.5h10l3.5 5.5z"/><path d="M7 13.5V5.5h10v8M12 5.5V3"/>',
    "bulb-off": '<path d="M9 18h6M10 21h4M12 3a6 6 0 00-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0012 3z"/><path d="M4 4l16 16"/>',
    palette: '<path d="M12 3.5a8.5 8.5 0 100 17c1.3 0 2-.8 2-1.7 0-1.2-1-1.6-1-2.6 0-.9.7-1.5 1.7-1.5H17a3.5 3.5 0 003.5-3.5C20.5 6.7 16.7 3.5 12 3.5z"/><circle cx="7.8" cy="11" r="1"/><circle cx="10.5" cy="7.3" r="1"/><circle cx="15" cy="7.8" r="1"/>',
    eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/>',
    "eye-off": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/><path d="M4 4l16 16"/>',
    fixture: '<path d="M9 2.5h6M12 2.5V6"/><path d="M6.5 6h11v1.5"/><g transform="rotate(28 12 12)"><rect x="8.5" y="7.5" width="7" height="8" rx="1.8"/></g><path d="M9 19l-1 2.5M13 19.5l.4 2.5M17.5 17.5l1.8 2"/>',
    move: '<path d="M12 3v18M3 12h18M12 3l-3 3M12 3l3 3M12 21l-3-3M12 21l3-3M3 12l3-3M3 12l3 3M21 12l-3-3M21 12l-3 3"/>',
    rotate: '<path d="M20 12a8 8 0 11-2.6-5.9"/><path d="M20 4v4.5h-4.5"/>',
    scale: '<rect x="4" y="10" width="10" height="10" rx="1"/><path d="M14 4h6v6M20 4l-8 8"/>',
    spot: '<path d="M8 3h8l2 6H6z"/><path d="M9 12l-3 9M15 12l3 9M12 12v9"/>',
    truss: '<path d="M3 8h18M3 16h18M3 8l4 8 4-8 4 8 4-8"/>',
    wall: '<path d="M4 6h16v12H4z"/><path d="M4 12h16M9 6v6M15 12v6"/>',
    copy: '<rect x="8" y="8" width="12" height="12" rx="1.5"/><path d="M16 8V5.5A1.5 1.5 0 0014.5 4h-9A1.5 1.5 0 004 5.5v9A1.5 1.5 0 005.5 16H8"/>',
    download: '<path d="M12 4v12M7 11l5 5 5-5M5 20h14"/>',
    "bookmark-plus": '<path d="M7 4h10v16l-5-4-5 4z"/><path d="M12 8v5M9.5 10.5h5"/>',
    attach: '<path d="M6 4v8a6 6 0 0012 0V4"/><path d="M6 8h3M15 8h3"/>',
    save: '<path d="M5 4h11l3 3v13H5z"/><path d="M8 4v5h7V4M8 20v-6h8v6"/>',
  };
  const NS = "http://www.w3.org/2000/svg";

  function inner(name) {
    const def = PATHS[name] || PATHS.close;
    return typeof def === "string" ? { body: def, fill: false } : { body: def.d, fill: !!def.fill };
  }

  /** <svg class="ico ico--NAME"> als Element. extraClass optional. */
  function svg(name, extraClass) {
    const { body, fill } = inner(name);
    const node = document.createElementNS(NS, "svg");
    node.setAttribute("viewBox", "0 0 24 24");
    node.setAttribute("class", "ico ico--" + name + (fill ? " ico--fill" : "") + (extraClass ? " " + extraClass : ""));
    node.setAttribute("aria-hidden", "true");
    node.setAttribute("focusable", "false");
    node.innerHTML = body;                // feste Zeichenketten aus PATHS
    return node;
  }

  /** Dasselbe als HTML-Zeichenkette (fuer Vorlagen). */
  function markup(name, extraClass) {
    const { body, fill } = inner(name);
    return `<svg class="ico ico--${name}${fill ? " ico--fill" : ""}${extraClass ? " " + extraClass : ""}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${body}</svg>`;
  }

  return { svg, markup, has: (name) => Object.prototype.hasOwnProperty.call(PATHS, name) };
})();
