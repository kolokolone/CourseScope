'use client';

import * as React from 'react';

import { useGeoCities } from '@/hooks/useGeo';
import type { GeoCityItem } from '@/types/api';

type CityAutocompleteProps = {
  value: string;
  onChange: (value: string) => void;
  onSelectionChange?: (selection: GeoCityItem | null) => void;
  placeholder?: string;
  className?: string;
};

function useDebouncedValue(value: string, delayMs: number) {
  const [debounced, setDebounced] = React.useState(value);
  React.useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timer);
  }, [delayMs, value]);
  return debounced;
}

export function CityAutocomplete({ value, onChange, onSelectionChange, placeholder, className }: CityAutocompleteProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [activeIndex, setActiveIndex] = React.useState(-1);
  const [hasTyped, setHasTyped] = React.useState(false);

  const listboxId = React.useId();
  const debounced = useDebouncedValue(value.trim(), 300);
  const queryEnabled = debounced.length >= 2;

  const citiesQuery = useGeoCities(debounced, {
    limit: 8,
    language: 'fr',
    enabled: queryEnabled,
  });

  const options = citiesQuery.data?.results ?? [];

  React.useEffect(() => {
    setActiveIndex(options.length > 0 ? 0 : -1);
  }, [options.length]);

  const close = () => {
    setIsOpen(false);
    setActiveIndex(-1);
  };

  const commitSelection = (item: GeoCityItem) => {
    onChange(item.label);
    onSelectionChange?.(item);
    setHasTyped(false);
    close();
  };

  return (
    <div className="relative mt-1">
      <input
        value={value}
        placeholder={placeholder}
        className={className}
        role="combobox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        aria-autocomplete="list"
        aria-activedescendant={activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined}
        onFocus={() => {
          if (options.length > 0) setIsOpen(true);
        }}
        onChange={(e) => {
          const next = e.target.value;
          onChange(next);
          onSelectionChange?.(null);
          setHasTyped(true);
          setIsOpen(next.trim().length >= 2);
        }}
        onBlur={() => {
          window.setTimeout(() => {
            if (hasTyped) {
              onSelectionChange?.(null);
            }
            close();
          }, 120);
        }}
        onKeyDown={(e) => {
          if (!isOpen || options.length === 0) {
            if (e.key === 'ArrowDown' && options.length > 0) {
              e.preventDefault();
              setIsOpen(true);
              setActiveIndex(0);
            }
            return;
          }
          if (e.key === 'ArrowDown') {
            e.preventDefault();
            setActiveIndex((prev) => (prev + 1) % options.length);
          } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setActiveIndex((prev) => (prev <= 0 ? options.length - 1 : prev - 1));
          } else if (e.key === 'Enter') {
            e.preventDefault();
            if (activeIndex >= 0 && activeIndex < options.length) {
              const item = options[activeIndex];
              if (item) commitSelection(item);
            }
          } else if (e.key === 'Escape') {
            e.preventDefault();
            close();
          }
        }}
      />

      {isOpen ? (
        <div
          id={listboxId}
          role="listbox"
          className="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded-md border bg-popover p-1 shadow"
        >
          {citiesQuery.isFetching ? <div className="px-2 py-1.5 text-xs text-muted-foreground">Recherche...</div> : null}
          {!citiesQuery.isFetching && options.length === 0 ? <div className="px-2 py-1.5 text-xs text-muted-foreground">Aucune suggestion</div> : null}
          {options.map((item, index) => (
            <button
              key={`${item.label}-${item.lat}-${item.lon}`}
              id={`${listboxId}-option-${index}`}
              role="option"
              aria-selected={activeIndex === index}
              type="button"
              className={`block w-full rounded px-2 py-1.5 text-left text-sm ${
                activeIndex === index ? 'bg-accent text-accent-foreground' : 'hover:bg-accent/60'
              }`}
              onMouseEnter={() => setActiveIndex(index)}
              onMouseDown={(ev) => {
                ev.preventDefault();
                commitSelection(item);
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
