// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

export interface Notification {
  id: number;
  user_id: number;
  title: string;
  content: string;
  read: boolean;
  evaluation_id: number;
  scan_name: string;
  reviewer_id: number;
  type: string;
}