// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { HttpClient, HttpHeaders, HttpResponse } from '@angular/common/http';
import { Injectable, signal } from '@angular/core';
import { MessageRequest } from '../interfaces/message-request';
import { catchError, finalize, Observable, throwError } from 'rxjs';
import config from '../config.json';
import { LoaderService } from './loader-service';
import { Notification } from '../interfaces/notification';
import { ApiMessage } from '../interfaces/api-message';
import { UnreadCount } from '../interfaces/unread-count';

interface ResponseHttpOptions {
  headers: HttpHeaders;
  observe: 'response';
}

@Injectable({
  providedIn: 'root',
})
export class NotificationService {
  private httpOptions: ResponseHttpOptions;
  unreadCount = signal(0);

  constructor(
    private http: HttpClient,
    private loaderService: LoaderService
  ) {
    this.httpOptions = {
      headers: new HttpHeaders({
        'Content-Type': 'application/json',
      }),
      observe: 'response',
    };
  }

  readMessage(messageRequest: MessageRequest): Observable<HttpResponse<ApiMessage>> {
    const URL = `${config.api.baseUrl}${config.api.notifications.read}`;
    const body = messageRequest;

    return this.http.post<ApiMessage>(URL, body, this.httpOptions).pipe(
      catchError((err) => {
        return throwError(() => err);
      })
    );
  }

  getNotifications(email: string): Observable<Notification[]> {
    let URL = `${config.api.baseUrl}${config.api.notifications.mailbox}`;

    this.loaderService.show();

    return this.http.get<Notification[]>(URL).pipe(
      catchError((err) => throwError(() => err)),
      finalize(() => {
        this.loaderService.hide();
      })
    );
  }

  getUnreadNotificationsQuantity(email: string): Observable<UnreadCount> {
    let URL = `${config.api.baseUrl}${config.api.notifications.unreadQuantity}`;

    return this.http.get<UnreadCount>(URL).pipe(
      catchError((err) => throwError(() => err))
    );
  }

  setUnreadCount(value: number) {
    this.unreadCount.set(value);
  }
}
