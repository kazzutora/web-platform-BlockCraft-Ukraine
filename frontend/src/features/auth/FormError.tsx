import { Icon } from "@/components/ui/Icon";

/** Error of the whole form, announced to screen readers. */
export function FormError({ message }: { message?: string }) {
  if (!message) return null;
  return (
    <p role="alert" className="flex items-start gap-2 border border-danger p-3 text-sm text-danger">
      <Icon name="warning" className="shrink-0" />
      {message}
    </p>
  );
}
