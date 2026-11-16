import uz from "./locales/uz.json";
import ru from "./locales/ru.json";
import en from "./locales/en.json";
export const dictionaries = { uz, ru, en } as const;
export type Language = keyof typeof dictionaries;
export type TranslationKey = keyof typeof uz;
export function translate(language: Language, key: TranslationKey): string {
  return dictionaries[language][key] ?? uz[key] ?? key;
}
export function getMissingTranslations() {
  const keys = Object.keys(uz) as TranslationKey[];
  return (Object.keys(dictionaries) as Language[]).flatMap((language) =>
    keys.filter((key) => !dictionaries[language][key]).map((key) => ({ language, key }))
  );
}