import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class StorageService {
  private evaluationIdSubject = new BehaviorSubject<string | null> (null);
  evaluationId$ = this.evaluationIdSubject.asObservable();

  constructor() {
    window.addEventListener('storage', this.storageListener);
  }

  private storageListener = (event: StorageEvent) => {
    if (event.key === ('evaluationId' + localStorage.getItem('accountEmail'))) {
      this.evaluationIdSubject.next(event.newValue);
    }
  };

  setEvaluationId(value: string): void {
    this.evaluationIdSubject.next(value);
  }

  clearEvaluationId(): void {
    this.evaluationIdSubject.next(null);
  }

  ngOnDestroy(): void {
    window.removeEventListener('storage', this.storageListener);
  }
}
