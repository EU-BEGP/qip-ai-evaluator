// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, signal } from '@angular/core';
import { MessageRequest } from '../interfaces/message-request';
import { catchError, finalize, Observable, tap, throwError } from 'rxjs';
import config from '../config.json';
import { LoaderService } from './loader-service';

@Injectable({
  providedIn: 'root',
})
export class NotificationService {
  private httpOptions = <any>{};
  unreadCount = signal(0);

  constructor(
    private http: HttpClient,
    private loaderService: LoaderService
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

    this.loaderService.show();

    return this.http.get<any>(URL).pipe(
      catchError((err) => throwError(() => err)),
      finalize(() => {
        this.loaderService.hide();
      })
    );
  }

  getUnreadNotificationsQuantity(email: string): Observable<any> {
    let URL = `${config.api.baseUrl}${config.api.notifications.unreadQuantity}`;
    URL = URL.replace('{email}', email);

    return this.http.get<any>(URL).pipe(
      catchError((err) => throwError(() => err))
    );
  }

  setUnreadCount(value: number) {
    this.unreadCount.set(value);
  }
}
