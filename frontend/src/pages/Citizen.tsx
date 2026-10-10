import { useId, useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { citizenLookup } from "../api/core";
import type { CitizenLookupRequest, CitizenLookupResponse } from "../api/types";
import { useLang } from "../i18n";
import FormField from "../components/FormField";
import CitizenResult from "../components/CitizenResult";
import { buildRequest, EMPTY_FORM, errorKey, validate, type FieldErrors, type FieldName, type FormValues } from "./citizenForm";

/** Citizen roll lookup page (route "/"). Stores nothing beyond the API response in memory. */
export default function Citizen() {
  const { t } = useTranslation();
  const lang = useLang();
  const baseId = useId();

  const [values, setValues] = useState<FormValues>(EMPTY_FORM);
  const [useEpic, setUseEpic] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});

  const lookup = useMutation<CitizenLookupResponse, unknown, CitizenLookupRequest>({
    mutationFn: (body) => citizenLookup(body),
  });

  const id = (field: FieldName) => `${baseId}-${field}`;
  const err = (field: FieldName) => (errors[field] ? t(errors[field]) : undefined);

  const set = (field: FieldName) => (value: string) => {
    setValues((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  function switchMode(next: boolean) {
    setUseEpic(next);
    setErrors({});
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const found = validate(values, useEpic);
    setErrors(found);
    const first = Object.keys(found)[0] as FieldName | undefined;
    if (first) {
      document.getElementById(id(first))?.focus();
      return;
    }
    lookup.mutate(buildRequest(values, useEpic, lang));
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <section aria-labelledby={`${baseId}-title`}>
        <h1 id={`${baseId}-title`} className="text-2xl font-bold text-slate-900">
          {t("citizen.title")}
        </h1>
        <p className="mt-2 text-slate-700">{t("citizen.intro")}</p>
      </section>

      <form
        noValidate
        aria-label={t("citizen.form_label")}
        onSubmit={onSubmit}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"
      >
        <p className="text-sm text-slate-600">{t("citizen.required_note")}</p>

        <label className="flex min-h-11 cursor-pointer items-center gap-3">
          <input
            type="checkbox"
            role="switch"
            checked={useEpic}
            onChange={(e) => switchMode(e.target.checked)}
            className="h-6 w-6 accent-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
          />
          <span className="font-medium text-slate-800">{t("citizen.use_epic")}</span>
        </label>

        {useEpic ? (
          <FormField
            id={id("epic_no")}
            label={t("citizen.epic_no")}
            hint={t("citizen.epic_hint")}
            error={err("epic_no")}
            value={values.epic_no}
            onChange={set("epic_no")}
          />
        ) : (
          <>
            <FormField
              id={id("name")}
              label={t("citizen.name")}
              hint={t("citizen.name_hint")}
              error={err("name")}
              value={values.name}
              onChange={set("name")}
            />
            <FormField
              id={id("relative_name")}
              label={t("citizen.relative_name")}
              error={err("relative_name")}
              value={values.relative_name}
              onChange={set("relative_name")}
            />
            <FormField
              id={id("part_no")}
              label={t("citizen.part_no")}
              hint={t("citizen.part_no_hint")}
              error={err("part_no")}
              value={values.part_no}
              onChange={set("part_no")}
              inputMode="numeric"
            />
          </>
        )}

        <button
          type="submit"
          disabled={lookup.isPending}
          aria-busy={lookup.isPending}
          className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-lg bg-blue-700 px-5 text-base font-semibold text-white hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 disabled:cursor-wait disabled:opacity-70 sm:w-auto"
        >
          {lookup.isPending && (
            <span aria-hidden="true" className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
          )}
          {lookup.isPending ? t("citizen.submitting") : t("citizen.submit")}
        </button>
      </form>

      <section aria-live="polite" aria-label={t("result.region_label")}>
        {lookup.isError && (
          <div role="alert" className="rounded-xl border-2 border-slate-300 bg-white p-4 text-slate-800">
            <span aria-hidden="true">ⓘ </span>
            {t(errorKey(lookup.error))}
          </div>
        )}
        {lookup.isSuccess && <CitizenResult result={lookup.data} onUseEpic={() => switchMode(true)} />}
      </section>
    </div>
  );
}
