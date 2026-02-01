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

interface VerticalPaceHistogramProps {
  data: SplitsData[];
  className?: string;
}

const VerticalPaceHistogram: React.FC<VerticalPaceHistogramProps> = ({ data, className = "" }) => {
  // Format pace for display
  const formatPaceDisplay = (paceSec: number) => {
    const minutes = Math.floor(paceSec / 60);
    const seconds = Math.floor(paceSec % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  // Calculate pace metrics for color
  const paceValues = data.map(d => d.pace_s_per_km).filter(p => p !== null && p !== undefined) as number[];
  const minPace = Math.min(...paceValues);
  const maxPace = Math.max(...paceValues);
  const paceRange = maxPace - minPace;

  // Color function - same as horizontal chart (lighter = faster)
  const getBarColor = (paceSec: number) => {
    if (paceRange === 0) return '#009E73'; // Default Splits color
    const normalizedPace = (maxPace - paceSec) / paceRange;
    const lightness = 85 - (normalizedPace * 40); // 85% (light) -> 45% (dark)
    return `hsl(142, 70%, ${lightness}%)`; // Green hue, same logic
  };

  // Prepare data for vertical bar chart
  const chartData = data.map((split, index) => ({
    splitNumber: split.split_index,
    pace: split.pace_s_per_km || 0,
    paceDisplay: formatPaceDisplay(split.pace_s_per_km || 0),
    avgHr: split.avg_hr_bpm,
    elevDelta: split.elev_delta_m,
  }));

  // Y-axis domain inverted (faster pace = higher position)
  const yDomain = [maxPace, minPace];

  return (
    <div className={`w-full ${className}`}>
      {/* Header */}
      <div className="bg-gray-50 px-6 py-3 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Allure par split</h3>
      </div>
      
      {/* Chart */}
      <div className="h-80">
        <ResponsiveContainer width="100%" height={320}>
          <BarChart 
            data={chartData}
            margin={{ top: 20, right: 30, bottom: 40, left: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis 
              dataKey="splitNumber" 
              type="number" 
              domain={[0.5, data.length + 0.5]}
              tickFormatter={(value) => `Km ${value}`}
            />
            <YAxis 
              type="number" 
              domain={yDomain} // Inverted domain: faster (lower value) = higher position
              tickFormatter={(value) => formatPaceDisplay(value)}
              label="Allure (min/km)"
              reversed // This ensures faster paces appear at the top
            />
            <Bar 
              dataKey="pace" 
              fill={getBarColor}
              radius={[4, 4, 0, 0]} // Rounded top corners, flat bottom
              maxBarSize={40}
            />
            <Tooltip 
              formatter={(value: any, payload: any) => {
                const data = payload && payload[0];
                if (!data) return '';
                
                let tooltipContent = `Allure: ${data.paceDisplay}/km<br>`;
                tooltipContent += `Split: ${data.splitNumber}`;
                
                if (data.avgHr !== undefined && data.avgHr !== null) {
                  tooltipContent += `<br>FC: ${Math.round(data.avgHr)} bpm`;
                }
                
                if (data.elevDelta !== undefined && data.elevDelta !== null) {
                  tooltipContent += `<br>Élév.: ${data.elevDelta > 0 ? '+' : ''}${Math.abs(data.elevDelta)}m`;
                }
                
                return tooltipContent;
              }}
              contentStyle={{ backgroundColor: 'rgba(0, 0, 0, 0.8)', borderRadius: '4px' }}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Collapsible Table */}
      <div className="border-t border-gray-200">
        <button 
          className="w-full px-6 py-3 text-left font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
          onClick={() => {
            const table = document.getElementById('splits-table');
            if (table) {
              table.classList.toggle('hidden');
            }
          }}
        >
          <span>Afficher/Masquer le tableau détaillé</span>
        </button>
        <div id="splits-table" className="hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Split
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Distance
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Temps
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Allure
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    FC
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Élév.
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data.map((row, index) => (
                  <tr key={index} className="hover:bg-gray-50 transition-colors duration-200">
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {row.splitNumber}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {row.distance_km} km
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {formatPaceDisplay(row.pace || 0)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {row.avgHr !== undefined && row.avgHr !== null 
                        ? Math.round(row.avgHr) 
                        : '--'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {row.elevDelta !== undefined && row.elevDelta !== null 
                        ? `${row.elevDelta > 0 ? '+' : ''}${Math.abs(row.elevDelta)}`
                        : '--'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VerticalPaceHistogram;