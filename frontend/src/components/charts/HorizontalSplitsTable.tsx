import React from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from 'recharts';
import { formatPace } from '@/lib/paceUtils';

interface SplitsData {
  split_index: number;
  distance_km: number;
  time_s: number;
  pace_s_per_km: number;
  elevation_gain_m: number;
  avg_hr_bpm?: number;
  elev_delta_m?: number;
}

interface HorizontalSplitsTableProps {
  data: SplitsData[];
  className?: string;
}

const HorizontalSplitsTable: React.FC<HorizontalSplitsTableProps> = ({ data, className = "" }) => {
  // Format pace for display
  const formatPaceDisplay = (paceSec: number) => {
    const minutes = Math.floor(paceSec / 60);
    const seconds = Math.floor(paceSec % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  // Calculate pace metrics for bar width and color
  const paceValues = data.map(d => d.pace_s_per_km).filter(p => p !== null && p !== undefined) as number[];
  const minPace = Math.min(...paceValues);
  const maxPace = Math.max(...paceValues);
  const paceRange = maxPace - minPace;

  // Normalization function for bar width
  const getBarWidth = (paceSec: number) => {
    if (paceRange === 0) return 0.7; // Default width if all paces are equal
    const normalizedWidth = (maxPace - paceSec) / paceRange;
    return Math.max(0.2, normalizedWidth); // Minimum 20% width for visibility
  };

  // Color function - lighter = faster, darker = slower
  const getBarColor = (paceSec: number) => {
    if (paceRange === 0) return '#56B4E9'; // Default Pacing color
    const normalizedPace = (maxPace - paceSec) / paceRange;
    // Use HSL lightness manipulation: faster (smaller pace) = lighter color
    const lightness = 85 - (normalizedPace * 40); // 85% (light) -> 45% (dark)
    return `hsl(210, 70%, ${lightness}%)`; // Blue hue, same saturation, variable lightness
  };

  // Prepare data for horizontal bar chart
  const chartData = data.map((split, index) => ({
    name: `Split ${split.split_index}`,
    value: split.pace_s_per_km || 0,
  }));

  const columns = [
    { 
      key: 'km', 
      header: 'Km', 
      align: 'left',
      render: (row: SplitsData) => (
        <span className="font-medium">
          {row.split_index === data.length - 1 && row.distance_km < 1 ? `${row.distance_km}` : row.split_index}
        </span>
      )
    },
    { 
      key: 'pace', 
      header: 'Allure', 
      align: 'left',
      render: (row: SplitsData) => (
        <span className="font-mono">
          {row.pace_s_per_km ? formatPaceDisplay(row.pace_s_per_km) : '--'}
        </span>
      )
    },
    {
      key: 'bar',
      header: '',
      align: 'center',
      render: (row: SplitsData) => (
        <div className="w-24">
          <ResponsiveContainer width="100%" height={24}>
            <BarChart 
              layout="horizontal" 
              data={[{ name: row.split_index.toString(), value: row.pace_s_per_km || 0 }]}
              margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
            >
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="name" />
              <Bar 
                dataKey="value" 
                fill={getBarColor(row.pace_s_per_km || 0)}
                radius={[0, 8, 8, 0]} // Pill-shaped bars
              />
              <Tooltip 
                formatter={(value: any) => formatPaceDisplay(value as number)}
                contentStyle={{ backgroundColor: 'rgba(0, 0, 0, 0.8)', borderRadius: '4px' }}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )
    },
    { 
      key: 'elevation', 
      header: 'Élév.', 
      align: 'right',
      render: (row: SplitsData) => (
        <span className="font-mono">
          {row.elev_delta_m !== undefined && row.elev_delta_m !== null 
            ? `${row.elev_delta_m > 0 ? '+' : ''}${Math.abs(row.elev_delta_m)}`
            : '--'
          }
        </span>
      )
    },
    { 
      key: 'hr', 
      header: 'FC', 
      align: 'right',
      render: (row: SplitsData) => (
        <span className="font-mono">
          {row.avg_hr_bpm ? Math.round(row.avg_hr_bpm) : '--'}
        </span>
      )
    }
  ];

  return (
    <div className={`w-full border border-gray-200 rounded-lg overflow-hidden ${className}`}>
      {/* Header */}
      <div className="bg-gray-50 px-6 py-3 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Temps intermédiaires</h3>
      </div>
      
      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((col) => (
                <th 
                  key={col.key}
                  className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${col.align === 'right' ? 'text-right' : ''}`}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.map((row, index) => (
              <tr 
                key={index}
                className="hover:bg-gray-50 transition-colors duration-200"
              >
                {columns.map((col) => (
                  <td 
                    key={col.key}
                    className={`px-6 py-4 whitespace-nowrap text-sm ${col.align === 'right' ? 'text-right' : 'text-left'}`}
                  >
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="px-6 py-3 text-sm text-gray-600 border-t border-gray-200">
        <div className="flex items-center space-x-4">
          <div className="flex items-center">
            <div className="w-4 h-3 bg-gradient-to-r from-blue-200 to-blue-600 rounded-full"></div>
            <span className="ml-2">Plus rapide</span>
          </div>
          <div className="flex items-center">
            <div className="w-4 h-3 bg-gradient-to-r from-blue-600 to-blue-800 rounded-full"></div>
            <span className="ml-2">Plus lent</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HorizontalSplitsTable;