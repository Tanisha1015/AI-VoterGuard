interface FormFieldProps {
  id: string;
  label: string;
  hint?: string;
  /** Already-translated error text. */
  error?: string;
  value: string;
  onChange: (value: string) => void;
  inputMode?: "text" | "numeric";
}

/** Labelled text input (44px+ tall) with optional hint and inline error linked via aria-describedby. */
export default function FormField({ id, label, hint, error, value, onChange, inputMode = "text" }: FormFieldProps) {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div>
      <label htmlFor={id} className="block font-medium text-slate-800">
        {label}
      </label>
      {hint && (
        <p id={hintId} className="text-sm text-slate-600">
          {hint}
        </p>
      )}
      <input
        id={id}
        type="text"
        inputMode={inputMode}
        autoComplete="off"
        required
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={`mt-1 block min-h-11 w-full rounded-lg border-2 bg-white px-3 py-2 text-base text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 ${
          error ? "border-red-700" : "border-slate-400"
        }`}
      />
      {error && (
        <p id={errorId} className="mt-1 text-sm font-medium text-red-800">
          <span aria-hidden="true">⚠ </span>
          {error}
        </p>
      )}
    </div>
  );
}
