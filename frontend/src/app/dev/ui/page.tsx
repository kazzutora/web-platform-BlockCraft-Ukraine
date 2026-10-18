import Link from "next/link";

import { Container } from "@/components/layout/Container";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { Card } from "@/components/ui/Card";
import { CardGrid } from "@/components/ui/CardGrid";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon, type IconName } from "@/components/ui/Icon";
import { IconButton } from "@/components/ui/IconButton";
import { Illustration, type IllustrationName } from "@/components/ui/Illustration";
import { Input } from "@/components/ui/Input";
import { SaveButton } from "@/components/ui/SaveButton";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import { StarRating } from "@/components/ui/StarRating";
import { Tabs } from "@/components/ui/Tabs";
import { Textarea } from "@/components/ui/Textarea";
import { ControlDemos } from "@/features/dev-ui/ControlDemos";
import { OverlayDemos } from "@/features/dev-ui/OverlayDemos";
import { ShowcaseSection } from "@/features/dev-ui/ShowcaseSection";
import { TokenSwatches } from "@/features/dev-ui/TokenSwatches";

const icons: IconName[] = [
  "home",
  "search",
  "plus",
  "bookmark",
  "heart",
  "star",
  "star-filled",
  "user",
  "users",
  "bell",
  "menu",
  "close",
  "chevron-down",
  "chevron-left",
  "chevron-right",
  "chevron-up",
  "check",
  "copy",
  "download",
  "upload",
  "external-link",
  "link",
  "share",
  "eye",
  "eye-off",
  "filter",
  "flag",
  "gamepad",
  "globe",
  "image",
  "info",
  "lock",
  "login",
  "logout",
  "moon",
  "sun",
  "more",
  "pencil",
  "reload",
  "server",
  "settings",
  "trash",
  "trophy",
  "warning",
  "blocks",
];

const illustrations: IllustrationName[] = [
  "home",
  "mods",
  "packs",
  "skins",
  "servers",
  "moments",
  "worlds",
  "empty",
  "void",
  "error",
];

const cards = [
  { title: "Sodium", meta: "1.21 · Fabric · ★ 4.8", illustration: "mods" as const },
  { title: "Complementary Shaders", meta: "1.21 · Iris · ★ 4.9", illustration: "worlds" as const },
  { title: "Лицар у зеленому", meta: "Slim · 128 збережень", illustration: "skins" as const },
  { title: "UA Survival", meta: "● 214 онлайн · Виживання", illustration: "servers" as const },
];

export default function DevUiPage() {
  return (
    <Container className="flex flex-col gap-16 py-12 md:py-16">
      <header className="flex flex-col gap-4">
        <p className="caps text-muted">Етап 1 · лише dev</p>
        <h1 className="text-h1">Дизайн-система</h1>
        <p className="max-w-prose text-muted">
          Усі примітиви в усіх станах. Перемикай тему в шапці й перевіряй на 375 і 1440 px. Шаблони
          сторінок:{" "}
          <Link className="underline" href="/dev/ui/catalog">
            каталог
          </Link>
          ,{" "}
          <Link className="underline" href="/dev/ui/detail">
            об’єкт
          </Link>
          ,{" "}
          <Link className="underline" href="/dev/ui/form">
            форма
          </Link>
          .
        </p>
      </header>

      <ShowcaseSection id="tokens" title="Кольори">
        <TokenSwatches />
      </ShowcaseSection>

      <ShowcaseSection id="type" title="Типографіка">
        <p className="text-display">Display</p>
        <p className="font-serif text-h1">Заголовок сторінки H1</p>
        <p className="font-serif text-h2">Заголовок секції H2</p>
        <p className="caps text-muted">Для твоєї версії</p>
        <p className="max-w-prose">
          Основний текст: Inter 16 px, висота рядка 1.6, не більше 65 символів у рядку. Знайди моди
          під свою версію, збережи скіни й сервери в колекції.
        </p>
        <p className="text-meta text-muted">1.21 · Fabric · ★ 4,6</p>
        <p className="text-4xl tabular-nums">1 284 онлайн</p>
      </ShowcaseSection>

      <ShowcaseSection id="buttons" title="Кнопки">
        <div className="flex flex-wrap items-center gap-3">
          <Button>Головна дія</Button>
          <Button variant="secondary">Другорядна</Button>
          <Button variant="ghost">Текстова</Button>
          <Button disabled>Недоступна</Button>
          <Button loading>Зберігаємо…</Button>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button size="lg">Завантажити для 1.21 · Fabric</Button>
          <Button size="lg" variant="secondary">
            <Icon name="plus" /> В колекцію
          </Button>
          <ButtonLink href="/dev/ui" size="lg" variant="ghost">
            Посилання-кнопка
          </ButtonLink>
        </div>
        <div className="flex flex-wrap items-center gap-1">
          <IconButton icon="search" label="Пошук" />
          <IconButton icon="share" label="Поділитися" />
          <IconButton icon="more" label="Ще" variant="secondary" />
          <IconButton icon="trash" label="Видалити" disabled />
        </div>
      </ShowcaseSection>

      <ShowcaseSection id="icons" title="Іконки">
        <ul className="grid grid-cols-6 gap-4 sm:grid-cols-9 lg:grid-cols-15">
          {icons.map((name) => (
            <li key={name} className="flex flex-col items-center gap-2" title={name}>
              <Icon name={name} />
              <span className="text-[0.625rem] text-muted">{name}</span>
            </li>
          ))}
        </ul>
      </ShowcaseSection>

      <ShowcaseSection id="fields" title="Поля">
        <div className="grid gap-6 md:grid-cols-2">
          <Input label="Нік" placeholder="Steve_UA" hint="3–24 символи: латиниця, цифри, _" />
          <Input label="Email" type="email" defaultValue="steve@" error="Введи коректну адресу" />
          <Input label="Недоступне поле" disabled defaultValue="1.21.4" />
          <Select
            label="Лоадер"
            placeholder="Обери лоадер"
            options={[
              { value: "fabric", label: "Fabric" },
              { value: "forge", label: "Forge" },
              { value: "neoforge", label: "NeoForge" },
            ]}
          />
          <div className="md:col-span-2">
            <Textarea label="Відгук" placeholder="Що сподобалося, що ні?" hint="До 1000 символів" />
          </div>
        </div>
      </ShowcaseSection>

      <ShowcaseSection id="chips" title="Чипи й фільтри">
        <div className="flex flex-wrap gap-2">
          <Chip tone="mods">Моди</Chip>
          <Chip tone="packs">Зборки</Chip>
          <Chip tone="skins">Скіни</Chip>
          <Chip tone="servers">Сервери</Chip>
          <Chip tone="moments">Моменти</Chip>
          <Chip>Без розділу</Chip>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone="accent" icon="check">
            Перевірено
          </Badge>
          <Badge>Новий</Badge>
          <Badge icon="users">214</Badge>
        </div>
        <ControlDemos />
      </ShowcaseSection>

      <ShowcaseSection id="tabs" title="Вкладки">
        <Tabs
          label="Сторінка мода"
          items={[
            { value: "about", label: "Опис", content: <p>Опис мода українською.</p> },
            { value: "versions", label: "Версії", content: <p>Список версій.</p> },
            { value: "reviews", label: "Відгуки", content: <p>Відгуки гравців.</p> },
            { value: "similar", label: "Схоже", content: <p>Схожі проєкти.</p> },
          ]}
        />
      </ShowcaseSection>

      <ShowcaseSection id="cards" title="Картки">
        <CardGrid>
          {cards.map((card, index) => (
            <Card
              key={card.title}
              href="/dev/ui/detail"
              title={card.title}
              meta={card.meta}
              cover={
                <div className="flex size-full items-center justify-center">
                  <Illustration name={card.illustration} size={120} />
                </div>
              }
              action={<SaveButton defaultSaved={index === 1} />}
            />
          ))}
        </CardGrid>
        <CardGrid>
          {Array.from({ length: 4 }, (_, index) => (
            <div key={index} className="flex flex-col gap-3">
              <Skeleton className="aspect-square w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          ))}
        </CardGrid>
      </ShowcaseSection>

      <ShowcaseSection id="overlays" title="Діалоги, шторки, поповери, тости">
        <OverlayDemos />
      </ShowcaseSection>

      <ShowcaseSection id="rating" title="Оцінка й аватари">
        <div className="flex flex-wrap items-center gap-6">
          <StarRating value={4.6} count={312} />
          <StarRating value={3.2} size={24} />
        </div>
        <div className="flex flex-wrap items-end gap-4">
          <Avatar name="Steve_UA" size={32} />
          <Avatar name="Alex" size={40} />
          <Avatar name="Мавка" size={64} />
          <Avatar name="Notch" size={96} />
          <Avatar name="Herobrine" size={128} />
        </div>
      </ShowcaseSection>

      <ShowcaseSection id="states" title="Стани">
        <div className="grid gap-6 md:grid-cols-2">
          <div className="border border-line">
            <EmptyState
              title="Тут поки порожньо. Збережи перший мод."
              action={<ButtonLink href="/mods">До модів</ButtonLink>}
            />
          </div>
          <div className="flex flex-col items-center justify-center gap-4 border border-line p-8 text-center">
            <Icon name="warning" size={48} />
            <p>Не вдалося завантажити список.</p>
            <Button variant="secondary">Спробувати ще</Button>
          </div>
          <div className="flex flex-col items-center justify-center gap-4 border border-line p-8 text-center md:col-span-2">
            <Icon name="lock" size={48} />
            <p>Увійди, щоб не загубити збережене.</p>
            <ButtonLink href="/login">Увійти</ButtonLink>
          </div>
        </div>
      </ShowcaseSection>

      <ShowcaseSection id="illustrations" title="Ілюстрації-заглушки">
        <ul className="grid grid-cols-2 gap-6 sm:grid-cols-5">
          {illustrations.map((name) => (
            <li key={name} className="flex flex-col items-center gap-2 border border-line p-4">
              <Illustration name={name} size={96} />
              <code className="text-meta text-muted">{name}</code>
            </li>
          ))}
        </ul>
      </ShowcaseSection>
    </Container>
  );
}
