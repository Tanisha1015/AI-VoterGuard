import Fastify, { type FastifyInstance } from "fastify";
import cors from "@fastify/cors";

/** Build the agent-service HTTP app. Explanation logic is added in task A5. */
export async function buildApp(): Promise<FastifyInstance> {
  const app = Fastify({ logger: true });
  await app.register(cors, { origin: "http://localhost:5173" });

  app.get("/health", async () => ({ status: "ok", mode: "mock" }));

  return app;
}

async function main(): Promise<void> {
  const port = Number(process.env.PORT ?? 8001);
  const app = await buildApp();
  await app.listen({ port, host: "0.0.0.0" });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err: unknown) => {
    console.error(err);
    process.exit(1);
  });
}
