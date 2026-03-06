# /src/assets/images  →  project images folder

Place your product images here.

## Required file
- `Equalizer.png`  — the hand-holding-device hero image used on the homepage

## How the image is referenced
In `home.component.html` the `<img>` tag uses the path:

  src="images/Equalizer.png"

Angular's `angular.json` asset configuration copies the entire `src/assets/`
folder to the build output, so the file is served at:

  http://localhost:4200/images/Equalizer.png   (dev)
  /images/Equalizer.png                        (production)
