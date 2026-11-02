package com.larkwright.pausebird;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * On-device first look at a new text or KakaoTalk message. Pure Java (no Android classes) so it
 * can be tested on a desktop JVM.
 *
 * It does NOT decide whether something is a scam. It only decides whether the message is worth a
 * "check this with Pausebird" nudge. The real check runs on the server, and only when the person
 * taps the nudge. Nothing here sends anything anywhere.
 *
 * Score >= THRESHOLD means "nudge". One strong sign is enough; weak signs need company, so an
 * ordinary bank or delivery notice doesn't nag.
 */
public final class ScamPrefilter {

    public static final int THRESHOLD = 3;

    public static final class Result {
        public final int score;
        public final List<String> reasons;
        Result(int score, List<String> reasons) { this.score = score; this.reasons = reasons; }
        public boolean hit() { return score >= THRESHOLD; }
    }

    // Links: with a scheme, starting www., or a bare domain with a path or a known TLD.
    private static final Pattern URL = Pattern.compile(
            "(?i)(?:https?://|www\\.)[^\\s<>\"']+"
            + "|\\b[a-z0-9][a-z0-9-]*(?:\\.[a-z0-9-]+)*\\.(?:[a-z]{2,24})(?:/[^\\s<>\"']*)?(?=$|[\\s,;!?)])");
    private static final Pattern HOST = Pattern.compile("(?i)^(?:https?://)?(?:www\\.)?([^/:?#\\s]+)");
    private static final Pattern IP_HOST = Pattern.compile("^\\d{1,3}(?:\\.\\d{1,3}){3}$");

    // Common, well-known sites that friends and family share all the time. A link to one of these
    // alone is not a reason to nudge (other signs still count).
    private static final String[] TRUSTED = {
            "youtube.com", "youtu.be", "naver.com", "naver.me", "daum.net", "kakao.com", "kakaocorp.com",
            "google.com", "goo.gl.maps", "maps.app.goo.gl", "apple.com", "microsoft.com", "wikipedia.org",
            "nytimes.com", "washingtonpost.com", "cnn.com", "bbc.com", "yna.co.kr", "chosun.com",
            "joongang.co.kr", "donga.com", "hani.co.kr", "koreadaily.com", "instagram.com", "facebook.com"
    };
    private static final String[] SHORTENERS = {
            "bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "ow.ly", "buff.ly", "rebrand.ly", "cutt.ly",
            "han.gl", "me2.kr", "url.kr", "vo.la", "shorturl.at", "rb.gy", "s.id", "t.ly", "tiny.cc", "lnkd.in",
            "bitly.com", "short.io"
    };
    // TLDs that cheap scam domains love.
    private static final String[] RISKY_TLDS = {
            "top", "xyz", "vip", "icu", "click", "shop", "live", "online", "site", "info", "cc", "tk", "ml",
            "ga", "cf", "gq", "pw", "ru", "cn", "link", "buzz", "rest", "monster", "cyou", "sbs", "cfd",
            "bond", "lol", "mom", "quest", "win", "work", "support", "help", "page"
    };
    // A brand name inside a domain that isn't the brand's own site (usps-help.top, chase-login.xyz).
    private static final String[][] BRANDS = {
            {"usps", "usps.com"}, {"ups", "ups.com"}, {"fedex", "fedex.com"}, {"amazon", "amazon.com"},
            {"paypal", "paypal.com"}, {"chase", "chase.com"}, {"wellsfargo", "wellsfargo.com"},
            {"bankofamerica", "bankofamerica.com"}, {"ezpass", "e-zpassny.com"}, {"apple", "apple.com"},
            {"netflix", "netflix.com"}, {"irs", "irs.gov"}, {"cj", "cjlogistics.com"}, {"kbstar", "kbstar.com"},
            {"shinhan", "shinhan.com"}, {"wooribank", "wooribank.com"}, {"hanabank", "hanabank.com"},
            {"nhbank", "nhbank.com"}, {"coupang", "coupang.com"}, {"kakaobank", "kakaobank.com"}
    };

    // Korean internet-phone numbers (070) that voice-phishing rings use, from home or abroad.
    private static final Pattern KR_070 = Pattern.compile("(?:\\+\\s?82[\\s.-]?0?70|\\b070)[\\s.)-]?\\d{3,4}[\\s.-]?\\d{4}");

    // One of these alone is worth a nudge.
    private static final Pattern STRONG = Pattern.compile("(?i)("
            + "안전\\s?계좌|문화\\s?상품권|구글\\s?기프트|기프트\\s?카드|상품권|검찰|지검|수사관|금융감독원|금감원|대포\\s?통장|명의\\s?도용"
            + "|원격\\s?(?:앱|제어|프로그램)|팀뷰어|애니데스크|액정|폰이?\\s?(?:고장|깨졌|망가)|새\\s?번호|번호\\s?바뀌|수리\\s?맡겼"
            + "|비트코인|가상\\s?화폐|코인\\s?투자|미납\\s?(?:요금|통행료)|통행료|주소\\s?(?:확인|불일치|오류)|배송이?\\s?(?:보류|지연|불가)"
            + "|gift\\s?cards?|bitcoin|crypto(?:currency)?|wire\\s?transfer|western\\s?union|zelle\\s?me"
            + "|account\\s+(?:has\\s+been\\s+|is\\s+)?(?:suspended|locked|disabled|on\\s+hold)|unusual\\s+(?:activity|sign-?in)"
            + "|unpaid\\s+toll|toll\\s+balance|package\\s+(?:is\\s+)?(?:on\\s+hold|undeliverable)|incomplete\\s+address"
            + "|verify\\s+your\\s+(?:identity|account|information)|final\\s+notice|social\\s+security\\s+(?:number|administration)"
            + "|lost\\s+my\\s+phone|new\\s+number|teamviewer|anydesk|remote\\s+access"
            + ")");
    // Family-member impersonation: "Mom, it's me", "엄마 나야", "Grandpa it's me".
    private static final Pattern FAMILY = Pattern.compile("(?i)("
            + "(?:엄마|아빠|어머니|아버지|할머니|할아버지)[,\\s]*(?:나야|저예요|저에요|나예요)"
            + "|(?:mom|dad|grandma|grandpa|grandmother|grandfather)[,!\\s]+(?:it'?s|its)\\s+me"
            + ")");
    // Each of these adds a little.
    private static final Pattern WEAK = Pattern.compile("(?i)("
            + "송금|이체|입금\\s?해|계좌|택배|배송|보류|미납|연체|환급|당첨|대출|인증\\s?번호|비밀\\s?번호|급하게|급해|긴급|지금\\s?바로"
            + "|아무(?:에게|한테)도|비밀로|확인\\s?바랍니다|클릭|링크"
            + "|urgent|immediately|right\\s+away|within\\s+24\\s+hours|verify|suspend|refund|prize|winner"
            + "|password|passcode|pay\\s+now|payment|overdue|locked|click|don'?t\\s+tell"
            + ")");

    private ScamPrefilter() { }

    public static Result check(String text) {
        List<String> why = new ArrayList<>();
        if (text == null) return new Result(0, why);
        String t = text.length() > 5000 ? text.substring(0, 5000) : text;
        int score = 0;

        Matcher u = URL.matcher(t);
        while (u.find()) {
            String link = u.group();
            Matcher h = HOST.matcher(link);
            if (!h.find()) continue;
            String host = h.group(1).toLowerCase(Locale.ROOT).replaceAll("[.,]+$", "");
            if (!host.contains(".")) continue;
            // Skip things like "10.00" or "3.5" that only look like domains.
            String tld = host.substring(host.lastIndexOf('.') + 1);
            if (tld.matches("\\d+")) {
                if (IP_HOST.matcher(host).matches()) { score += 3; why.add("link to a bare IP address"); }
                continue;
            }
            boolean hasScheme = link.matches("(?i)^(?:https?://|www\\.).*");
            boolean hasPath = link.indexOf('/', hasScheme ? link.indexOf("//") + 2 : 0) > 0;
            if (!hasScheme && !hasPath && !isKnownTld(tld)) continue; // "Mr.Kim" etc.
            if (host.startsWith("xn--") || host.contains(".xn--")) { score += 3; why.add("look-alike (punycode) link"); continue; }
            if (endsWithAny(host, SHORTENERS)) { score += 3; why.add("short link that hides where it goes"); continue; }
            if (endsWithAny(host, TRUSTED)) continue;
            if (contains(RISKY_TLDS, tld)) { score += 3; why.add("link on a cheap ." + tld + " address"); continue; }
            String brandHit = brandMismatch(host);
            if (brandHit != null) { score += 3; why.add("uses the name '" + brandHit + "' but isn't its site"); continue; }
            score += 1; why.add("has a link");
        }
        if (KR_070.matcher(t).find()) { score += 3; why.add("070 internet-phone number"); }
        Matcher s = STRONG.matcher(t);
        if (s.find()) { score += 3; why.add("pressure or money trick: " + s.group(1)); }
        if (FAMILY.matcher(t).find()) { score += 3; why.add("'it's me' family message"); }
        Matcher w = WEAK.matcher(t);
        int weak = 0;
        while (w.find() && weak < 3) { weak++; }
        if (weak > 0) { score += weak; why.add(weak + " warning word(s)"); }
        return new Result(score, why);
    }

    private static boolean isKnownTld(String tld) {
        return tld.length() == 2 || contains(RISKY_TLDS, tld)
                || contains(new String[]{"com", "net", "org", "gov", "edu", "info", "biz", "app", "dev", "io", "me", "co"}, tld);
    }

    private static String brandMismatch(String host) {
        String flat = host.replace("-", "").replace(".", " ");
        for (String[] b : BRANDS) {
            String brand = b[0], real = b[1];
            if (host.equals(real) || host.endsWith("." + real)) return null;
            boolean named = brand.length() >= 4 ? flat.contains(brand)
                    : (" " + flat + " ").matches(".*[\\s]" + brand + "[a-z]*\\s.*") || host.startsWith(brand + "-");
            if (named) return brand;
        }
        return null;
    }

    private static boolean endsWithAny(String host, String[] list) {
        for (String d : list) if (host.equals(d) || host.endsWith("." + d)) return true;
        return false;
    }

    private static boolean contains(String[] list, String s) {
        for (String x : list) if (x.equals(s)) return true;
        return false;
    }
}
