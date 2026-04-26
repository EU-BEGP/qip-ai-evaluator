// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { HttpClient, HttpHeaders, HttpResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { catchError, finalize, interval, Observable, switchMap, takeWhile, tap, throwError } from 'rxjs';
import config from '../config.json';
import { ToastrService } from 'ngx-toastr';
import { ScanRequest } from '../interfaces/scan-request';
import { StorageService } from './storage-service';
import { LoaderService } from './loader-service';
import { EvaluateResponse } from '../interfaces/evaluate-response';
import { EvaluationListItem } from '../interfaces/evaluation-list-item';
import { EvaluationResult } from '../interfaces/evaluation-result';
import { EvaluationStatus } from '../interfaces/evaluation-status';
import { Scan } from '../interfaces/scan';
import { ModuleLink } from '../interfaces/module-link';
import { ModuleDashboardItem } from '../interfaces/module-dashboard-item';

interface ResponseHttpOptions {
  headers: HttpHeaders;
  observe: 'response';
}

@Injectable({
  providedIn: 'root',
})
export class EvaluationService {
  private evaluationInterval = config.time.evaluationPolling * 1000;

  private httpOptions: ResponseHttpOptions;

  constructor(
    private http: HttpClient,
    private toastr: ToastrService,
    private storageService: StorageService,
    private loaderService: LoaderService
  ) {
    this.httpOptions = {
      headers: new HttpHeaders({
        'Content-Type': 'application/json',
      }),
      observe: 'response',
    };
  }

  evaluate(scanRequest: ScanRequest): Observable<HttpResponse<EvaluateResponse>> {
    const URL = `${config.api.baseUrl}${config.api.evaluation.evaluate}`;
    const body = scanRequest;
    this.loaderService.show();

    return this.http.post<EvaluateResponse>(URL, body, this.httpOptions).pipe(
      tap((response: HttpResponse<EvaluateResponse>) => {
        const scanId = response.body?.scan_id;
        if (scanId !== undefined) {
          this.storageService.addEvaluation(String(scanId), body.scan_name);
        }
        this.toastr.success('Evaluation request successfully submitted.', 'Success');
        this.loaderService.hide();
      }),
      catchError((err) => {
        this.toastr.error('Please try again later.', 'Error');
        this.loaderService.hide();
        return throwError(() => err);
      })
    );
  }

  getEvaluationList(scanRequest: ScanRequest): Observable<HttpResponse<EvaluationListItem[]>> {
    const URL = `${config.api.baseUrl}${config.api.evaluation.list}`;
    const body = scanRequest;
    this.loaderService.show();

    return this.http.post<EvaluationListItem[]>(URL, body, this.httpOptions).pipe(
      catchError((err) => {
        this.toastr.error('Could not load history.', 'Error');
        return throwError(() => err);
      }),
      finalize(() => {
        this.loaderService.hide();
      })
    );
  }

  getEvaluationDetailModule(id: number, loader: boolean = false): Observable<EvaluationResult> {
    let URL = `${config.api.baseUrl}${config.api.evaluation.detailModule}`;
    URL = URL.replace('{id}', String(id));

    if (loader) {
      this.loaderService.show();
    }

    return this.http.get<EvaluationResult>(URL).pipe(
      catchError((err) => {
        this.toastr.error('Could not load evaluation detail.', 'Error');
        return throwError(() => err);
      }),
      finalize(() => {
        if (loader) {
          this.loaderService.hide();
        }
      })
    );
  }

  getEvaluationDetailScan(id: number, loader: boolean = false): Observable<EvaluationResult> {
    let URL = `${config.api.baseUrl}${config.api.evaluation.detailScan}`;
    URL = URL.replace('{id}', String(id));

    if (loader) {
      this.loaderService.show();
    }

    return this.http.get<EvaluationResult>(URL).pipe(
      catchError((err) => {
        this.toastr.error('Could not load evaluation detail.', 'Error');
        return throwError(() => err);
      }),
      finalize(() => {
        if (loader) {
          this.loaderService.hide();
        }
      })
    );
  }

  getStatusModule(id: string): Observable<EvaluationStatus> {
    let URL = `${config.api.baseUrl}${config.api.evaluation.statusModule}`;
    URL = URL.replace('{id}', String(id));

    return interval(this.evaluationInterval).pipe(
      switchMap(() => this.http.get<EvaluationStatus>(URL)),
      takeWhile(res => res.status !== 'Completed' && res.status !== 'Failed', true)
    );
  }

  getStatusScan(id: string): Observable<EvaluationStatus> {
    let URL = `${config.api.baseUrl}${config.api.evaluation.statusScan}`;
    URL = URL.replace('{id}', String(id));

    return interval(this.evaluationInterval).pipe(
      switchMap(() => this.http.get<EvaluationStatus>(URL)),
      takeWhile(res => res.status !== 'Completed' && res.status !== 'Failed', true)
    );
  }

  getIdsList(id: string): Observable<Scan[]> {
    this.loaderService.show();
    let URL = `${config.api.baseUrl}${config.api.evaluation.idsList}`;
    URL = URL.replace('{id}', String(id));


    return this.http.get<Scan[]>(URL).pipe(
      catchError((err) => {
        return throwError(() => err);
      }),
      finalize(() => {
        this.loaderService.hide();
      })
    );
  }

  getLinkModule(id: string): Observable<ModuleLink> {
    let URL = `${config.api.baseUrl}${config.api.evaluation.linkModule}`;
    URL = URL.replace('{id}', String(id));
    this.loaderService.show();

    return this.http.get<ModuleLink>(URL).pipe(
      catchError((err) => {
        this.loaderService.hide();
        return throwError(() => err);
      }),
      finalize(() => {
        //this.loaderService.hide();
      })
    );
  }

  getModules(email: string): Observable<ModuleDashboardItem[]> {
    let URL = `${config.api.baseUrl}${config.api.evaluation.modulesList}`;
    URL = URL.replace('{email}', email);
    this.loaderService.show();

    return this.http.get<ModuleDashboardItem[]>(URL).pipe(
      catchError((err) => throwError(() => err)),
      finalize(() => {
        this.loaderService.hide();
      })
    );
  }
}
