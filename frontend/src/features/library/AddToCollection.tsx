"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Checkbox } from "@/components/ui/Checkbox";
import { Icon } from "@/components/ui/Icon";
import { Input } from "@/components/ui/Input";
import { Popover } from "@/components/ui/Popover";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/useToast";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { libraryCopy } from "./copy";
import type { Kind, MyCollection } from "./types";

const copy = libraryCopy.addToCollection;

/** «В колекцію»: the player's collections with a check for those that hold the object. */
export function AddToCollection({ kind, id }: { kind: Kind; id: string }) {
  const requireAuth = useRequireAuth();
  const [open, setOpen] = useState(false);

  return (
    <Popover
      label={copy.label}
      open={open}
      onOpenChange={(next) => {
        if (!next) setOpen(false);
        else requireAuth(() => setOpen(true));
      }}
      trigger={
        <Button variant="secondary" size="lg">
          <Icon name="plus" />
          {copy.button}
        </Button>
      }
    >
      {open && <CollectionsChecklist kind={kind} id={id} />}
    </Popover>
  );
}

function CollectionsChecklist({ kind, id }: { kind: Kind; id: string }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const key = queryKeys.library.myCollections(kind, id);
  const [title, setTitle] = useState("");

  const collections = useQuery({
    queryKey: key,
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/me/collections", { params: { query: { kind, id } } });
      if (!data) throw new Error("me/collections");
      return data;
    },
  });

  const toggle = useMutation({
    mutationFn: async (collection: MyCollection) => {
      const path = { id: collection.id };
      const result =
        collection.contains && collection.item_id
          ? await api.DELETE("/api/v1/collections/{id}/items/{item_id}", {
              params: { path: { ...path, item_id: collection.item_id } },
            })
          : await api.POST("/api/v1/collections/{id}/items", {
              params: { path },
              body: { kind, id },
            });
      if (!result.data) throw new Error("collection items");
      return collection;
    },
    onMutate: async (collection) => {
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<MyCollection[]>(key);
      queryClient.setQueryData<MyCollection[]>(key, (list) =>
        list?.map((item) =>
          item.id === collection.id ? { ...item, contains: !item.contains } : item,
        ),
      );
      return previous;
    },
    onError: (_error, _collection, previous) => {
      queryClient.setQueryData(key, previous);
      toast({ title: copy.error, tone: "danger" });
    },
    onSuccess: (collection) =>
      toast({
        title: collection.contains ? copy.removed(collection.title) : copy.added(collection.title),
      }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: queryKeys.library.all }),
  });

  const create = useMutation({
    mutationFn: async (name: string) => {
      const created = await api.POST("/api/v1/collections", { body: { title: name } });
      if (!created.data) throw new Error("create collection");
      const added = await api.POST("/api/v1/collections/{id}/items", {
        params: { path: { id: created.data.id } },
        body: { kind, id },
      });
      if (!added.data) throw new Error("add item");
      return created.data;
    },
    onSuccess: (collection) => {
      setTitle("");
      toast({ title: copy.added(collection.title) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.library.all });
    },
    onError: () => toast({ title: copy.error, tone: "danger" }),
  });

  function onCreate(event: FormEvent) {
    event.preventDefault();
    if (title.trim()) create.mutate(title.trim());
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="caps text-muted">{copy.label}</p>
      {collections.isPending ? (
        <div role="status" className="flex flex-col gap-2">
          <span className="sr-only">{copy.loading}</span>
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-6 w-2/3" />
        </div>
      ) : collections.data?.length ? (
        <ul className="flex max-h-60 flex-col gap-3 overflow-y-auto">
          {collections.data.map((collection) => (
            <li key={collection.id}>
              <Checkbox
                label={collection.title}
                checked={collection.contains}
                onChange={() => toggle.mutate(collection)}
              />
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted">{copy.empty}</p>
      )}
      <form onSubmit={onCreate} className="flex items-end gap-2 border-t border-line pt-4">
        <div className="flex-1">
          <Input
            label={copy.newTitle}
            maxLength={80}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="h-10"
          />
        </div>
        <Button type="submit" loading={create.isPending} disabled={!title.trim()}>
          {copy.create}
        </Button>
      </form>
    </div>
  );
}
