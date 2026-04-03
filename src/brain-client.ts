interface JsonRpcResponse<T = unknown> {
  jsonrpc: "2.0";
  id: number;
  result?: T;
  error?: { code: number; message: string };
}

interface ToolCallResult {
  content: Array<{ type: string; text: string }>;
}

export class BrainClient {
  private requestId = 0;

  constructor(
    private readonly url: string,
    private readonly apiKey: string,
    private readonly tenant: string
  ) {}

  private async post<T>(method: string, params: Record<string, unknown>): Promise<T> {
    const id = ++this.requestId;
    const body: Record<string, unknown> = { jsonrpc: "2.0", method, params, id };

    const response = await fetch(this.url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${this.apiKey}`,
        "X-Brain-Tenant": this.tenant,
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(30_000),
    });

    if (response.status === 401) throw new Error("Brain auth failed — check BRAIN_API_KEY");
    if (response.status === 429) throw new Error("Brain rate limited");
    if (!response.ok) throw new Error(`Brain HTTP ${response.status}: ${response.statusText}`);

    const json = (await response.json()) as JsonRpcResponse<T>;
    if (json.error) throw new Error(`Brain RPC error ${json.error.code}: ${json.error.message}`);
    if (json.result === undefined) throw new Error("Brain returned empty result");
    return json.result;
  }

  async callTool(name: string, args: Record<string, unknown>): Promise<string> {
    const result = await this.post<ToolCallResult>("tools/call", {
      name,
      arguments: args,
    });

    return result.content
      .filter((block) => block.type === "text")
      .map((block) => block.text)
      .join("\n");
  }

  async callToolJson<T>(name: string, args: Record<string, unknown>): Promise<T> {
    const raw = await this.callTool(name, args);
    return JSON.parse(raw) as T;
  }
}
