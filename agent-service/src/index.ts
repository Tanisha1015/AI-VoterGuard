import cors from "@fastify/cors";
import Fastify, { type FastifyInstance } from "fastify";
import { loadConfig, type AgentConfig } from "./config.js";
import { ExplainService } from "./explain.js";
import { AgentUnavailableError, ExplainRequestSchema, NeutralityFailedError } from "./types.js";

function errorBody(code: string, message: string): { error: { code: string; message: string } } {
  return { error: { code, message } };
}

/** Build the agent-service HTTP app (CONTRACT.md 6.4). `service` can be injected for tests. */
export async function buildApp(
  config: AgentConfig = loadConfig(),
  service: ExplainService = new ExplainService(config),
): Promise<FastifyInstance> {
  const app = Fastify({ logger: !process.env.VITEST });
  await app.register(cors, { origin: "http://localhost:5173" });

  app.get("/health", async () => ({ status: "ok", mode: config.mock ? "mock" : "agent" }));

  app.post("/explain", async (request, reply) => {
    const parsed = ExplainRequestSchema.safeParse(request.body);
    if (!parsed.success) {
      const message = parsed.error.issues
        .map((issue) => `${issue.path.join(".") || "body"}: ${issue.message}`)
        .join("; ");
      return reply.code(422).send(errorBody("VALIDATION_ERROR", message));
    }
    try {
      return await service.explain(parsed.data);
    } catch (error) {
      if (error instanceof NeutralityFailedError) {
        return reply.code(422).send(errorBody("NEUTRALITY_FAILED", error.message));
      }
      if (error instanceof AgentUnavailableError) {
        return reply.code(503).send(errorBody("AGENT_UNAVAILABLE", error.message));
      }
      request.log.error({ err: error }, "unexpected error while explaining a flag");
      return reply.code(503).send(errorBody("AGENT_UNAVAILABLE", "The agent could not complete the request."));
    }
  });

  return app;
}

async function main(): Promise<void> {
  const config = loadConfig();
  const app = await buildApp(config);
  await app.listen({ port: config.port, host: "0.0.0.0" });
  app.log.info(`agent-service mode: ${config.mock ? "mock" : "agent"}`);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err: unknown) => {
    console.error(err);
    process.exit(1);
  });
}
