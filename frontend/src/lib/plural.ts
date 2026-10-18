const rules = new Intl.PluralRules("uk-UA");

export type PluralForms = {
  /** 1, 21, 31… — «мод» */
  one: string;
  /** 2–4, 22–24… — «моди» */
  few: string;
  /** 0, 5–20, 25… — «модів» */
  many: string;
};

/** Ukrainian plural: `plural(5, { one: "мод", few: "моди", many: "модів" })` → «5 модів». */
export function plural(count: number, forms: PluralForms): string {
  const rule = rules.select(count);
  const word = rule === "one" ? forms.one : rule === "few" ? forms.few : forms.many;
  return `${count.toLocaleString("uk-UA")} ${word}`;
}
