"use client";

import { type ChangeEvent, useRef, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { useToast } from "@/components/ui/useToast";
import { FormError } from "@/features/auth/FormError";
import type { Me } from "@/features/auth/useMe";
import { fieldErrors, generalError } from "@/lib/api/errors";

import { settingsCopy } from "./copy";
import { useAvatar, useUpdateAccount } from "./useSettings";

const copy = settingsCopy.profile;

export function ProfilePanel({ me }: { me: Me }) {
  const toast = useToast();
  const update = useUpdateAccount();
  const { upload, remove } = useAvatar();
  const fileRef = useRef<HTMLInputElement>(null);
  const [bio, setBio] = useState(me.bio);
  const [mcNickname, setMcNickname] = useState(me.mc_nickname ?? "");
  const [errors, setErrors] = useState<Record<string, string>>({});

  async function onAvatar(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setErrors({});
    try {
      await upload.mutateAsync(file);
      toast({ title: settingsCopy.saved });
    } catch (error) {
      setErrors({ avatar: fieldErrors(error).avatar ?? generalError(error, settingsCopy.error) });
    }
  }

  async function onSave() {
    setErrors({});
    try {
      await update.mutateAsync({ bio, mc_nickname: mcNickname });
      toast({ title: settingsCopy.saved });
    } catch (error) {
      const fields = fieldErrors(error);
      setErrors(Object.keys(fields).length ? fields : { root: settingsCopy.error });
    }
  }

  return (
    <div className="flex max-w-xl flex-col gap-8">
      <div className="flex flex-col gap-3">
        <p className="text-sm font-medium">{copy.avatar}</p>
        <div className="flex items-center gap-6">
          <Avatar name={me.nickname} src={me.avatar_url} size={96} />
          <div className="flex flex-wrap gap-3">
            <Button
              variant="secondary"
              loading={upload.isPending}
              onClick={() => fileRef.current?.click()}
            >
              {copy.upload}
            </Button>
            {me.avatar_url && (
              <Button variant="ghost" loading={remove.isPending} onClick={() => remove.mutate()}>
                {copy.remove}
              </Button>
            )}
          </div>
        </div>
        <input
          ref={fileRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          className="sr-only"
          tabIndex={-1}
          aria-label={copy.avatar}
          onChange={onAvatar}
        />
        <p className={errors.avatar ? "text-meta text-danger" : "text-meta text-muted"}>
          {errors.avatar ?? copy.avatarHint}
        </p>
      </div>
      <Input label={copy.nickname} value={me.nickname} disabled readOnly />
      <form
        noValidate
        className="flex flex-col gap-6"
        onSubmit={(event) => {
          event.preventDefault();
          void onSave();
        }}
      >
        <FormError message={errors.root} />
        <Textarea
          label={copy.bio}
          hint={copy.bioHint}
          maxLength={160}
          rows={3}
          value={bio}
          onChange={(event) => setBio(event.target.value)}
          error={errors.bio}
        />
        <Input
          label={copy.mcNickname}
          hint={copy.mcNicknameHint}
          maxLength={16}
          value={mcNickname}
          onChange={(event) => setMcNickname(event.target.value)}
          error={errors.mc_nickname}
        />
        <Button type="submit" className="self-start" loading={update.isPending}>
          {settingsCopy.save}
        </Button>
      </form>
    </div>
  );
}
