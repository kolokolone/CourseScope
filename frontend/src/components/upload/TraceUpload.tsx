'use client';

import { useCallback } from 'react';
import { FileText, Upload } from 'lucide-react';
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
    <Card className="mx-auto w-full max-w-2xl">
      <CardHeader className="p-4 md:p-6">
        <CardTitle className="flex items-center gap-2 text-base"><Upload className="h-5 w-5" />{title}</CardTitle>
      </CardHeader>
      <CardContent className="p-4 pt-0 md:p-6 md:pt-0">
        {description ? <div className="mb-3 text-sm text-muted-foreground">{description}</div> : null}
        <div
          {...dropzone.getRootProps()}
          className={`cursor-pointer rounded-lg border-2 border-dashed p-5 text-center transition-colors duration-200 ease-in-out md:p-8 ${dropzone.isDragActive ? 'border-primary bg-primary/5' : 'border-gray-300 hover:border-gray-400'}`}
        >
          <input {...dropzone.getInputProps()} data-testid="trace-upload-input" />
          <div className="flex flex-col items-center gap-3 md:gap-4">
            <FileText className="h-10 w-10 text-gray-400 md:h-12 md:w-12" />
            <div className="text-center">
              <p className="mb-2 text-base font-medium md:text-lg">
                {upload.isPending ? 'Import et indexation en cours...' : dropzone.isDragActive ? 'Déposez le fichier ici…' : 'Glissez un fichier GPX/FIT ici, ou cliquez pour le choisir'}
              </p>
              <p className="text-sm text-gray-500">Formats GPX et FIT · 100 Mo maximum</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
