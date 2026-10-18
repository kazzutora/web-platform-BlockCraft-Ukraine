import net from "node:net";

/**
 * With TUNNEL_TO=nginx:80 (tests in a container next to the stack) forwards
 * localhost:8080 there: Django accepts only localhost as the host and origin.
 */
export default async function globalSetup() {
  const target = process.env.TUNNEL_TO;
  if (!target) return;
  const [host, port] = target.split(":");
  const server = net.createServer((client) => {
    const upstream = net.connect(Number(port), host);
    client.pipe(upstream).pipe(client);
    upstream.on("error", () => client.destroy());
    client.on("error", () => upstream.destroy());
  });
  await new Promise<void>((resolve) => server.listen(8080, "127.0.0.1", resolve));
  return () => new Promise<void>((resolve) => server.close(() => resolve()));
}
