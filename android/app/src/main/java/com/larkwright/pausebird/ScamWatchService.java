package com.larkwright.pausebird;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.Parcelable;
import android.os.SystemClock;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Auto-watch: looks at NEW notifications from Google Messages and KakaoTalk only.
 *
 * Privacy:
 *  - The check (ScamPrefilter) runs on the phone. This service makes no network calls and saves
 *    nothing to storage.
 *  - When a message looks risky, it shows a Korean "check this" notification. Only if the person
 *    TAPS it does the text go to Pausebird (the normal Share path, same as sharing by hand).
 *
 * Turned on with "Notification access" for Pausebird (Settings, or adb:
 *   cmd notification allow_listener com.larkwright.pausebird/com.larkwright.pausebird.ScamWatchService).
 */
public class ScamWatchService extends NotificationListenerService {

    static final String CHANNEL_ID = "pausebird_alerts";
    private static final String[] WATCHED = {
            "com.google.android.apps.messaging",   // Google Messages (SMS/RCS)
            "com.kakao.talk",                      // KakaoTalk
    };
    private static final long DEDUPE_MS = 10 * 60 * 1000L;
    private static final int MAX_TEXT = 5000;

    // text hash -> when we last nudged about it (in-memory only, gone when the service stops)
    private final Map<Integer, Long> recent = new LinkedHashMap<>();

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        try {
            handle(sbn);
        } catch (RuntimeException e) {
            // Never crash the listener over one odd notification.
        }
    }

    private void handle(StatusBarNotification sbn) {
        if (sbn == null || !isWatched(sbn.getPackageName())) return;
        Notification n = sbn.getNotification();
        if (n == null || sbn.isOngoing()) return;
        if ((n.flags & Notification.FLAG_GROUP_SUMMARY) != 0) return;
        Bundle x = n.extras;
        if (x == null) return;

        String sender = str(x.getCharSequence(Notification.EXTRA_TITLE));
        String text = lastMessage(x);
        if (text.isEmpty()) text = str(x.getCharSequence(Notification.EXTRA_BIG_TEXT));
        if (text.isEmpty()) text = str(x.getCharSequence(Notification.EXTRA_TEXT));
        text = text.trim();
        if (text.isEmpty()) return;
        if (text.length() > MAX_TEXT) text = text.substring(0, MAX_TEXT);

        ScamPrefilter.Result r = ScamPrefilter.check(sender + "\n" + text);
        if (!r.hit()) return;

        int key = (sbn.getPackageName() + "\u0000" + text).hashCode();
        long now = SystemClock.elapsedRealtime();
        synchronized (recent) {
            for (Iterator<Map.Entry<Integer, Long>> it = recent.entrySet().iterator(); it.hasNext(); ) {
                if (now - it.next().getValue() > DEDUPE_MS) it.remove();
            }
            if (recent.containsKey(key)) return;
            recent.put(key, now);
        }
        nudge(key, sender, text);
    }

    /** MessagingStyle notifications keep the newest message last in EXTRA_MESSAGES. */
    private static String lastMessage(Bundle x) {
        Parcelable[] msgs = x.getParcelableArray(Notification.EXTRA_MESSAGES);
        if (msgs == null || msgs.length == 0) return "";
        Parcelable last = msgs[msgs.length - 1];
        if (last instanceof Bundle) return str(((Bundle) last).getCharSequence("text"));
        return "";
    }

    private void nudge(int key, String sender, String text) {
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return;
        ensureChannel(nm);

        // Same intent as sharing the text to Pausebird by hand: the app opens and checks it.
        Intent share = new Intent(Intent.ACTION_SEND)
                .setClass(this, LauncherActivity.class)
                .setType("text/plain")
                .putExtra(Intent.EXTRA_TEXT, text)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        if (!sender.isEmpty()) share.putExtra(Intent.EXTRA_SUBJECT, "보낸 사람: " + sender);

        int flags = PendingIntent.FLAG_UPDATE_CURRENT
                | (Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0);
        PendingIntent tap = PendingIntent.getActivity(this, key, share, flags);

        Notification.Builder b = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);
        b.setSmallIcon(android.R.drawable.ic_dialog_alert)
                .setContentTitle("⚠️ 의심스러운 메시지")
                .setContentText("누르거나 답장하기 전에, 여기를 눌러 Pausebird로 확인하세요.")
                .setStyle(new Notification.BigTextStyle().bigText(
                        "누르거나 답장하기 전에, 여기를 눌러 Pausebird로 확인하세요."
                                + (sender.isEmpty() ? "" : "\n보낸 사람: " + sender)))
                .setContentIntent(tap)
                .setAutoCancel(true)
                .setCategory(Notification.CATEGORY_MESSAGE);
        if (Build.VERSION.SDK_INT < 26) b.setPriority(Notification.PRIORITY_HIGH);
        nm.notify("pausebird-watch", key, b.build());
    }

    static void ensureChannel(NotificationManager nm) {
        if (Build.VERSION.SDK_INT < 26 || nm.getNotificationChannel(CHANNEL_ID) != null) return;
        NotificationChannel ch = new NotificationChannel(CHANNEL_ID, "Pausebird 경고",
                NotificationManager.IMPORTANCE_HIGH);
        ch.setDescription("의심스러운 문자나 카톡이 오면 알려 줍니다. (Alerts when a text or KakaoTalk message looks risky.)");
        nm.createNotificationChannel(ch);
    }

    private static boolean isWatched(String pkg) {
        for (String p : WATCHED) if (p.equals(pkg)) return true;
        return false;
    }

    private static String str(CharSequence cs) {
        return cs == null ? "" : cs.toString();
    }
}
