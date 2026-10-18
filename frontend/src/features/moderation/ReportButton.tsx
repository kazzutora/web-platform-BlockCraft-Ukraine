"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { Dialog } from "@/components/ui/Dialog";
import { Icon } from "@/components/ui/Icon";
import { Textarea } from "@/components/ui/Textarea";
import { useToast } from "@/components/ui/useToast";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { api } from "@/lib/api/client";
import { generalError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";
import { cn } from "@/lib/cn";

type ReportKind = components["schemas"]["ReportKindEnum"];
type Reason = components["schemas"]["ReasonEnum"];

const copy = {
  open: "Поскаржитися",
  title: "Що не так?",
  description: "Скаргу побачать лише модератори. Після п’яти скарг об’єкт ховається до перевірки.",
  reason: "Причина",
  reasons: [
    { value: "inappropriate", label: "Неприйнятний вміст" },
    { value: "spam", label: "Спам або реклама" },
    { value: "stolen", label: "Чужа робота" },
    { value: "scam", label: "Шахрайство" },
    { value: "other", label: "Інше" },
  ] satisfies Array<{ value: Reason; label: string }>,
  comment: "Коментар для модератора",
  commentHint: "Необов’язково, до 500 символів.",
  submit: "Надіслати скаргу",
  cancel: "Скасувати",
  sent: "Дякуємо! Модератори перевірять.",
  error: "Не вдалося надіслати скаргу.",
};

type ReportButtonProps = {
  kind: ReportKind;
  id: string;
  /** Text button (pages) or a small flag (comments). */
  compact?: boolean;
};

/** «Поскаржитися»: reason and an optional note for the moderators. */
export function ReportButton({ kind, id, compact = false }: ReportButtonProps) {
  const toast = useToast();
  const requireAuth = useRequireAuth();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<Reason | "">("");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);

  async function send() {
    if (!reason) return;
    setBusy(true);
    const { error, response } = await api.POST("/api/v1/reports", {
      body: { kind, id, reason, comment },
    });
    setBusy(false);
    if (!response.ok) {
      toast({ title: generalError(error, copy.error), tone: "danger" });
      return;
    }
    setOpen(false);
    setReason("");
    setComment("");
    toast({ title: copy.sent });
  }

  return (
    <Dialog
      title={copy.title}
      description={copy.description}
      open={open}
      onOpenChange={(next) => (next ? requireAuth(() => setOpen(true)) : setOpen(false))}
      trigger={
        <Button
          variant="ghost"
          aria-label={compact ? copy.open : undefined}
          title={compact ? copy.open : undefined}
          className={cn(compact && "size-9 px-0 text-muted")}
        >
          <Icon name="flag" size={compact ? 16 : 24} />
          {!compact && copy.open}
        </Button>
      }
      footer={
        <>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            {copy.cancel}
          </Button>
          <Button loading={busy} disabled={!reason} onClick={() => void send()}>
            {copy.submit}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-6">
        <ChoiceChips
          label={copy.reason}
          options={copy.reasons}
          value={reason}
          onChange={setReason}
        />
        <Textarea
          label={copy.comment}
          hint={copy.commentHint}
          maxLength={500}
          rows={3}
          value={comment}
          onChange={(event) => setComment(event.target.value)}
        />
      </div>
    </Dialog>
  );
}
