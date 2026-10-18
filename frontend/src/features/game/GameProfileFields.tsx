"use client";

import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { Popover } from "@/components/ui/Popover";
import { Select } from "@/components/ui/Select";

import {
  type Edition,
  type GameVersion,
  type Interest,
  type Loader,
  editionOptions,
  gameVersionOptions,
  interestOptions,
  loaderOptions,
} from "./labels";

const copy = {
  version: "Версія гри",
  versionPlaceholder: "Обери версію",
  howTo: "Як дізнатися свою версію?",
  howToJava:
    "Java: версія написана в лаунчері біля кнопки «Грати» та в лівому нижньому куті головного меню гри.",
  howToBedrock: "Bedrock: «Налаштування» — номер версії в самому низу сторінки.",
  loader: "Лоадер модів",
  edition: "Видання",
  interests: "Що тобі цікаво",
};

export type GameProfileValues = {
  game_version: GameVersion | "";
  loader: Loader | "";
  edition: Edition;
  interests: Interest[];
};

type Props = {
  values: GameProfileValues;
  onChange: (values: GameProfileValues) => void;
  errors?: Partial<Record<keyof GameProfileValues, string>>;
};

/** Version, loader, edition and interests — shared by onboarding and settings. */
export function GameProfileFields({ values, onChange, errors = {} }: Props) {
  const set = <K extends keyof GameProfileValues>(key: K, value: GameProfileValues[K]) =>
    onChange({ ...values, [key]: value });

  return (
    <div className="flex flex-col gap-8">
      <ChoiceChips
        label={copy.edition}
        options={editionOptions}
        value={values.edition}
        onChange={(value) => set("edition", value)}
        error={errors.edition}
      />
      <div className="flex flex-col gap-2">
        <Select
          label={copy.version}
          placeholder={copy.versionPlaceholder}
          options={gameVersionOptions}
          value={values.game_version}
          onChange={(event) => set("game_version", event.target.value as GameVersion | "")}
          error={errors.game_version}
        />
        <Popover
          label={copy.howTo}
          align="start"
          trigger={
            <button type="button" className="self-start text-sm underline underline-offset-4">
              {copy.howTo}
            </button>
          }
        >
          <div className="flex flex-col gap-2 text-sm">
            <p>{copy.howToJava}</p>
            <p>{copy.howToBedrock}</p>
          </div>
        </Popover>
      </div>
      {values.edition === "java" && (
        <ChoiceChips
          label={copy.loader}
          options={loaderOptions}
          value={values.loader}
          onChange={(value) => set("loader", value)}
          error={errors.loader}
        />
      )}
      <ChoiceChips
        multiple
        label={copy.interests}
        options={interestOptions}
        value={values.interests}
        onChange={(value) => set("interests", value)}
        error={errors.interests}
      />
    </div>
  );
}
