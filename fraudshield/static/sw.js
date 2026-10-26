// Needed so Android can install the page and offer "Share to Fraud Shield".
// Nothing is cached: messages and checks are private, and every check needs the server anyway.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
