import { createTelegramNotifierFromEnv } from "./telegram-notifier.js";
import type { NotificationEvent } from "./notifier.js";

const notifier = createTelegramNotifierFromEnv();
if (!notifier) {
  throw new Error("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required");
}

const event: NotificationEvent = {
  event_type: "personal_wake_completed",
  tenant: process.env["VOICE_BRIDGE_TENANT"]?.trim() || "rainer",
  wake_type: "personal",
  summary: "MUSE voice stack demo ping. If voice is enabled, you should get a voice note too.",
  timestamp: new Date().toISOString(),
  user_visible: true,
};

await notifier.send(event);
console.log("demo notification sent");
