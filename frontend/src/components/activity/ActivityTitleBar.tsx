'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';

import { Button } from '@/components/ui/button';

type ActivityTitleBarProps = {
  activityId: string;
  titleDisplay: string;
  isEditingTitle: boolean;
  activityNameDraft: string;
  isTitleDirty: boolean;
  isRenaming: boolean;
  raceDateLabel: string | null;
  titleInputRef: React.RefObject<HTMLInputElement | null>;
  onTitleChange: (value: string) => void;
  onStartEditing: () => void;
  onRename: () => Promise<void>;
  onCancelEditing: () => void;
};

export function ActivityTitleBar({
  activityId,
  titleDisplay,
  isEditingTitle,
  activityNameDraft,
  isTitleDirty,
  isRenaming,
  raceDateLabel,
  titleInputRef,
  onTitleChange,
  onStartEditing,
  onRename,
  onCancelEditing,
}: ActivityTitleBarProps) {
  const router = useRouter();

  return (
    <div>
      {!isEditingTitle ? (
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="text-base font-semibold text-left hover:underline underline-offset-2"
            onClick={onStartEditing}
          >
            {titleDisplay}
          </button>
          <span className="inline-flex items-center rounded-full border bg-background/70 px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
            {activityId}
          </span>
          <Button
            size="sm"
            variant="ghost"
            className="text-xs text-muted-foreground"
            onClick={() => router.push(`/activities-beta/${activityId}`)}
          >
            Vue bêta
          </Button>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <input
            ref={titleInputRef}
            className="h-9 w-full max-w-md rounded-md border px-3 text-sm"
            value={activityNameDraft}
            onChange={(e) => onTitleChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                e.preventDefault();
                onCancelEditing();
              }
              if (e.key === 'Enter') {
                if (isTitleDirty) {
                  void onRename();
                } else {
                  onCancelEditing();
                }
              }
            }}
            placeholder="Nom personnalisé de l'activité"
          />
          {isTitleDirty ? (
            <Button size="sm" variant="outline" onClick={() => void onRename()} disabled={isRenaming}>
              Renommer
            </Button>
          ) : null}
        </div>
      )}
      {raceDateLabel ? <div className="text-xs text-muted-foreground">Date de course: {raceDateLabel}</div> : null}
    </div>
  );
}
