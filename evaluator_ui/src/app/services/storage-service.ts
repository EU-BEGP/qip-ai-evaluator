// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Injectable } from '@angular/core';
import { ScanItem } from '../interfaces/scan-item';

@Injectable({
  providedIn: 'root',
})
export class StorageService {
  constructor() {}

  addEvaluation(scanId: string, scanName: string): void {
    const storageKey = 'evaluationList' + localStorage.getItem('accountEmail');
    const list = JSON.parse(localStorage.getItem(storageKey) || '[]');

    const exists = list.some(
      (item: ScanItem) =>
        item.scan_id === scanId && item.scan_name === scanName
    );

    if (!exists) {
      const item = { "scan_id": scanId, "scan_name": scanName }
      list.push(item);
      localStorage.setItem(storageKey, JSON.stringify(list));
    }
  }

  removeEvaluation(scanId: string, scanName: string): void {
    const storageKey = 'evaluationList' + localStorage.getItem('accountEmail');
    const list = JSON.parse(localStorage.getItem(storageKey) || '[]');

    const updatedList = list.filter(
      (item: ScanItem) =>
        !(item.scan_id === scanId && item.scan_name === scanName)
    );

    if (updatedList.length === 0) {
      localStorage.removeItem(storageKey);
    } else {
      localStorage.setItem(storageKey, JSON.stringify(updatedList));
    }
  }
}
