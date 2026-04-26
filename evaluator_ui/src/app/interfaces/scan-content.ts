// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Criterion } from './criterion';

export interface ScanContent {
  scan: string;
  description: string;
  criteria: Criterion[];
}
