"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Icon } from "@/components/ui/Icon";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { CollectionForm } from "./CollectionForm";
import { libraryCopy } from "./copy";

/** Opens the form and goes to the new collection. */
export function NewCollectionButton() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  return (
    <Dialog
      title={libraryCopy.addToCollection.newTitle}
      open={open}
      onOpenChange={setOpen}
      trigger={
        <Button size="lg">
          <Icon name="plus" />
          {libraryCopy.addToCollection.newTitle}
        </Button>
      }
    >
      <CollectionForm
        submitLabel={libraryCopy.form.create}
        onSubmit={async (values) => {
          const { data, error } = await api.POST("/api/v1/collections", {
            body: {
              title: values.title,
              description: values.description,
              visibility: values.visibility,
            },
          });
          if (!data) throw error;
          await queryClient.invalidateQueries({ queryKey: queryKeys.library.all });
          setOpen(false);
          router.push(`/c/${data.id}`);
        }}
      />
    </Dialog>
  );
}
