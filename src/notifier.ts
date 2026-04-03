export type NotificationEventType =
  | "task_completed"
  | "review_completed"
  | "personal_wake_completed"
  | "impulse_wake_completed"
  | "dream_completed"
  | "wake_failed";

export interface NotificationEvent {
  event_type: NotificationEventType;
  tenant: string;
  wake_type: "duty" | "baton" | "personal" | "impulse" | "dream";
  summary: string;
  artifact_path?: string;
  timestamp: string;
  user_visible: boolean;
}

export interface Notifier {
  send(event: NotificationEvent): Promise<void>;
}
