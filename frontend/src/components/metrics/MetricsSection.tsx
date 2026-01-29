import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

type MetricValue = unknown;

interface MetricItem {
  label: string;
  value: MetricValue;
  unit?: string;
}

interface MetricsSectionProps {
  title: string;
  data: unknown;
}

function formatLabel(label: string) {
  const withSpaces = label.replace(/[_-]+/g, ' ');
  return withSpaces.charAt(0).toUpperCase() + withSpaces.slice(1);
}

function inferUnit(label: string) {
  if (label.endsWith('_km')) return 'km';
  if (label.endsWith('_m')) return 'm';
  if (label.endsWith('_s')) return 's';
  if (label.endsWith('_kmh')) return 'km/h';
  if (label.endsWith('_bpm')) return 'bpm';
  if (label.endsWith('_spm')) return 'spm';
  if (label.endsWith('_pct')) return '%';
  if (label.endsWith('_w')) return 'W';
  return undefined;
}

function formatNumber(value: number) {
  if (Number.isInteger(value)) return String(value);
  return value.toFixed(2);
}

function renderValue(value: MetricValue) {
  if (value === null || value === undefined) {
    return <span className="text-gray-400">-</span>;
  }

  if (typeof value === 'number') {
    return <span className="text-lg font-semibold">{formatNumber(value)}</span>;
  }

  if (typeof value === 'boolean') {
    return <span className="text-lg font-semibold">{value ? 'Yes' : 'No'}</span>;
  }

  if (typeof value === 'string') {
    return <span className="text-lg font-semibold break-words">{value}</span>;
  }

  return (
    <pre className="text-xs bg-gray-50 border rounded-md p-2 overflow-auto max-h-48">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function normalizeItems(data: unknown): MetricItem[] {
  if (data === null || data === undefined) return [];
  if (Array.isArray(data)) {
    return [{ label: 'Items', value: data }];
  }
  if (typeof data === 'object') {
    return Object.entries(data as Record<string, unknown>).map(([key, value]) => ({
      label: formatLabel(key),
      value,
      unit: inferUnit(key),
    }));
  }
  return [{ label: 'Value', value: data }];
}

function isEmptyData(data: unknown) {
  if (data === null || data === undefined) return true;
  if (Array.isArray(data)) return data.length === 0;
  if (typeof data === 'object') return Object.keys(data as Record<string, unknown>).length == 0;
  return false;
}

function MetricTile({ item }: { item: MetricItem }) {
  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-gray-600">{item.label}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2 flex-wrap">
          {renderValue(item.value)}
          {item.unit ? <span className="text-sm text-gray-500">{item.unit}</span> : null}
        </div>
      </CardContent>
    </Card>
  );
}

export function MetricsSection({ title, data }: MetricsSectionProps) {
  if (isEmptyData(data)) {
    return null;
  }

  const items = normalizeItems(data);
  if (items.length === 0) return null;

  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold">{title}</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((item) => (
          <MetricTile key={`${title}-${item.label}`} item={item} />
        ))}
      </div>
    </section>
  );
}
