import { useEffect, useId, useMemo, useRef, useState } from "react";

export default function SearchSelect({
  label,
  value,
  options,
  onChange,
  placeholder,
  disabled = false,
  required = false,
}) {
  const listId = useId();
  const wrapRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(value || "");

  useEffect(() => {
    setQuery(value || "");
  }, [value]);

  useEffect(() => {
    function onDocClick(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        setOpen(false);
        setQuery(value || "");
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [value]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter((item) => item.toLowerCase().includes(q));
  }, [options, query]);

  function pick(item) {
    onChange(item);
    setQuery(item);
    setOpen(false);
  }

  return (
    <label className="field" ref={wrapRef}>
      <span>{label}</span>
      <input
        type="text"
        value={query}
        placeholder={placeholder}
        disabled={disabled}
        required={required}
        autoComplete="off"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        onFocus={() => !disabled && setOpen(true)}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          if (value) onChange("");
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" && filtered.length === 1) {
            e.preventDefault();
            pick(filtered[0]);
          }
        }}
      />
      {open && !disabled && (
        <ul className="dropdown" id={listId} role="listbox">
          {filtered.length === 0 && (
            <li className="dropdown-empty">Ничего не найдено</li>
          )}
          {filtered.map((item) => (
            <li key={item}>
              <button type="button" onMouseDown={() => pick(item)}>
                {item}
              </button>
            </li>
          ))}
        </ul>
      )}
    </label>
  );
}
