// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

export interface Review {
  id: number;
  reviewer: string;
  review_max: number;
  review_score: number;
  date: string;
}