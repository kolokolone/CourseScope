'use client';

import * as React from 'react';
import { Star } from 'lucide-react';

import { Button } from '@/components/ui/button';

type TraceTitleBarProps = {
  titleDisplay: string;
  isEditingTitle: boolean;
  traceNameDraft: string;
  isTitleDirty: boolean;
  isRenaming: boolean;
  isSaved: boolean;
  isSaving: boolean;
  titleInputRef: React.RefObject<HTMLInputElement | null>;
  onTitleChange: (value: string) => void;
  onStartEditing: () => void;
  onRename: () => void;
  onCancelEditing: () => void;
  onToggleSave: () => Promise<void>;
};

export function TraceTitleBar({
  titleDisplay,
  isEditingTitle,
  traceNameDraft,
  isTitleDirty,
  isRenaming,
  isSaved,
  isSaving,
  titleInputRef,
  onTitleChange,
  onStartEditing,
  onRename,
  onCancelEditing,
  onToggleSave,
}: TraceTitleBarProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <div className="text-xs text-muted-foreground">Nom du trace</div>
        {!isEditingTitle ? (
          <button
            type="button"
            className="text-base font-semibold text-left hover:underline underline-offset-2"
            onClick={onStartEditing}
          >
            {titleDisplay}
          </button>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            <input
              ref={titleInputRef}
              className="h-9 w-full max-w-md rounded-md border px-3 text-sm"
              value={traceNameDraft}
              onChange={(e) => onTitleChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') {
                  e.preventDefault();
                  onCancelEditing();
                }
                if (e.key === 'Enter') {
                  if (isTitleDirty) onRename();
                  else onCancelEditing();
                }
              }}
              placeholder="Nom personnalise du trace"
            />
            {isTitleDirty ? (
              <Button size="sm" variant="outline" onClick={onRename} disabled={isRenaming}>
                Renommer
              </Button>
            ) : null}
          </div>
        )}
      </div>
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant={isSaved ? 'outline' : 'ghost'}
          onClick={() => void onToggleSave()}
          disabled={isSaving || isSaved}
          title={isSaved ? 'Trace deja enregistre' : 'Enregistrer le trace'}
        >
          <Star className={`h-4 w-4 ${isSaved ? 'fill-yellow-400 text-yellow-500' : ''}`} />
        </Button>
        <div className="text-xs text-muted-foreground">
          {isSaved ? 'Trace enregistree' : 'Trace non enregistree'}
        </div>
      </div>
    </div>
  );
}
