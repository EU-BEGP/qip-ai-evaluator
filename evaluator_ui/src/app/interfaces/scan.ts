// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

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