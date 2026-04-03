import { appendFileSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { BrainClient } from "./brain-client.js";

export interface TranscriptRecord {
  transcript: string;
  tags: string[];
  source: "telegram";
  chat_id: string;
  message_id: number;
  received_at: string;
  tenant: string;
}

export interface MemorySink {
  kind: "file" | "mcp" | "webhook";
  persist(record: TranscriptRecord): Promise<void>;
}

function requiredEnv(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing required env var: ${name}`);
  return value;
}

function optionalEnv(name: string): string | undefined {
  const value = process.env[name]?.trim();
  return value || undefined;
}

class FileMemorySink implements MemorySink {
  readonly kind = "file" as const;

  constructor(private readonly filePath: string) {}

  async persist(record: TranscriptRecord): Promise<void> {
    mkdirSync(dirname(this.filePath), { recursive: true });
    appendFileSync(this.filePath, `${JSON.stringify(record)}\n`, "utf-8");
  }
}

class McpMemorySink implements MemorySink {
  readonly kind = "mcp" as const;

  constructor(private readonly brain: BrainClient) {}

  async persist(record: TranscriptRecord): Promise<void> {
    await this.brain.callToolJson("mind_observe", {
      mode: "whisper",
      content: record.transcript,
      tags: record.tags,
      context: `source=${record.source} chat_id=${record.chat_id} message_id=${record.message_id} received_at=${record.received_at}`,
    });
  }
}

class WebhookMemorySink implements MemorySink {
  readonly kind = "webhook" as const;

  constructor(
    private readonly url: string,
    private readonly apiKey: string | undefined,
    private readonly timeoutMs: number
  ) {}

  async persist(record: TranscriptRecord): Promise<void> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }

    const response = await fetch(this.url, {
      method: "POST",
      headers,
      body: JSON.stringify(record),
      signal: AbortSignal.timeout(this.timeoutMs),
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Memory webhook failed (${response.status}): ${body.slice(0, 300)}`);
    }
  }
}

export function createMemorySinkFromEnv(timeoutMs: number): MemorySink {
  const mode = (process.env["MEMORY_SINK_MODE"] || "").trim().toLowerCase();

  const autoSelectMcp = !mode && optionalEnv("BRAIN_URL") && optionalEnv("BRAIN_API_KEY");
  if (mode === "mcp" || autoSelectMcp) {
    const tenant = optionalEnv("VOICE_BRIDGE_TENANT") || "rainer";
    const brain = new BrainClient(requiredEnv("BRAIN_URL"), requiredEnv("BRAIN_API_KEY"), tenant);
    return new McpMemorySink(brain);
  }

  const autoSelectWebhook = !mode && optionalEnv("MEMORY_WEBHOOK_URL");
  if (mode === "webhook" || autoSelectWebhook) {
    return new WebhookMemorySink(
      requiredEnv("MEMORY_WEBHOOK_URL"),
      optionalEnv("MEMORY_WEBHOOK_API_KEY"),
      timeoutMs
    );
  }

  if (mode === "" || mode === "file") {
    return new FileMemorySink(optionalEnv("MEMORY_FILE_PATH") || "./state/transcripts.ndjson");
  }

  throw new Error(`Unsupported MEMORY_SINK_MODE: ${mode} (expected file|mcp|webhook)`);
}

