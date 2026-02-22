

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { catchError, finalize, Observable, throwError } from 'rxjs';
import config from '../config.json';
import { LoaderService } from './loader-service';

@Injectable({
  providedIn: 'root',
})
export class SelfEvaluationService {
  private base = `${config.api.baseUrl}evaluations`;

  constructor(private http: HttpClient,
              private loaderService: LoaderService
  ) {}

  getScans(moduleId: string): Observable<any> {
    return this.http.get<any>(
      `${this.base}/scans/${encodeURIComponent(moduleId)}`,
    );
  }

  getCriterions(scanId: string): Observable<any> {
    return this.http.get<any>(
      `${this.base}/scans/${encodeURIComponent(scanId)}/criterions`,
    );
  }

  updateCriterion(criterionId: string, result: any): Observable<any> {
    const url = `${this.base}/scans/criterions/${encodeURIComponent(criterionId)}/`;
    return this.http.put<any>(url, { result });
  }

  requestAiSuggestion(criterionId: string, question: string, description: string): Observable<any> {
    const url = `${this.base}/scans/criterions/${encodeURIComponent(criterionId)}/ai-suggestion/`;
    return this.http.post<{
      result: string;
    }>(url, { question, description});
  }

  getAiSuggestion(criterionId: string): Observable<{
    result: string;
  }> {
    const url = `${this.base}/scans/criterions/${encodeURIComponent(criterionId)}/result`;
    return this.http.get<{
      result: string;
    }>(url);
  }

  getResults(evaluationId: string) {
    let URL = `${config.api.baseUrl}${config.api.selfAssessment.results}`;
    URL = URL.replace('{id}', evaluationId);

    this.loaderService.show();

    return this.http.get<any>(URL).pipe(
      catchError((err) => throwError(() => err)),
      finalize(() => {
        this.loaderService.hide();
      })
    );
  }
}
