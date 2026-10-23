# Pilani Supply Co. — customer mobile app

Native Android/iOS app (React Native + Expo Router) for customers to browse the catalogue,
build a cart and place orders. It talks to the same FastAPI backend as the web apps:

| App action | Endpoint |
|---|---|
| Sign in | `POST /api/auth` |
| Catalogue (MRP, selling price, promo) | `GET /api/catalog` |
| Place order (cart + unlisted items + UTR) | `POST /api/orders` |
| My orders | `GET /api/customer/orders` |
| UPI QR at checkout | `/static/images/upi_qr.png` (uploaded in the admin portal) |

Screens: Login · Home (deals banner, category strip, product grid, sticky cart bar) · Cart ·
Checkout modal (unlisted items, UPI QR, UTR) · Orders · Account.

## Which server does the app use?

`app.json` → `expo.extra.apiUrl` is the address baked into the APK:

```json
"extra": { "apiUrl": "http://192.168.0.154:8000" }
```

That is the shop PC on the local Wi-Fi, so phones must be on the same Wi-Fi while the server
(`start_server.bat`) is running. Customers can also change the address on the login screen
(tap **Server: …** under the Sign in card) — so one APK keeps working when the backend moves
to a hosted domain. When you go live, change `apiUrl` to e.g. `https://speedbuy.pro` and
rebuild so new installs get the right default.

> If the PC's Wi-Fi address changes (check with `ipconfig` → "IPv4 Address"), update it on the
> login screen or in `app.json`. Giving the PC a fixed IP in your router avoids this.

## Build the APK in the cloud (EAS) — step by step

You need: this PC with Node.js (already installed), and a free Expo account.

1. **Create an Expo account** (once): sign up at https://expo.dev/signup.

2. **Open a terminal in this folder**:
   ```
   cd G:\pos_backend\pos_backend\mobile
   ```

3. **Install the app's packages** (first time, or after pulling changes):
   ```
   npm ci
   ```

4. **Log in to Expo** (once per PC) — enter your Expo email/username and password when asked:
   ```
   npx eas-cli@latest login
   ```

5. **Link the project to your Expo account** (once). Answer **Yes** when it asks to create a
   project; it writes a `projectId` into `app.json` — commit that change:
   ```
   npx eas-cli@latest init
   ```

6. **Start the cloud build**:
   ```
   npx eas-cli@latest build -p android --profile preview
   ```
   - First time only, it asks *"Generate a new Android Keystore?"* → answer **Yes**. Expo
     stores the signing key for you; every later APK is signed with the same key so updates
     install over the old app.
   - The build runs on Expo's servers (about 10–20 minutes). You can close the terminal; the
     build continues and shows up at https://expo.dev under your project → **Builds**.

7. **Download the APK**: when the build finishes the terminal prints a link (also on the
   build's page at expo.dev). Download the `.apk` file.

8. **Distribute it from your own domain**: upload the `.apk` to your website/host (for
   example `https://speedbuy.pro/app/pilani-supply.apk`) and share that link. On the phone:
   open the link → download → tap the file → allow **Install unknown apps** for the browser
   when Android asks → **Install**.

### Releasing an update

1. In `app.json` raise `"version"` (e.g. `1.0.1`) **and** `android.versionCode` (e.g. `2`).
2. Run step 6 again and replace the APK on your website. Customers install it over the old
   one; they stay signed in.

## Develop / preview on this PC

```
npm ci
npx expo start          # scan the QR with a development build, or press w for web
npx tsc --noEmit        # typecheck
npx expo-doctor         # dependency/config checks
```

Expo Go may not include every native module this app uses; for on-device testing build once
with `npx eas-cli@latest build -p android --profile development` and install that APK.

## Regenerating the icons

`assets/` holds the generated icon set. To change the colours or monogram, edit
`scripts/make-icons.py` and run it from the repo root:

```
.venv\Scripts\python.exe mobile\scripts\make-icons.py
```
