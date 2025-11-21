import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { catchError, Observable, throwError } from 'rxjs';
import config from '../config.json';

@Injectable({
  providedIn: 'root',
})
export class UtilsService {
  constructor (
    private http: HttpClient,
  ) {}

  downloadPDF(id: string): Observable<Blob> {
    let URL = `${config.api.baseUrl}${config.api.extra.download}`;
    URL = URL.replace('{id}', String(id));

    return this.http.get(URL, {
      responseType: 'blob'
    }).pipe(
      catchError((err) => throwError(() => err))
    );
  }
}
