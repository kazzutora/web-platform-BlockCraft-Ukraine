"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { buttonClasses } from "@/components/ui/buttonClasses";
import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { Dialog } from "@/components/ui/Dialog";
import { Icon } from "@/components/ui/Icon";
import { Input } from "@/components/ui/Input";
import type { Me } from "@/features/auth/useMe";
import { api } from "@/lib/api/client";
import { fieldErrors, generalError } from "@/lib/api/errors";
import { setSessionHint } from "@/lib/session-hint";

import { settingsCopy } from "./copy";

const copy = settingsCopy.data;
type Mode = "anonymize" | "delete";

/** «Мої дані»: download everything as JSON, or leave (anonymize or delete). */
export function DataPanel({ me }: { me: Me }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<Mode>("anonymize");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function leave() {
    setBusy(true);
    setError("");
    const { error: apiError, response } = await api.DELETE("/api/v1/me", {
      params: { query: { mode, confirm } },
    });
    setBusy(false);
    if (!response.ok) {
      setError(fieldErrors(apiError).confirm ?? generalError(apiError, copy.error));
      return;
    }
    setSessionHint(false);
    queryClient.clear();
    router.replace("/");
    router.refresh();
  }

  return (
    <div className="flex max-w-xl flex-col gap-10">
      <section className="flex flex-col gap-3">
        <h2 className="caps font-sans">{copy.exportTitle}</h2>
        <p className="text-muted">{copy.exportText}</p>
        <a
          href="/api/v1/me/export"
          download
          className={buttonClasses({ variant: "secondary", className: "self-start" })}
        >
          <Icon name="download" />
          {copy.export}
        </a>
      </section>

      <section className="flex flex-col gap-3 border-t border-line pt-10">
        <h2 className="caps font-sans">{copy.deleteTitle}</h2>
        <p className="text-muted">{copy.deleteText}</p>
        <Dialog
          title={copy.dialogTitle}
          open={open}
          onOpenChange={setOpen}
          trigger={
            <Button variant="secondary" className="self-start">
              {copy.delete}
            </Button>
          }
          footer={
            <>
              <Button variant="ghost" onClick={() => setOpen(false)}>
                {copy.cancel}
              </Button>
              <Button
                loading={busy}
                disabled={confirm.trim().toLowerCase() !== me.nickname.toLowerCase()}
                onClick={() => void leave()}
              >
                {mode === "delete" ? copy.confirmDelete : copy.confirmAnonymize}
              </Button>
            </>
          }
        >
          <div className="flex flex-col gap-6">
            <ChoiceChips
              label={copy.mode}
              options={[
                { value: "anonymize", label: copy.modes.anonymize },
                { value: "delete", label: copy.modes.delete },
              ]}
              value={mode}
              onChange={setMode}
            />
            <p className="text-sm text-muted">{copy.modeHints[mode]}</p>
            <Input
              label={copy.confirm(me.nickname)}
              autoComplete="off"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              error={error}
            />
          </div>
        </Dialog>
      </section>
    </div>
  );
}
