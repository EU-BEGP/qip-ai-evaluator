// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { LoaderService } from './loader-service';
import { catchError, finalize, Observable, throwError } from 'rxjs';
import config from '../config.json';

@Injectable({
  providedIn: 'root',
})
export class UtilsService {
  constructor (
    private http: HttpClient,
    private loaderService: LoaderService
  ) {}

  downloadPDF(id: string): Observable<Blob> {
    let URL = `${config.api.baseUrl}${config.api.extra.download}`;
    URL = URL.replace('{id}', String(id));
    this.loaderService.show();

    return this.http.get(URL, {
      responseType: 'blob'
    }).pipe(
      catchError((err) => throwError(() => err)),
      finalize(() => {
        this.loaderService.hide();
      })
    );
  }

  parseDate(date: string): Date {
    const [datePart, timePart] = date.split(' ');
    const [year, month, day] = datePart.split('-').map(Number);
    const [hour, minute] = timePart.split(':').map(Number);

    return new Date(year, month - 1, day, hour, minute);
  };
}