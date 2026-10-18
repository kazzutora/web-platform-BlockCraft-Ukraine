import { Button } from "./Button";
import { ButtonLink } from "./ButtonLink";

const copy = { label: "Показати ще", loading: "Завантажуємо…" };

type LoadMoreProps =
  | { href: string; onClick?: never; loading?: never }
  | { href?: never; onClick: () => void; loading?: boolean };

/** «Показати ще» under a catalog grid: a link to the next page or a button. */
export function LoadMore({ href, onClick, loading = false }: LoadMoreProps) {
  return (
    <div className="flex justify-center pt-8">
      {href !== undefined ? (
        <ButtonLink href={href} variant="secondary" size="lg" scroll={false}>
          {copy.label}
        </ButtonLink>
      ) : (
        <Button variant="secondary" size="lg" onClick={onClick} loading={loading}>
          {loading ? copy.loading : copy.label}
        </Button>
      )}
    </div>
  );
}
