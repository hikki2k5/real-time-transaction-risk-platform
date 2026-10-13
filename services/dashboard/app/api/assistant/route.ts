import { proxyAssistant } from "../../lib/assistant-proxy";

export const runtime = "nodejs";
export const maxDuration = 120;

export async function POST(request: Request) {
  return proxyAssistant(request, {
    authBaseUrl: process.env.AUTH_API_BASE_URL || process.env.NEXT_PUBLIC_AUTH_API_BASE_URL || "",
    assistantBaseUrl: process.env.AI_ASSISTANT_BASE_URL || "",
    operatorToken: process.env.AI_ASSISTANT_API_TOKEN || ""
  });
}
