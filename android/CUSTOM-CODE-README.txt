1.1.0 adds HAND-WRITTEN code that Bubblewrap does not know about:
  app/src/main/java/com/larkwright/pausebird/ScamPrefilter.java
  app/src/main/java/com/larkwright/pausebird/ScamWatchService.java
  AndroidManifest.xml: POST_NOTIFICATIONS + the ScamWatchService <service> block
DO NOT run `bubblewrap update` (it regenerates the manifest/java from templates and would drop these).
Build with gradle directly (build-1.1.0.sh), not `bubblewrap build`.
Backup of the untouched 1.0.0 source: ~/pausebird-android-src-1.0.0-backup.tgz
