// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Routes } from '@angular/router';
import { LoginComponent } from './pages/login/login';
import { EvaluationComponent } from './pages/evaluation/evaluation';
import { AuthGuard } from './guards/auth.guard';
import { Modules } from './pages/modules/modules';
import { Notifications } from './pages/notifications/notifications';
import { MainLayout } from './pages/main-layout/main-layout';
import { SelfAssessment } from './pages/self-assessment/self-assessment';
import { PeerReviewEvaluation } from './pages/peer-review-evaluation/peer-review-evaluation';
import { Results } from './pages/results/results';
import { PeerReview } from './pages/peer-review/peer-review';

export const routes: Routes = [
  {
    path: '',
    component: MainLayout,
    children: [
      {
        path: '',
        redirectTo: '/modules',
        pathMatch: 'full',
      },
      {
        path: 'modules',
        component: Modules,
        canActivate: [AuthGuard],
      },
      {
        path: 'notifications',
        component: Notifications,
        canActivate: [AuthGuard],
      },
      {
        path: 'evaluation/:id',
        component: EvaluationComponent,
        canActivate: [AuthGuard],
      },
      {
        path: 'self-assessment/:id',
        component: SelfAssessment,
        canActivate: [AuthGuard],
      },
      {
        path: 'self-assessment/:id/results',
        component: Results,
        canActivate: [AuthGuard],
      },
      {
        path: 'peer-review-evaluation/:id/review/:reviewId',
        component: PeerReviewEvaluation,
        canActivate: [AuthGuard],
      },
      {
        path: 'external-review/:token',
        component: PeerReview,
        canActivate: [AuthGuard],
      },
    ],
  },
  {
    path: 'login',
    component: LoginComponent,
  },
];
