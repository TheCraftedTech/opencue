# Vendored libraries

## three/three-lite.js
A trimmed build of [three.js](https://threejs.org) (MIT, see `three/LICENSE`) plus its `OrbitControls`, exposed as `window.THREE`
(only the classes the 3D stage of the live demo uses). It is a plain script, so the site also works when the files are opened
straight from disk. Source: `static/vendor/three` of this repository (three.js r186).

How it was made (one-off, not part of the site; needs Node):

```
npm install esbuild
# entry.js imports the needed names from "three" and OrbitControls, and assigns them to window.THREE
npx esbuild entry.js --bundle --minify --format=iife --legal-comments=inline --target=es2020 \
  --alias:three=static/vendor/three/three.module.js --outfile=docs/assets/vendor/three/three-lite.js
```

The list of names is in `docs/assets/demo/stage3d.js` (every `THREE.<Name>` it uses). If a new one is needed, add it to the entry and rebuild.
