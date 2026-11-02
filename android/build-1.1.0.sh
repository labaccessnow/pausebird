#!/bin/bash
# Build + sign Pausebird 1.1.0 (auto-watch) with gradle directly. NOT `bubblewrap build/update`
# (those would regenerate the manifest/java and drop the hand-written ScamWatchService).
set -euo pipefail
export JAVA_HOME=$HOME/jdk17 ANDROID_HOME=$HOME/pb-sdk ANDROID_SDK_ROOT=$HOME/pb-sdk
export PATH=$JAVA_HOME/bin:$PATH
cd "$HOME/pausebird-android"
BT=$ANDROID_HOME/build-tools/36.0.0
KS=$HOME/.android-keystores/pausebird-upload.jks
PASSF=$HOME/.android-keystores/pausebird-upload.pass
OUT=$HOME/pausebird-android/out-1.1.0
./gradlew --no-daemon -q clean bundleRelease assembleRelease
mkdir -p "$OUT"
cp app/build/outputs/bundle/release/app-release.aab "$OUT/app-release-bundle.aab"
jarsigner -keystore "$KS" -storepass:file "$PASSF" -keypass:file "$PASSF" "$OUT/app-release-bundle.aab" pausebird >/dev/null
"$BT/zipalign" -f -p 4 app/build/outputs/apk/release/app-release-unsigned.apk "$OUT/app-release-unsigned-aligned.apk"
"$BT/apksigner" sign --ks "$KS" --ks-key-alias pausebird --ks-pass "file:$PASSF" \
    --out "$OUT/app-release-signed.apk" "$OUT/app-release-unsigned-aligned.apk"
rm -f "$OUT/app-release-unsigned-aligned.apk"
echo BUILD_OK
