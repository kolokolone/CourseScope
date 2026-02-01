'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useUploadActivity } from '@/hooks/useActivity';
import { ApiError } from '@/lib/api';

interface ActivityUploadProps {
  onUploadSuccess: (activityId: string, activityType: 'real' | 'theoretical') => void;
}

export function ActivityUpload({ onUploadSuccess }: ActivityUploadProps) {
  const [uploadingFile, setUploadingFile] = useState<File | null>(null);
  const uploadMutation = useUploadActivity();

  const startUpload = useCallback(
    async (file: File) => {
      setUploadingFile(file);

      try {
        const result = await uploadMutation.mutateAsync({
          file,
          name: file.name,
        });

        onUploadSuccess(result.id, result.type);
        setUploadingFile(null);
      } catch (error) {
        if (error instanceof ApiError) {
          console.error('[UPLOAD ERROR] API Error:', error);
          alert(`Upload failed: ${error.message}`);
        } else if (error instanceof Error) {
          console.error('[UPLOAD ERROR] Generic Error:', error);
          const message = error.message || 'Unknown error';
          const lower = message.toLowerCase();
          const hint = lower.includes('failed to fetch') || lower.includes('network') || lower.includes('err_failed')
            ? `Network error (${message}). Check API URL, CORS, or backend availability.`
            : lower.includes('failed to parse url')
              ? `Invalid API URL (${message}). Check NEXT_PUBLIC_API_URL formatting.`
              : message;
          alert(`Upload failed: ${hint}`);
        } else {
          console.error('[UPLOAD ERROR] Unknown Error:', error);
          alert('Upload failed: Unknown error');
        }
        setUploadingFile(null);
      }
    },
    [uploadMutation, onUploadSuccess]
  );

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;

      const file = acceptedFiles[0];
      const fileName = file.name.toLowerCase();

      // Validation .gpx/.fit
      if (!fileName.endsWith('.gpx') && !fileName.endsWith('.fit')) {
        alert('Please upload a GPX or FIT file');
        return;
      }

      // Validation taille (100MB)
      if (file.size > 100 * 1024 * 1024) {
        alert('File too large. Maximum size is 100MB');
        return;
      }

      startUpload(file);
    },
    [startUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/gpx+xml': ['.gpx'],
      'application/octet-stream': ['.fit']
    },
    maxFiles: 1,
    multiple: false,
    disabled: uploadMutation.isPending
  });

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="h-5 w-5" />
          Upload Activity
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!uploadingFile ? (
          <div
            {...getRootProps()}
            className={`
              border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
              transition-colors duration-200 ease-in-out
              ${isDragActive 
                ? 'border-primary bg-primary/5' 
                : 'border-gray-300 hover:border-gray-400'
              }
            `}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center gap-4">
              <FileText className="h-12 w-12 text-gray-400" />
              <div>
                {isDragActive ? (
                  <p className="text-lg font-medium">Drop the file here...</p>
                ) : (
                  <div className="text-center">
                    <p className="text-lg font-medium mb-2">
                      Drag & drop a GPX/FIT file here, or click to select
                    </p>
                    <p className="text-sm text-gray-500">
                      Supported formats: GPX, FIT (max 100MB)
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-blue-600" />
                <div>
                  <p className="font-medium">{uploadingFile.name}</p>
                  <p className="text-sm text-gray-500">
                    {(uploadingFile.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-center rounded-md border border-dashed border-gray-200 py-4 text-sm text-gray-600">
              Uploading and analyzing...
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
