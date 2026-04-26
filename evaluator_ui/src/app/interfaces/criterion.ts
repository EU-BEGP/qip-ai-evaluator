// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

export interface Criterion {
  name: string;
  description: string;
  score: number;
  shortcomings: string[];
  recommendations: string[];
}
