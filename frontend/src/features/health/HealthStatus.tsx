import { getHealth } from "./api";

const copy = {
  label: "Статус API",
  unreachable: "API недоступне. Перевір, що бекенд запущено: make up.",
  checks: {
    database: "База даних",
    redis: "Redis",
  },
};

export async function HealthStatus() {
  const health = await getHealth();

  if (!health) {
    return <p role="status">{copy.unreachable}</p>;
  }

  return (
    <section role="status" className="flex flex-col gap-3">
      <p className="text-2xl">
        {copy.label}: <strong>{health.status}</strong>
      </p>
      <dl className="grid grid-cols-[max-content_auto] gap-x-6 gap-y-1 text-sm">
        <dt>{copy.checks.database}</dt>
        <dd>{health.checks.database}</dd>
        <dt>{copy.checks.redis}</dt>
        <dd>{health.checks.redis}</dd>
      </dl>
    </section>
  );
}
