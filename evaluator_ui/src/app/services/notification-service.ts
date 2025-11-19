import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { MessageRequest } from '../interfaces/message-request';
import { catchError, Observable, throwError } from 'rxjs';
import config from '../config.json';

@Injectable({
  providedIn: 'root',
})
export class NotificationService {
  private httpOptions = <any>{};

  constructor(
    private http: HttpClient,
  ) {
    this.httpOptions = {
      headers: new HttpHeaders({
        'Content-Type': 'application/json',
      }),
      observe: 'response' as 'response',
    };
  }

  readMessage(messageRequest: MessageRequest): Observable<any> {
    const URL = `${config.api.baseUrl}${config.api.notifications.read}`;
    const body = messageRequest;

    return this.http.post(URL, body, this.httpOptions).pipe(
      catchError((err) => {
        return throwError(() => err);
      })
    );
  }

  getNotifications(email: string): Observable<any> {
    let URL = `${config.api.baseUrl}${config.api.notifications.mailbox}`;
    URL = URL.replace('{email}', email);

    return this.http.get<any>(URL).pipe(
      catchError((err) => throwError(() => err))
    );
  }
}
