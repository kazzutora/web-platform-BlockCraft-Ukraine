"use client";

import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { type FormEvent, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import { StarRating } from "@/components/ui/StarRating";
import { StarRatingInput } from "@/components/ui/StarRatingInput";
import { Textarea } from "@/components/ui/Textarea";
import { useToast } from "@/components/ui/useToast";
import { FormError } from "@/features/auth/FormError";
import { useMe } from "@/features/auth/useMe";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import type { Kind } from "@/features/library/types";
import { formatDate } from "@/features/mods/format";
import { api } from "@/lib/api/client";
import { fieldErrors } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";
import { cn } from "@/lib/cn";
import { queryKeys } from "@/lib/query-keys";

import { socialCopy } from "./copy";

const copy = socialCopy.reviews;

type Review = components["schemas"]["Review"];
type Sort = "helpful" | "new";

type ReviewsProps = {
  kind: Kind;
  id: string;
  /** False for the owner of the object: owners do not rate their own projects. */
  canReview?: boolean;
  /** Extra line under the form, e.g. how often a server review can change. */
  hint?: string;
};

/** Rating summary, the player's own review and everybody else's. */
export function Reviews({ kind, id, canReview = true, hint }: ReviewsProps) {
  const [sort, setSort] = useState<Sort>("helpful");
  const reviews = useInfiniteQuery({
    queryKey: queryKeys.social.reviews(kind, id, sort),
    initialPageParam: 1,
    queryFn: async ({ pageParam }) => {
      const { data } = await api.GET("/api/v1/reviews", {
        params: { query: { kind, id, sort, page: pageParam } },
      });
      if (!data) throw new Error("reviews");
      return data;
    },
    getNextPageParam: (last) => last.next_page ?? undefined,
  });

  if (reviews.isPending) return <Skeleton className="h-48 w-full" />;
  if (!reviews.data) return null;

  const first = reviews.data.pages[0];
  const summary = first.summary;
  const results = reviews.data.pages.flatMap((page) => page.results);

  return (
    <div className="flex flex-col gap-10">
      <div className="grid gap-10 md:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        <Summary summary={summary} />
        {canReview ? (
          <div className="flex flex-col gap-3">
            <ReviewForm kind={kind} id={id} mine={summary.my_review} />
            {hint && <p className="text-meta text-muted">{hint}</p>}
          </div>
        ) : (
          <p className="text-muted">{copy.ownObject}</p>
        )}
      </div>

      {results.length > 0 && (
        <div className="flex flex-col gap-4">
          <div className="w-48">
            <Select
              label={copy.sort}
              hideLabel
              value={sort}
              options={copy.sorts}
              onChange={(event) => setSort(event.target.value as Sort)}
            />
          </div>
          <ul className="flex flex-col">
            {results.map((review) => (
              <ReviewItem key={review.id} review={review} kind={kind} id={id} />
            ))}
          </ul>
          {reviews.hasNextPage && (
            <Button
              variant="secondary"
              className="self-center"
              loading={reviews.isFetchingNextPage}
              onClick={() => void reviews.fetchNextPage()}
            >
              {copy.more}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

function Summary({ summary }: { summary: components["schemas"]["ReviewSummary"] }) {
  if (!summary.rating_count) {
    return <p className="text-muted">{copy.noReviews}</p>;
  }
  const max = Math.max(...Object.values(summary.distribution), 1);
  return (
    <div className="flex flex-col gap-4">
      <p className="font-serif text-h1 leading-none tabular-nums">
        {summary.rating_avg.toLocaleString("uk-UA", { maximumFractionDigits: 1 })}
      </p>
      <StarRating value={summary.rating_avg} count={summary.rating_count} size={24} />
      <ul className="flex flex-col gap-1">
        {["5", "4", "3", "2", "1"].map((stars) => (
          <li key={stars} className="flex items-center gap-3 text-meta">
            <span className="w-3 tabular-nums">{stars}</span>
            <span className="h-2 flex-1 bg-line" aria-hidden>
              <span
                className="block h-full bg-text"
                style={{ width: `${((summary.distribution[stars] ?? 0) / max) * 100}%` }}
              />
            </span>
            <span className="w-8 text-right text-muted tabular-nums">
              {summary.distribution[stars] ?? 0}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ReviewForm({ kind, id, mine }: { kind: Kind; id: string; mine: Review | null }) {
  const { me } = useMe();
  const requireAuth = useRequireAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [stars, setStars] = useState(mine?.stars ?? 0);
  const [text, setText] = useState(mine?.text ?? "");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const save = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.PUT("/api/v1/reviews", { body: { kind, id, stars, text } });
      if (!data) throw error;
      return data;
    },
    onSuccess: () => {
      toast({ title: copy.saved });
      void queryClient.invalidateQueries({ queryKey: queryKeys.social.reviewsOf(kind, id) });
    },
    onError: (error) => {
      const fields = fieldErrors(error);
      setErrors(Object.keys(fields).length ? fields : { root: copy.error });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    setErrors({});
    requireAuth(() => {
      if (stars) save.mutate();
    });
  }

  if (!me) {
    return (
      <div className="flex flex-col items-start gap-3">
        <p className="caps text-muted">{copy.yours}</p>
        <Button variant="secondary" onClick={() => requireAuth()}>
          {copy.loginToRate}
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-4">
      <FormError message={errors.root} />
      <StarRatingInput
        label={copy.yours}
        name={`review-${kind}-${id}`}
        value={stars}
        onValueChange={setStars}
      />
      <Textarea
        label={copy.text}
        hint={copy.textHint}
        maxLength={1000}
        rows={3}
        value={text}
        onChange={(event) => setText(event.target.value)}
        error={errors.text}
      />
      <Button type="submit" className="self-start" loading={save.isPending} disabled={!stars}>
        {mine ? copy.update : copy.submit}
      </Button>
    </form>
  );
}

function ReviewItem({ review, kind, id }: { review: Review; kind: Kind; id: string }) {
  const requireAuth = useRequireAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [state, setState] = useState({ vote: review.my_vote, helpful: review.helpful_count });
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: queryKeys.social.reviewsOf(kind, id) });

  const vote = useMutation({
    mutationFn: async (isHelpful: boolean) => {
      const { data } = await api.POST("/api/v1/reviews/{id}/vote", {
        params: { path: { id: review.id } },
        body: { is_helpful: isHelpful },
      });
      if (!data) throw new Error("vote");
      return data;
    },
    onMutate: (isHelpful) => {
      const previous = state;
      const helpful = state.helpful + (isHelpful ? 1 : 0) - (state.vote === true ? 1 : 0);
      setState({ vote: isHelpful, helpful });
      return previous;
    },
    onError: (_error, _vote, previous) => previous && setState(previous),
    onSuccess: (data) => setState({ vote: data.my_vote, helpful: data.helpful_count }),
  });

  const remove = useMutation({
    mutationFn: async () => {
      await api.DELETE("/api/v1/reviews/{id}", { params: { path: { id: review.id } } });
    },
    onSuccess: () => {
      toast({ title: copy.deleted });
      void invalidate();
    },
  });

  return (
    <li className="flex flex-col gap-3 border-b border-line py-6">
      <div className="flex items-center gap-3">
        <Avatar name={review.user.nickname} src={review.user.avatar_url} size={32} />
        <Link href={`/u/${review.user.nickname}`} className="font-medium hover:underline">
          {review.user.nickname}
        </Link>
        <StarRating value={review.stars} />
        <span className="text-meta text-muted">{formatDate(review.updated_at)}</span>
      </div>
      {review.text && <p className="max-w-prose whitespace-pre-line">{review.text}</p>}
      <div className="flex flex-wrap items-center gap-2">
        {review.is_mine ? (
          <Button
            variant="ghost"
            className="px-0"
            loading={remove.isPending}
            onClick={() => remove.mutate()}
          >
            {copy.delete}
          </Button>
        ) : (
          <>
            {[true, false].map((isHelpful) => (
              <button
                key={String(isHelpful)}
                type="button"
                aria-pressed={state.vote === isHelpful}
                onClick={() => requireAuth(() => vote.mutate(isHelpful))}
                className={cn(
                  "inline-flex h-9 items-center gap-2 border px-3 text-sm",
                  state.vote === isHelpful
                    ? "border-text bg-text text-bg"
                    : "border-line hover:border-text",
                )}
              >
                {isHelpful ? copy.helpful : copy.notHelpful}
                {isHelpful && (
                  <span className="tabular-nums">{copy.helpfulCount(state.helpful)}</span>
                )}
              </button>
            ))}
          </>
        )}
      </div>
    </li>
  );
}
