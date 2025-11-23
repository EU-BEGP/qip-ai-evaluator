import { Injectable } from '@angular/core';
import { ScanItem } from '../interfaces/scan-item';

@Injectable({
  providedIn: 'root',
})
export class StorageService {
  private readonly storageKey = 'evaluationList' + localStorage.getItem('accountEmail');

  constructor() {}

  addEvaluation(scanId: string, scanName: string): void {
    const list = JSON.parse(localStorage.getItem(this.storageKey) || '[]');

    const exists = list.some(
      (item: ScanItem) =>
        item.scan_id === scanId && item.scan_name === scanName
    );

    if (!exists) {
      const item = { "scan_id": scanId, "scan_name": scanName }
      list.push(item);
      localStorage.setItem(this.storageKey, JSON.stringify(list));
    }
  }

  removeEvaluation(scanId: string, scanName: string): void {
    const list = JSON.parse(localStorage.getItem(this.storageKey) || '[]');

    const updatedList = list.filter(
      (item: ScanItem) =>
        !(item.scan_id === scanId && item.scan_name === scanName)
    );

    if (updatedList.length === 0) {
      localStorage.removeItem(this.storageKey);
    } else {
      localStorage.setItem(this.storageKey, JSON.stringify(updatedList));
    }
  }
}
