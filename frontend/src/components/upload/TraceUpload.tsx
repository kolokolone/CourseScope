'use client';

import { useCallback } from 'react';
import { Route, Upload } from 'lucide-react';
import { useDropzone } from 'react-dropzone';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useUploadTrace } from '@/hooks/useTraces';
import { ApiError } from '@/lib/api';
import type { TraceId } from '@/types/api';

export interface TraceUploadProps {
  title?: string;
  description?: string;
  onUploadSuccess: (traceId: TraceId) => void;
}

export function TraceUpload({ title = 'Importer une trace', description, onUploadSuccess }: TraceUploadProps) {
  const upload = useUploadTrace();
  const onDrop = useCallback(async (files: File[]) => {
    const file = files[0];
    if (!file) return;
    if (!/\.(gpx|fit)$/i.test(file.name)) {
      window.alert('Formats autorises : GPX et FIT.');
      return;
    }
    if (file.size > 100 * 1024 * 1024) {
      window.alert('Le fichier depasse la limite de 100 Mo.');
      return;
    }
    try {
      const result = await upload.mutateAsync({ file, name: file.name });
      onUploadSuccess(result.trace.id);
    } catch (error) {
      window.alert(error instanceof ApiError ? error.message : "L'import de la trace a echoue.");
    }
  }, [onUploadSuccess, upload]);

  const dropzone = useDropzone({
    onDrop,
    maxFiles: 1,
    multiple: false,
    disabled: upload.isPending,
    accept: { 'application/gpx+xml': ['.gpx'], 'application/octet-stream': ['.fit'] },
  });

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base"><Upload className="h-5 w-5" />{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {description ? <p className="mb-3 text-sm text-muted-foreground">{description}</p> : null}
        <div
          {...dropzone.getRootProps()}
          className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-colors ${dropzone.isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'}`}
        >
          <input {...dropzone.getInputProps()} data-testid="trace-upload-input" />
          <Route className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
          <p className="font-medium">{upload.isPending ? 'Import et indexation en cours...' : 'Glissez un fichier GPX/FIT ou cliquez pour le choisir'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Trace persistante, fichier original et Parquet — 100 Mo maximum</p>
        </div>
      </CardContent>
    </Card>
  );
}
