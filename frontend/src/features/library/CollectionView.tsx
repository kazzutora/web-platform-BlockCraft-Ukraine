"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Container } from "@/components/layout/Container";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { CardGrid } from "@/components/ui/CardGrid";
import { Chip } from "@/components/ui/Chip";
import { Dialog } from "@/components/ui/Dialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { IconButton } from "@/components/ui/IconButton";
import { Tabs } from "@/components/ui/Tabs";
import { useToast } from "@/components/ui/useToast";
import { useMe } from "@/features/auth/useMe";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { ModCard } from "@/features/mods/ModCard";
import { ReportButton } from "@/features/moderation/ReportButton";
import { SkinCard } from "@/features/skins/SkinCard";
import { Comments } from "@/features/social/Comments";
import { api } from "@/lib/api/client";
import { plural } from "@/lib/plural";
import { queryKeys } from "@/lib/query-keys";

import { CollectionForm, parseEditors } from "./CollectionForm";
import { libraryCopy } from "./copy";
import { LikeButton } from "./LikeButton";
import { SaveToggle } from "./SaveToggle";
import type { CollectionDetail, CollectionItem } from "./types";

const copy = libraryCopy.collection;

type CollectionViewProps = { initial: CollectionDetail; shareToken: string };

export function CollectionView({ initial, shareToken }: CollectionViewProps) {
  const key = queryKeys.library.collection(initial.id);
  const { data: collection = initial } = useQuery({
    queryKey: key,
    initialData: initial,
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/collections/{id}", {
        params: { path: { id: initial.id }, query: shareToken ? { share_token: shareToken } : {} },
      });
      if (!data) throw new Error("collection");
      return data;
    },
  });
  const { me } = useMe();
  const isOwner = me?.nickname === collection.owner.nickname;

  return (
    <Container className="flex flex-col gap-12 py-12 md:py-16">
      <header className="flex flex-col gap-6">
        <div className="flex flex-wrap items-center gap-3">
          <Chip tone="packs">{copy.chip}</Chip>
          {collection.can_edit && collection.visibility !== "public" && (
            <Badge icon={collection.visibility === "private" ? "lock" : "link"}>
              {libraryCopy.visibility[collection.visibility]}
            </Badge>
          )}
        </div>
        <h1 className="text-h1">{collection.title}</h1>
        {collection.description && (
          <p className="max-w-prose text-muted">{collection.description}</p>
        )}
        <p className="flex flex-wrap items-center gap-3 text-meta text-muted">
          <Link
            href={`/u/${collection.owner.nickname}`}
            className="flex items-center gap-2 text-text hover:underline"
          >
            <Avatar name={collection.owner.nickname} src={collection.owner.avatar_url} size={32} />
            {collection.owner.nickname}
          </Link>
          <span>{plural(collection.items_count, libraryCopy.card.items)}</span>
        </p>
        <div className="flex flex-wrap items-center gap-3">
          {collection.can_edit ? (
            <OwnerActions collection={collection} isOwner={isOwner} />
          ) : (
            <VisitorActions collection={collection} shareToken={shareToken} />
          )}
        </div>
      </header>

      <Tabs
        label={copy.tabsLabel}
        items={[
          {
            value: "items",
            label: `${copy.tabs.items} · ${collection.items_count}`,
            content: <Items collection={collection} />,
          },
          // Link-only collections are not listed, so they take no comments from visitors
          ...(collection.visibility === "public" || collection.can_edit
            ? [
                {
                  value: "comments",
                  label: copy.tabs.comments,
                  content: <Comments kind="collection" id={String(collection.id)} />,
                },
              ]
            : []),
        ]}
      />
    </Container>
  );
}

function shareUrl(collection: CollectionDetail): string {
  const url = new URL(`/c/${collection.id}`, window.location.origin);
  if (collection.visibility === "link" && collection.share_token) {
    url.searchParams.set("token", collection.share_token);
  }
  return url.toString();
}

function OwnerActions({ collection, isOwner }: { collection: CollectionDetail; isOwner: boolean }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const key = queryKeys.library.collection(collection.id);

  const remove = useMutation({
    mutationFn: () =>
      api.DELETE("/api/v1/collections/{id}", { params: { path: { id: collection.id } } }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.library.all });
      router.push("/me/collections");
    },
  });

  return (
    <>
      <Dialog
        title={copy.editTitle}
        open={editing}
        onOpenChange={setEditing}
        trigger={
          <Button variant="secondary" size="lg">
            <Icon name="pencil" />
            {copy.edit}
          </Button>
        }
      >
        <CollectionForm
          withEditors={isOwner}
          submitLabel={libraryCopy.form.save}
          initial={{
            title: collection.title,
            description: collection.description,
            visibility: collection.visibility,
            editors: collection.editors.join(", "),
          }}
          onSubmit={async (values) => {
            const { data, error } = await api.PATCH("/api/v1/collections/{id}", {
              params: { path: { id: collection.id } },
              body: {
                title: values.title,
                description: values.description,
                visibility: values.visibility,
                ...(isOwner ? { editors: parseEditors(values.editors) } : {}),
              },
            });
            if (!data) throw error;
            queryClient.setQueryData(key, data);
            setEditing(false);
          }}
        />
      </Dialog>
      {collection.visibility !== "private" && (
        <Button
          variant="secondary"
          size="lg"
          onClick={async () => {
            await navigator.clipboard.writeText(shareUrl(collection));
            toast({ title: copy.copied });
          }}
        >
          <Icon name="link" />
          {copy.share}
        </Button>
      )}
      {isOwner && (
        <Dialog
          title={copy.deleteTitle}
          description={copy.deleteText}
          open={deleting}
          onOpenChange={setDeleting}
          trigger={<Button variant="ghost">{copy.delete}</Button>}
          footer={
            <>
              <Button variant="ghost" onClick={() => setDeleting(false)}>
                {copy.cancel}
              </Button>
              <Button loading={remove.isPending} onClick={() => remove.mutate()}>
                {copy.deleteConfirm}
              </Button>
            </>
          }
        />
      )}
    </>
  );
}

function VisitorActions({
  collection,
  shareToken,
}: {
  collection: CollectionDetail;
  shareToken: string;
}) {
  const router = useRouter();
  const toast = useToast();
  const requireAuth = useRequireAuth();
  const copyCollection = useMutation({
    mutationFn: async () => {
      const { data } = await api.POST("/api/v1/collections/{id}/copy", {
        params: {
          path: { id: collection.id },
          query: shareToken ? { share_token: shareToken } : {},
        },
      });
      if (!data) throw new Error("copy");
      return data;
    },
    onSuccess: (data) => {
      toast({ title: copy.copiedCollection });
      router.push(`/c/${data.id}`);
    },
  });

  return (
    <>
      <Button
        size="lg"
        loading={copyCollection.isPending}
        onClick={() => requireAuth(() => copyCollection.mutate())}
      >
        <Icon name="copy" />
        {copy.copy}
      </Button>
      {collection.visibility === "public" && (
        <>
          <LikeButton
            kind="collection"
            id={String(collection.id)}
            liked={collection.is_liked}
            count={collection.likes_count}
          />
          <SaveToggle
            kind="collection"
            id={String(collection.id)}
            saved={collection.is_favorited}
          />
          <ReportButton kind="collection" id={String(collection.id)} />
        </>
      )}
    </>
  );
}

function Items({ collection }: { collection: CollectionDetail }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const key = queryKeys.library.collection(collection.id);

  const reorder = useMutation({
    mutationFn: async (items: CollectionItem[]) => {
      const { data } = await api.POST("/api/v1/collections/{id}/reorder", {
        params: { path: { id: collection.id } },
        body: { item_ids: items.map((item) => item.id) },
      });
      if (!data) throw new Error("reorder");
      return data;
    },
    onMutate: (items) => {
      const previous = queryClient.getQueryData<CollectionDetail>(key);
      queryClient.setQueryData<CollectionDetail>(
        key,
        (current) => current && { ...current, items },
      );
      return previous;
    },
    onError: (_error, _items, previous) => {
      queryClient.setQueryData(key, previous);
      toast({ title: libraryCopy.addToCollection.error, tone: "danger" });
    },
    onSuccess: (data) => queryClient.setQueryData(key, data),
  });

  const remove = useMutation({
    mutationFn: async (item: CollectionItem) => {
      const { data } = await api.DELETE("/api/v1/collections/{id}/items/{item_id}", {
        params: { path: { id: collection.id, item_id: item.id } },
      });
      if (!data) throw new Error("remove");
      return data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(key, data);
      void queryClient.invalidateQueries({ queryKey: queryKeys.library.myCollections() });
    },
  });

  function move(index: number, delta: number) {
    const items = [...collection.items];
    const [item] = items.splice(index, 1);
    items.splice(index + delta, 0, item);
    reorder.mutate(items);
  }

  if (!collection.items.length) {
    return <EmptyState title={copy.empty} illustration="packs" />;
  }

  return (
    <CardGrid>
      {collection.items.map((item, index) => (
        <div key={item.id} className="flex flex-col gap-2">
          {item.mod ? (
            <ModCard project={item.mod} />
          ) : item.skin ? (
            <SkinCard skin={item.skin} />
          ) : (
            <p className="border border-line p-4 text-sm text-muted">{copy.unknownItem}</p>
          )}
          {item.note && <p className="text-meta">{item.note}</p>}
          {collection.can_edit && (
            <div className="flex items-center gap-1">
              <IconButton
                icon="chevron-left"
                label={copy.moveUp}
                disabled={index === 0}
                onClick={() => move(index, -1)}
              />
              <IconButton
                icon="chevron-right"
                label={copy.moveDown}
                disabled={index === collection.items.length - 1}
                onClick={() => move(index, 1)}
              />
              <IconButton icon="trash" label={copy.remove} onClick={() => remove.mutate(item)} />
            </div>
          )}
        </div>
      ))}
    </CardGrid>
  );
}
