export interface Scan {
  name: string;
  id: number | null;
  evaluable: boolean;
  updated_data?: any;
  scan_max: number;
  scan_average: number | null;
  status: string;
  outdated: boolean;
}